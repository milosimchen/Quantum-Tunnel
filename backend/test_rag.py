"""
Retrieval checks that need no network or API keys: chunking, source parsing,
prompt formatting and citation validation.

    python test_rag.py
"""

import json
import os
import tempfile
from pathlib import Path

import rag
from rag_sources import (
    MAX_CHUNK_CHARS, arxiv_chunks, chunk_document, clean_mdx, content_hash, lesson_chunks,
    lesson_markdown, notebook_markdown, parse_arxiv_feed, qiskit_guide_chunks, split_sections, split_text,
)

results = []


def check(name, condition):
    results.append(bool(condition))
    print(("PASS " if condition else "FAIL ") + name)


# --- Splitting ---------------------------------------------------------------------------

sections = split_sections("Intro text\n\n# A\nalpha\n## B\nbeta\n```python\n# not a heading\n```\n### C\ngamma")
check("Sections split on #, ## and ###", [h for h, _ in sections] == [None, "A", "B", "C"])
check("A # inside a code fence is not a heading", "# not a heading" in sections[2][1])

long_paragraphs = "\n\n".join(("Sentence number %d is here. " % i) * 20 for i in range(10))
pieces = split_text(long_paragraphs)
check("Every piece fits the size limit", all(len(p) <= MAX_CHUNK_CHARS for p in pieces))
check("No text is lost when splitting", sum(len(p.replace("\n", "").replace(" ", "")) for p in pieces)
      == len(long_paragraphs.replace("\n", "").replace(" ", "")))
check("One giant word is still cut to size", all(len(p) <= MAX_CHUNK_CHARS for p in split_text("x" * 5000)))

chunks = chunk_document("qiskit_docs", "demo", "Demo", "https://example.org/demo", "# Demo\nfirst\n## Part two\nsecond")
check("A heading equal to the title is dropped as a section", chunks[0]["section"] is None)
check("Chunk ids are unique and ordered", [c["id"] for c in chunks] == ["qiskit_docs:demo:0", "qiskit_docs:demo:1"])

a = dict(chunks[0])
b = dict(chunks[0], content=chunks[0]["content"] + "!")
check("Content hash changes when the text changes", content_hash(a) != content_hash(b))
check("Content hash is stable", content_hash(a) == content_hash(dict(chunks[0])))

# --- Lessons --------------------------------------------------------------------------

lesson = {
    "id": "bell-states", "title": "Bell states", "trackTitle": "Entanglement",
    "blocks": [
        {"type": "p", "text": "The four Bell states are maximally entangled."},
        {"type": "math", "tex": "|\\Phi^+\\rangle"},
        {"type": "circuit", "numQubits": 2, "gates": [["h", [0]], ["cx", [0, 1]]], "caption": "H then CX."},
        {"type": "check", "question": "Is it separable?", "choices": ["Yes", "No"], "answer": 1, "explanation": "It is entangled."},
        {"type": "practice", "challenges": ["bell_phi_plus"]},
    ],
}
text = lesson_markdown(lesson)
check("Lesson prose, math, circuit caption and quiz answer are kept",
      all(s in text for s in ("maximally entangled", "$$|\\Phi^+\\rangle$$", "H on [0]", "Answer: No. It is entangled.")))
check("Practice blocks are skipped", "bell_phi_plus" not in text)
lc = lesson_chunks([lesson])
check("Lesson chunks link to the in-app lesson", lc[0]["url"] == "/study/bell-states" and lc[0]["section"] == "Entanglement")

# --- Qiskit guides ------------------------------------------------------------------------

mdx = """import Foo from "bar"
{/* cspell:ignore xyz */}
<span id="anchor" />
# Choose a mode
<Admonition type="note">Batch is cheaper.</Admonition>
See [the estimator guide](/docs/guides/estimator) for details.
"""
cleaned = clean_mdx(mdx)
check("MDX imports, comments and components are stripped", all(s not in cleaned for s in ("import", "cspell", "<span", "Admonition")))
check("Component children and link text survive", "Batch is cheaper." in cleaned and "the estimator guide for details" in cleaned)

code_mdx = 'import Foo from "bar"\nProse.\n```python\nimport numpy as np\nx = List<Int>\n```\n'
check("Code blocks keep their imports and angle brackets", "import numpy as np" in clean_mdx(code_mdx)
      and "List<Int>" in clean_mdx(code_mdx) and "Foo" not in clean_mdx(code_mdx))

notebook = {"cells": [
    {"cell_type": "markdown", "metadata": {}, "source": ["---\n", "title: Bit ordering\n", "---\n", "Qiskit is little-endian."]},
    {"cell_type": "markdown", "metadata": {"tags": ["version-info"]}, "source": ["generated"]},
    {"cell_type": "code", "metadata": {}, "source": ["qc = QuantumCircuit(2)"], "outputs": [{"text": "noise"}]},
]}
nb = notebook_markdown(json.dumps(notebook))
check("Notebook keeps markdown and code, drops version cells and outputs",
      "little-endian" in nb and "QuantumCircuit(2)" in nb and "generated" not in nb and "noise" not in nb)

with tempfile.TemporaryDirectory() as tmp:
    Path(tmp, "bit-ordering.ipynb").write_text(json.dumps(notebook))
    Path(tmp, "changelog-qiskit.mdx").write_text("---\ntitle: Changelog\n---\nskip me")
    Path(tmp, "_toc.json").write_text("{}")
    guide = qiskit_guide_chunks(tmp)
check("Guides are titled from front matter and changelogs are skipped",
      len(guide) == 1 and guide[0]["title"] == "Bit ordering" and guide[0]["doc_id"] == "bit-ordering")
check("Guide chunks link to the published docs page", guide[0]["url"] == "https://quantum.cloud.ibm.com/docs/guides/bit-ordering")

# --- arXiv -----------------------------------------------------------------------------

feed = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/quant-ph/0403025v2</id>
    <published>2004-03-03T00:00:00Z</published>
    <title>Universal quantum computation with ideal
      Clifford gates and noisy ancillas</title>
    <summary>  We consider a model of quantum computation in which the set of
      elementary operations is limited to Clifford unitaries.  </summary>
    <author><name>Sergey Bravyi</name></author>
    <author><name>Alexei Kitaev</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/1208.0928v2</id>
    <published>2012-08-04T00:00:00Z</published>
    <title>Surface codes: Towards practical large-scale quantum computation</title>
    <summary>This article provides an introduction to surface code quantum computing.</summary>
    <author><name>A</name></author><author><name>B</name></author><author><name>C</name></author><author><name>D</name></author>
  </entry>
</feed>"""
papers = parse_arxiv_feed(feed)
check("arXiv ids lose their version suffix", [p["id"] for p in papers] == ["quant-ph/0403025", "1208.0928"])
check("arXiv titles and abstracts are whitespace-normalised",
      papers[0]["title"] == "Universal quantum computation with ideal Clifford gates and noisy ancillas"
      and papers[0]["abstract"].startswith("We consider"))
ac = arxiv_chunks(papers + papers)
check("Duplicate papers across topics are indexed once", len(ac) == 2)
check("Old-style arXiv ids are safe as doc ids and keep a working URL",
      ac[0]["doc_id"] == "quant-ph_0403025" and ac[0]["url"] == "https://arxiv.org/abs/quant-ph/0403025")
check("Long author lists are shortened", ac[1]["section"] == "A, B, C et al. (2012)")

# --- Retrieval helpers ----------------------------------------------------------------------

for key in ("GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "RAG_ENABLED"):
    os.environ.pop(key, None)
check("Retrieval is off without keys", not rag.enabled())
os.environ.update(GEMINI_API_KEY="k", SUPABASE_URL="https://x.supabase.co", SUPABASE_SERVICE_ROLE_KEY="s")
check("Retrieval turns on with all three keys", rag.enabled())
os.environ["RAG_ENABLED"] = "0"
check("RAG_ENABLED=0 switches it off", not rag.enabled())

history = [{"role": "user", "content": "What is a magic state?"}, {"role": "assistant", "content": "..."}]
check("Follow-up questions carry the previous question into retrieval",
      rag.retrieval_query("How is it distilled?", history) == "What is a magic state?\nHow is it distilled?")
check("Keyword query ORs distinct words and drops short ones",
      rag.keyword_query("What is the T gate's T-count, the T-count?") == "what or the or gate or t-count")
check("Embeddings are scaled to unit length", abs(sum(x * x for x in rag.normalize([3.0, 4.0])) - 1) < 1e-12
      and rag.normalize([3.0, 4.0]) == [0.6, 0.8])
check("Legacy JWT service keys also go in the Authorization header", rag.auth_header("eyJhbGciOi.x.y") == {"Authorization": "Bearer eyJhbGciOi.x.y"})
check("New sb_secret_ keys are sent only as apikey", rag.auth_header("sb_secret_abc") == {})
check("Vectors are sent in pgvector's text format", rag.vector_literal([0.5, -1.0, 2e-9]) == "[0.5,-1,2e-09]")

class _Reply:
    ok, status_code = True, 200
    def json(self):
        return {"embeddings": [{"values": [3.0, 4.0]}]}


calls = []
def _flaky_post(*args, **kwargs):
    calls.append(1)
    if len(calls) == 1:
        raise rag.requests.Timeout("read timed out")
    return _Reply()


real_post, real_sleep = rag.requests.post, rag.time.sleep
rag.requests.post, rag.time.sleep = _flaky_post, lambda seconds: None
try:
    vectors = rag.embed(["text"], "document")
finally:
    rag.requests.post, rag.time.sleep = real_post, real_sleep
check("A timed-out embedding request is retried instead of failing", len(calls) == 2 and vectors == [[0.6, 0.8]])

class _Quota429:
    status_code, ok = 429, False
    def __init__(self, quota):
        self.quota = quota
    def json(self):
        return {"error": {"details": [
            {"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [{"quotaId": self.quota}]},
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "17s"},
        ]}}


check("429 details give the quota id and Google's retry delay",
      rag.quota_details(_Quota429("EmbedContentRequestsPerMinutePerProjectPerModel-FreeTier")) == ("EmbedContentRequestsPerMinutePerProjectPerModel-FreeTier", 18.0))
real_post = rag.requests.post
rag.requests.post = lambda *a, **k: _Quota429("EmbedContentRequestsPerDayPerProjectPerModel-FreeTier")
try:
    rag.embed(["text"], "document")
    stopped = False
except rag.RetrievalError as e:
    stopped = "daily quota" in str(e)
finally:
    rag.requests.post = real_post
check("A daily-quota 429 stops at once with a clear message instead of retrying", stopped)

retrieved = [
    {"source": "lesson", "doc_id": "bell-states", "title": "Bell states", "section": "Entanglement", "content": "x" * 3000},
    {"source": "qiskit_docs", "doc_id": "bit-ordering", "title": "Bit ordering", "url": "https://quantum.cloud.ibm.com/docs/guides/bit-ordering", "content": "y"},
    {"source": "qiskit_docs", "doc_id": "bit-ordering", "title": "Bit ordering", "url": "https://quantum.cloud.ibm.com/docs/guides/bit-ordering", "content": "z"},
]
block = rag.format_sources(retrieved)
check("Sources are numbered in rank order", block.count("<source id=") == 3 and '<source id="S2" kind="Qiskit documentation">' in block)
check("Long sources are truncated in the prompt", "x" * rag.MAX_SOURCE_CHARS not in block)
check("No sources gives an empty block", rag.format_sources([]) == "")

cited = rag.validate_citations(["S2", "S9", "S1", "s1", "Q", "S3", "S0"], retrieved)
check("Unknown, malformed and out-of-range citations are dropped", [c["id"] for c in cited] == ["S2", "S1"])
check("Two chunks of the same document are cited once", sum(c["title"] == "Bit ordering" for c in cited) == 1)
check("Lesson citations route inside the app; others link out",
      cited[1].get("path") == "/study/bell-states" and "url" not in cited[1] and cited[0]["url"].startswith("https://"))
check("Citations without retrieval resolve to nothing", rag.validate_citations(["S1"], []) == [])

print(f"\n{sum(results)} / {len(results)} tests passed.")
if not all(results):
    raise SystemExit(1)
