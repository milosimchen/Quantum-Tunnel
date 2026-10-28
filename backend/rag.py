"""
Retrieval for the copilot: embed the question with Gemini, run hybrid
(vector + keyword) search in Supabase, and hand the model numbered sources.

The model cites sources by number; validate_citations() keeps only numbers that
were actually retrieved, the same way copilot.validate_links() treats ids.
Retrieval is off unless GEMINI_API_KEY, SUPABASE_URL and
SUPABASE_SERVICE_ROLE_KEY are all set (and RAG_ENABLED isn't "0"), so the
copilot behaves exactly as before without them.
"""

import math
import os
import re
import time

import requests

EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "gemini-embedding-001")
EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
EMBED_DIM = 768  # must match vector(768) in supabase/migrations/004_rag.sql
TASK_TYPES = {"query": "RETRIEVAL_QUERY", "document": "RETRIEVAL_DOCUMENT"}
TOP_K = int(os.environ.get("RAG_TOP_K", "6"))
MAX_SOURCE_CHARS = 1500
SOURCE_LABELS = {"lesson": "Quantum Tunnel lesson", "qiskit_docs": "Qiskit documentation", "arxiv": "arXiv"}


class RetrievalError(Exception):
    pass


def enabled():
    if os.environ.get("RAG_ENABLED", "1") == "0":
        return False
    return all(os.environ.get(k) for k in ("GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"))


# --- Clients -----------------------------------------------------------------------

def embed(texts, input_type, retries=6, timeout=60):
    """Embed a list of texts. input_type is "query" or "document". Backs off on rate limits."""
    headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}
    body = {"requests": [{
        "model": f"models/{EMBED_MODEL}",
        "content": {"parts": [{"text": text}]},
        "taskType": TASK_TYPES[input_type],
        "outputDimensionality": EMBED_DIM,
    } for text in texts]}
    for attempt in range(retries):
        try:
            response = requests.post(EMBED_URL.format(model=EMBED_MODEL), json=body, headers=headers, timeout=timeout)
        except (requests.Timeout, requests.ConnectionError) as e:
            if attempt == retries - 1:
                raise RetrievalError(f"Gemini request failed: {e}") from e
            time.sleep(min(60, 2 ** attempt * 5))  # transient: retry like a rate limit
            continue
        except requests.RequestException as e:
            raise RetrievalError(f"Gemini request failed: {e}") from e
        if response.status_code == 429 or response.status_code >= 500:
            time.sleep(min(60, 2 ** attempt * 5))
            continue
        if not response.ok:
            raise RetrievalError(f"Gemini returned {response.status_code}: {response.text[:200]}")
        return [normalize(e["values"][:EMBED_DIM]) for e in response.json()["embeddings"]]
    raise RetrievalError("Gemini rate limit: gave up after retries")


def normalize(vector):
    """Unit length. Gemini only normalizes full-size embeddings, not reduced ones."""
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


def auth_header(key):
    """Legacy service_role keys are JWTs and go in Authorization too; new sb_secret_ keys only go in apikey."""
    return {"Authorization": f"Bearer {key}"} if key.startswith("eyJ") else {}


def supabase(method, path, timeout=15, **kwargs):
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    headers = {"apikey": key, **auth_header(key), **kwargs.pop("headers", {})}
    url = f"{os.environ['SUPABASE_URL'].rstrip('/')}/rest/v1/{path}"
    try:
        response = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
    except requests.RequestException as e:
        raise RetrievalError(f"Supabase request failed: {e}") from e
    if not response.ok:
        raise RetrievalError(f"Supabase returned {response.status_code}: {response.text[:200]}")
    return response.json() if response.content else None


def vector_literal(vector):
    return "[" + ",".join(f"{x:.7g}" for x in vector) + "]"


# --- Retrieval ---------------------------------------------------------------------

def retrieval_query(message, history, max_chars=1000):
    """The current message, plus the previous user turn so follow-ups like "what about the second one?" still retrieve."""
    previous = next((m.get("content", "") for m in reversed(history or []) if m.get("role") == "user"), "")
    query = f"{previous}\n{message}".strip() if previous else message.strip()
    return query[-max_chars:]


def keyword_query(text):
    """OR together the distinct words so the keyword side of hybrid search ranks partial matches instead of requiring all terms."""
    words = []
    for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9+\-]*", text.lower()):
        if len(word) > 2 and word not in words:
            words.append(word)
    return " or ".join(words[:30])


def search(query, k=TOP_K, sources=None, keyword=True):
    """Top-k chunks for a query. keyword=False turns off the full-text half of hybrid search (used by eval_rag.py)."""
    [vector] = embed([query], "query")
    rows = supabase("POST", "rpc/match_rag_chunks", json={
        "query_embedding": vector_literal(vector),
        "query_text": keyword_query(query) if keyword else "",
        "match_count": k,
        "source_filter": sources,
    })
    return rows or []


# --- Prompt and citations --------------------------------------------------------------

def format_sources(chunks):
    """The <sources> block for the prompt. Sources are numbered S1, S2, ... in rank order."""
    if not chunks:
        return ""
    parts = []
    for n, chunk in enumerate(chunks, start=1):
        heading = " > ".join(p for p in (chunk.get("title"), chunk.get("section")) if p)
        content = chunk.get("content", "")
        if len(content) > MAX_SOURCE_CHARS:
            content = content[: MAX_SOURCE_CHARS - 1].rstrip() + "…"
        parts.append(f'<source id="S{n}" kind="{SOURCE_LABELS.get(chunk.get("source"), "reference")}">\n{heading}\n\n{content}\n</source>')
    return "<sources>\n" + "\n".join(parts) + "\n</sources>"


def validate_citations(citations, chunks, limit=4):
    """Resolve cited ids (S1, S2, ...) to sources the user can open; anything not retrieved is dropped."""
    valid, seen_docs = [], set()
    for citation in citations or []:
        match = re.fullmatch(r"S(\d+)", str(citation).strip())
        if not match:
            continue
        index = int(match.group(1)) - 1
        if not 0 <= index < len(chunks):
            continue
        chunk = chunks[index]
        doc = (chunk.get("source"), chunk.get("doc_id"))
        if doc in seen_docs:
            continue
        seen_docs.add(doc)
        citation = {
            "id": f"S{index + 1}",
            "kind": chunk.get("source"),
            "label": SOURCE_LABELS.get(chunk.get("source"), "Source"),
            "title": chunk.get("title"),
        }
        if chunk.get("source") == "lesson":
            citation["path"] = f"/study/{chunk.get('doc_id')}"   # in-app route
        else:
            citation["url"] = chunk.get("url")
        valid.append(citation)
    return valid[:limit]
