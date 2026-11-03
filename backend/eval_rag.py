"""
Measure retrieval quality on a fixed question set (rag_data/eval_questions.json).

    python eval_rag.py              # search as the copilot runs it (vector-only unless RAG_HYBRID=1)
    python eval_rag.py --compare    # vector-only vs. hybrid

A question counts as answered at rank r if the r-th retrieved chunk comes from
one of its expected documents (lessons and Qiskit guides) or, for arXiv
questions, from a paper whose title contains one of the expected phrases.
Reports hit rate at 1, 3 and 6 (the copilot's default k) and mean reciprocal
rank over the top 10, overall and per source. This tests retrieval only; no
LLM is called.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")

import rag  # noqa: E402

DEPTH = 10
CACHE = HERE / "rag_data" / ".query_embeddings.json"   # gitignored; keyed by model and question


def query_vectors(questions):
    """Embed each question once, reusing cached vectors so re-runs cost no quota."""
    try:
        cache = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        cache = {}
    key = lambda q: hashlib.sha256(f"{rag.EMBED_MODEL}|{rag.EMBED_DIM}|{q}".encode()).hexdigest()
    missing = [q["question"] for q in questions if key(q["question"]) not in cache]
    for start in range(0, len(missing), 50):
        batch = missing[start:start + 50]
        cache.update({key(q): v for q, v in zip(batch, rag.embed(batch, "query"))})
        CACHE.write_text(json.dumps(cache))
    return {q["question"]: cache[key(q["question"])] for q in questions}


def first_hit(question, rows):
    for rank, row in enumerate(rows, start=1):
        if row["source"] != question["source"]:
            continue
        if "doc_ids" in question and row["doc_id"] in question["doc_ids"]:
            return rank
        if "title_contains" in question and any(t in row["title"].lower() for t in question["title_contains"]):
            return rank
    return None


def evaluate(questions, vectors, keyword):
    ranks = []
    for q in questions:
        rows = rag.search(q["question"], k=DEPTH, keyword=keyword, vector=vectors[q["question"]])
        ranks.append((q, first_hit(q, rows)))
    return ranks


def summarize(ranks):
    def stats(subset):
        n = len(subset)
        hit = lambda k: sum(1 for _, r in subset if r and r <= k) / n
        mrr = sum(1 / r for _, r in subset if r) / n
        return {"n": n, "hit@1": hit(1), "hit@3": hit(3), "hit@6": hit(6), "mrr@10": mrr}
    by_source = defaultdict(list)
    for q, r in ranks:
        by_source[q["source"]].append((q, r))
    return {"all": stats(ranks), **{s: stats(v) for s, v in sorted(by_source.items())}}


def print_table(name, summary):
    print(f"\n{name}")
    print(f"{'':12} {'n':>3} {'hit@1':>6} {'hit@3':>6} {'hit@6':>6} {'MRR@10':>7}")
    for key, s in summary.items():
        print(f"{key:12} {s['n']:3d} {s['hit@1']:6.2f} {s['hit@3']:6.2f} {s['hit@6']:6.2f} {s['mrr@10']:7.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--questions", default=str(HERE / "rag_data" / "eval_questions.json"))
    ap.add_argument("--compare", action="store_true", help="run vector-only and hybrid search side by side")
    ap.add_argument("--show-misses", action="store_true")
    args = ap.parse_args()
    if not rag.enabled():
        raise SystemExit("Set GEMINI_API_KEY, SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env first.")

    questions = json.loads(Path(args.questions).read_text())
    vectors = query_vectors(questions)
    if args.compare:
        runs = [("Vector only", False), ("Hybrid (vector + keyword)", True)]
    else:
        runs = [("Hybrid (vector + keyword)" if rag.HYBRID else "Vector only", rag.HYBRID)]
    for name, keyword in runs:
        ranks = evaluate(questions, vectors, keyword)
        print_table(name, summarize(ranks))
        if args.show_misses:
            for q, r in ranks:
                if not r or r > 6:
                    print(f"  rank {r or '>10':>3}: {q['question']}")


if __name__ == "__main__":
    main()
