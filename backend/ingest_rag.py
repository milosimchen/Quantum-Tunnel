"""
Build or refresh the copilot's retrieval index in Supabase.

    python ingest_rag.py --qiskit-docs ../../qiskit-documentation
    python ingest_rag.py --only lesson            # re-index lessons after editing them

Sources:
  lesson       Quantum Tunnel's lessons, exported with frontend/scripts/export-lessons.mjs (needs Node)
  qiskit_docs  docs/guides from a clone of github.com/Qiskit/documentation
  arxiv        abstracts from the arXiv API for the topics in rag_data/arxiv_topics.json

Only chunks whose text changed are re-embedded, and chunks that no longer
exist are deleted, so re-running is cheap. Needs GEMINI_API_KEY, SUPABASE_URL
and SUPABASE_SERVICE_ROLE_KEY in backend/.env.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")

import rag  # noqa: E402  (reads env at import)
from rag_sources import arxiv_chunks, content_hash, embedding_text, lesson_chunks, parse_arxiv_feed, qiskit_guide_chunks  # noqa: E402

ARXIV_API = "http://export.arxiv.org/api/query"
EMBED_BATCH = 50
UPSERT_BATCH = 100


def load_lessons():
    script = HERE.parent / "frontend" / "scripts" / "export-lessons.mjs"
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def fetch_arxiv(topics_file, per_topic):
    papers = []
    for topic in json.loads(Path(topics_file).read_text()):
        params = {"search_query": topic["query"], "max_results": per_topic, "sortBy": "relevance"}
        response = requests.get(f"{ARXIV_API}?{urlencode(params)}", timeout=60)
        response.raise_for_status()
        found = parse_arxiv_feed(response.text)
        print(f"  arxiv: {len(found):3d} papers for {topic['name']}")
        papers.extend(found)
        time.sleep(3)  # arXiv asks for at most one request every three seconds
    return papers


def existing_hashes(source):
    rows, offset = {}, 0
    while True:
        page = rag.supabase("GET", f"rag_chunks?select=id,content_hash&source=eq.{source}&order=id&limit=1000&offset={offset}")
        rows.update({r["id"]: r["content_hash"] for r in page})
        if len(page) < 1000:
            return rows
        offset += 1000


def sync(source, chunks, dry_run=False):
    for chunk in chunks:
        chunk["content_hash"] = content_hash(chunk)
    current = existing_hashes(source) if not dry_run else {}
    changed = [c for c in chunks if current.get(c["id"]) != c["content_hash"]]
    stale = sorted(set(current) - {c["id"] for c in chunks})
    print(f"{source}: {len(chunks)} chunks, {len(changed)} new or changed, {len(stale)} stale")
    if dry_run:
        return

    for start in range(0, len(changed), EMBED_BATCH):
        batch = changed[start:start + EMBED_BATCH]
        vectors = rag.embed([embedding_text(c) for c in batch], "document")
        for chunk, vector in zip(batch, vectors):
            chunk["embedding"] = rag.vector_literal(vector)
        print(f"  embedded {min(start + EMBED_BATCH, len(changed))}/{len(changed)}")

    for start in range(0, len(changed), UPSERT_BATCH):
        rows = [{k: c.get(k) for k in ("id", "source", "doc_id", "title", "section", "url", "content", "content_hash", "embedding")}
                for c in changed[start:start + UPSERT_BATCH]]
        rag.supabase("POST", "rag_chunks?on_conflict=id", json=rows,
                     headers={"Prefer": "resolution=merge-duplicates,return=minimal"})

    for start in range(0, len(stale), 100):
        ids = ",".join(f'"{i}"' for i in stale[start:start + 100])
        rag.supabase("DELETE", f"rag_chunks?id=in.({ids})", headers={"Prefer": "return=minimal"})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["lesson", "qiskit_docs", "arxiv"], action="append",
                    help="index just these sources (repeatable); default is all three")
    ap.add_argument("--qiskit-docs", help="path to a clone of github.com/Qiskit/documentation")
    ap.add_argument("--arxiv-topics", default=str(HERE / "rag_data" / "arxiv_topics.json"))
    ap.add_argument("--arxiv-per-topic", type=int, default=25)
    ap.add_argument("--dry-run", action="store_true", help="chunk and report counts without embedding or writing")
    args = ap.parse_args()

    sources = args.only or ["lesson", "qiskit_docs", "arxiv"]
    if not args.dry_run and not rag.enabled():
        sys.exit("Set GEMINI_API_KEY, SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env first.")

    if "lesson" in sources:
        sync("lesson", lesson_chunks(load_lessons()), args.dry_run)
    if "qiskit_docs" in sources:
        if not args.qiskit_docs:
            sys.exit("--qiskit-docs is required to index the Qiskit guides (or leave it out with --only).")
        sync("qiskit_docs", qiskit_guide_chunks(Path(args.qiskit_docs) / "docs" / "guides"), args.dry_run)
    if "arxiv" in sources:
        sync("arxiv", arxiv_chunks(fetch_arxiv(args.arxiv_topics, args.arxiv_per_topic)), args.dry_run)


if __name__ == "__main__":
    main()
