"""
Turns the retrieval corpus into chunks: Quantum Tunnel's own lessons, the
Qiskit guides (github.com/Qiskit/documentation, CC BY-SA 4.0) and arXiv
abstracts. Everything here is pure text processing so it can be tested without
network access.

A chunk is a dict with: id, source, doc_id, title, section, url, content.
"""

import fnmatch
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_CHUNK_CHARS = 3000
QISKIT_DOCS_URL = "https://quantum.cloud.ibm.com/docs/guides/"

# Guides about the IBM Cloud platform (accounts, billing, admin), partner
# products, REST and C APIs, and version migrations. They don't help with
# learning quantum computing or Qiskit, and they crowd out guides that do.
QISKIT_SKIP = [
    "changelog-*", "index", "faq", "code-of-conduct", "open-source", "support", "responsibilities",
    "access-*", "authorization-roles", "allocation-limits", "classroom-accounts", "cloud-*",
    "context-based-restrictions", "custom-roles", "invite-and-manage-users", "manage-*", "instances",
    "plans-overview", "view-cost", "virtual-private-endpoints", "security-policies", "secure-data",
    "ha-dr", "upgrade-from-open", "quickstart-steps-org", "retired-qpus", "fair-share-scheduler",
    "job-limits", "max-execution-time", "observability-*", "logging", "online-lab-environments",
    "slurm-*", "qrmi", "compute-services", "qiskit-code-assistant", "qiskit-mcp-servers", "ai-skills",
    "save-credentials", "initialize-account", "add-job-tags", "save-jobs", "calibration-jobs",
    "repetition-rate-execution", "qiskit-sdk-version-strategy",
    "*-rest-api", "install-c-api", "c-extension-for-python", "install-*-source", "metapackage-migration",
    "qiskit-1.0*", "qiskit-backendv1-to-v2", "pulse-migration", "migrate-*",
    "functions", "functions-get-started", "function-template-*", "qiskit-function-templates", "serverless*",
    "algorithmiq-*", "aqarios-*", "colibritd-*", "global-data-*", "kipu-*", "multiverse-*", "parity-*",
    "q-ctrl-*", "qedma-*", "qunova-*", "quantum-elements-*",
]


def skip_guide(stem):
    return any(fnmatch.fnmatch(stem, pattern) for pattern in QISKIT_SKIP)
ARXIV_URL = "https://arxiv.org/abs/"


def content_hash(chunk):
    text = "\x1f".join(str(chunk.get(k) or "") for k in ("title", "section", "url", "content"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embedding_text(chunk):
    """What gets embedded: the document and section titles give short chunks their context."""
    heading = " > ".join(part for part in (chunk["title"], chunk.get("section")) if part)
    return f"{heading}\n\n{chunk['content']}"


# --- Splitting -----------------------------------------------------------------

def split_sections(markdown):
    """Split markdown into (heading, body) pairs on #, ## and ### headings, skipping fenced code."""
    sections, heading, lines, in_fence = [], None, [], False
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else re.match(r"^(#{1,3})\s+(.*\S)\s*$", line)
        if match:
            if any(l.strip() for l in lines):
                sections.append((heading, "\n".join(lines).strip()))
            heading, lines = match.group(2).strip(), []
        else:
            lines.append(line)
    if any(l.strip() for l in lines):
        sections.append((heading, "\n".join(lines).strip()))
    return sections


def split_text(text, limit=MAX_CHUNK_CHARS):
    """Pack paragraphs into pieces of at most `limit` characters; a single oversized paragraph is cut on sentence breaks."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces, current = [], ""
    for paragraph in paragraphs:
        for part in _cut(paragraph, limit):
            if current and len(current) + len(part) + 2 > limit:
                pieces.append(current)
                current = part
            else:
                current = f"{current}\n\n{part}" if current else part
    if current:
        pieces.append(current)
    return pieces


def _cut(paragraph, limit):
    if len(paragraph) <= limit:
        return [paragraph]
    parts, current = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        while len(sentence) > limit:
            parts.append(sentence[:limit])
            sentence = sentence[limit:]
        if current and len(current) + len(sentence) + 1 > limit:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}" if current else sentence
    if current:
        parts.append(current)
    return parts


def chunk_document(source, doc_id, title, url, markdown, url_for_section=None):
    chunks = []
    for heading, body in split_sections(markdown):
        if heading and heading.strip() == title.strip():
            heading = None
        for piece in split_text(body):
            chunks.append({
                "id": f"{source}:{doc_id}:{len(chunks)}",
                "source": source,
                "doc_id": doc_id,
                "title": title,
                "section": heading,
                "url": url_for_section(heading) if url_for_section else url,
                "content": piece,
            })
    return chunks


# --- Lessons -------------------------------------------------------------------

def lesson_markdown(lesson):
    """Flatten a lesson's blocks (see frontend/src/study/lessons.js) into markdown."""
    out = []
    for block in lesson.get("blocks", []):
        kind = block.get("type")
        if kind in ("p", "note"):
            out.append(block["text"])
        elif kind == "math":
            out.append(f"$${block['tex']}$$")
        elif kind == "code":
            out.append(f"```{block.get('language', '')}\n{block['code']}\n```")
        elif kind == "circuit" and block.get("caption"):
            gates = ", ".join(f"{g[0].upper()} on {g[1]}" for g in block.get("gates", []))
            out.append(f"Circuit ({block.get('numQubits')} qubits: {gates}). {block['caption']}")
        elif kind == "check":
            answer = block["choices"][block["answer"]]
            out.append(f"Question: {block['question']}\nAnswer: {answer}. {block.get('explanation', '')}".strip())
    return "\n\n".join(out)


def lesson_chunks(lessons):
    chunks = []
    for lesson in lessons:
        title = lesson["title"]
        track = lesson.get("trackTitle") or lesson.get("track")
        for chunk in chunk_document("lesson", lesson["id"], title, f"/study/{lesson['id']}", lesson_markdown(lesson)):
            chunk["section"] = chunk["section"] or track
            chunks.append(chunk)
    return chunks


# --- Qiskit guides -----------------------------------------------------------------

def _frontmatter(text):
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not match:
        return {}, text
    meta = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        if value:
            meta[key.strip()] = value.strip().strip("'\"")
    return meta, text[match.end():]


def clean_mdx(text):
    """Strip MDX/JSX scaffolding from prose, keeping lists, math and code. Code blocks are left untouched."""
    parts = re.split(r"(^```.*?^```[ \t]*$)", text, flags=re.S | re.M)
    return re.sub(r"\n{3,}", "\n\n", "".join(p if p.startswith("```") else _clean_prose(p) for p in parts)).strip()


def _clean_prose(text):
    text = re.sub(r"\{/\*.*?\*/\}", "", text, flags=re.S)                    # MDX comments
    text = re.sub(r"^\s*(import|export)\s.*\bfrom\s+['\"].*$", "", text, flags=re.M)  # JS module lines
    text = re.sub(r"<(\w+)[^<>]*/>", "", text)                                # self-closing components
    text = re.sub(r"</?[A-Z]\w*(\s[^<>]*)?>", "", text)                       # component wrappers, keep children
    text = re.sub(r"</?(span|div|br|img|details|summary)\b[^<>]*>", "", text)
    return re.sub(r"\[([^\]]+)\]\((?:/docs/|https?://)[^)]*\)", r"\1", text)  # keep link text only


def notebook_markdown(raw):
    """Markdown and code cells of a .ipynb, in order. Outputs are dropped."""
    notebook = json.loads(raw)
    parts = []
    for cell in notebook.get("cells", []):
        if "version-info" in (cell.get("metadata", {}).get("tags") or []):
            continue
        source = "".join(cell.get("source", []))
        if not source.strip():
            continue
        parts.append(source if cell.get("cell_type") == "markdown" else f"```python\n{source}\n```")
    return "\n\n".join(parts)


def qiskit_guide_chunks(guides_dir):
    chunks = []
    for path in sorted(Path(guides_dir).iterdir()):
        if path.suffix not in (".mdx", ".ipynb") or skip_guide(path.stem):
            continue
        raw = path.read_text(encoding="utf-8")
        text = notebook_markdown(raw) if path.suffix == ".ipynb" else raw
        meta, body = _frontmatter(text)
        title = meta.get("title") or path.stem.replace("-", " ").capitalize()
        url = QISKIT_DOCS_URL + path.stem
        chunks.extend(chunk_document("qiskit_docs", path.stem, title, url, clean_mdx(body)))
    return chunks


# --- arXiv abstracts ---------------------------------------------------------------

ATOM = {"atom": "http://www.w3.org/2005/Atom"}


def parse_arxiv_feed(xml_text):
    """Papers from an arXiv API Atom response: id (no version), title, abstract, authors, year."""
    papers = []
    for entry in ET.fromstring(xml_text).findall("atom:entry", ATOM):
        raw_id = entry.findtext("atom:id", default="", namespaces=ATOM)
        arxiv_id = re.sub(r"v\d+$", "", raw_id.rsplit("/abs/", 1)[-1])
        if not arxiv_id:
            continue
        papers.append({
            "id": arxiv_id,
            "title": " ".join(entry.findtext("atom:title", default="", namespaces=ATOM).split()),
            "abstract": " ".join(entry.findtext("atom:summary", default="", namespaces=ATOM).split()),
            "authors": [a.findtext("atom:name", default="", namespaces=ATOM) for a in entry.findall("atom:author", ATOM)],
            "year": entry.findtext("atom:published", default="", namespaces=ATOM)[:4],
        })
    return papers


def arxiv_chunks(papers):
    chunks, seen = [], set()
    for paper in papers:
        if paper["id"] in seen or not paper["abstract"]:
            continue
        seen.add(paper["id"])
        authors = paper["authors"]
        byline = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        doc_id = paper["id"].replace("/", "_")
        chunks.append({
            "id": f"arxiv:{doc_id}:0",
            "source": "arxiv",
            "doc_id": doc_id,
            "title": paper["title"],
            "section": f"{byline} ({paper['year']})" if byline else paper["year"],
            "url": ARXIV_URL + paper["id"],
            "content": paper["abstract"],
        })
    return chunks
