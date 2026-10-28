"""
Measure retrieval quality on a fixed question set (rag_data/eval_questions.json).

    python eval_rag.py              # hybrid search, as the copilot uses it
    python eval_rag.py --compare    # hybrid vs. vector-only

A question counts as answered at rank r if the r-th retrieved chunk comes from
one of its expected documents (lessons and Qiskit guides) or, for arXiv
questions, from a paper whose title contains one of the expected phrases.
Reports hit rate at 1, 3 and 6 (the copilot's default k) and mean reciprocal
rank over the top 10, overall and per source. This tests retrieval only; no
LLM is called.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")

import rag  # noqa: E402

DEPTH = 10


def first_hit(question, rows):
    for rank, row in enumerate(rows, start=1):
        if row["source"] != question["source"]:
            continue
        if "doc_ids" in question and row["doc_id"] in question["doc_ids"]:
            return rank
        if "title_contains" in question and any(t in row["title"].lower() for t in question["title_contains"]):
            return rank
    return None


def evaluate(questions, keyword):
    ranks = []
    for q in questions:
        rank = first_hit(q, rag.search(q["question"], k=DEPTH, keyword=keyword))
        ranks.append((q, rank))
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
    ap.add_argument("--compare", action="store_true", help="also run vector-only search for comparison")
    ap.add_argument("--show-misses", action="store_true")
    args = ap.parse_args()
    if not rag.enabled():
        raise SystemExit("Set VOYAGE_API_KEY, SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env first.")

    questions = json.loads(Path(args.questions).read_text())
    runs = [("Hybrid (vector + keyword)", True)] + ([("Vector only", False)] if args.compare else [])
    for name, keyword in runs:
        ranks = evaluate(questions, keyword)
        print_table(name, summarize(ranks))
        if args.show_misses:
            for q, r in ranks:
                if not r or r > 6:
                    print(f"  rank {r or '>10':>3}: {q['question']}")


if __name__ == "__main__":
    main()
