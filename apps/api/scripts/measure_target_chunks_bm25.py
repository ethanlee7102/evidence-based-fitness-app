"""Measure the BM25 (lexical) rank of the verified target chunks.

Lexical counterpart to the vector-similarity `diagnose` in
`measure_target_chunks.py`. The question it answers: would a hybrid (lexical)
retriever surface the recall-bound target chunks that *vector* search buries
deep in the ranking? If BM25 ranks them shallow, hybrid is worth building; if
BM25 also buries them, hybrid is not the lever for this target set.

Builds a THROWAWAY in-memory BM25 index over the full corpus (no persistent
index, no migration, no new infra) and reports each target's lexical rank plus
the same rank histogram the vector measurement prints, so the two are directly
comparable.

Usage:
    python -m scripts.measure_target_chunks_bm25
    python -m scripts.measure_target_chunks_bm25 --output results/target_chunks_bm25.json
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from rank_bm25 import BM25Okapi

from scripts.measure_target_chunks import TARGETS, _bucket, _load_queries, _surname
from src.db import get_supabase

_TOKEN = re.compile(r"[a-z0-9]+")


def _tok(text: str) -> list[str]:
    """Minimal BM25 tokenizer: lowercase, split on word chars. IDF down-weights
    common terms naturally, so no stopword list is needed for this measurement."""
    return _TOKEN.findall(text.lower())


def _load_corpus() -> list[dict]:
    """Pull every chunk's text + (authors, year, chunk_index) via paginated select
    (Supabase REST caps each page at 1000 rows)."""
    sb = get_supabase()
    rows: list[dict] = []
    page, size = 0, 1000
    while True:
        res = (
            sb.table("chunks")
            .select("chunk_index, text, papers(authors, year)")
            .range(page * size, page * size + size - 1)
            .execute()
        )
        if not res.data:
            break
        rows.extend(res.data)
        if len(res.data) < size:
            break
        page += 1
    return rows


def measure_bm25() -> dict:
    queries = _load_queries()

    corpus = _load_corpus()
    tokenized = [_tok(r["text"]) for r in corpus]
    bm25 = BM25Okapi(tokenized)
    # Per-row (authors, year, chunk_index) for matching targets.
    meta = [
        ((r.get("papers") or {}).get("authors") or "",
         (r.get("papers") or {}).get("year"),
         r["chunk_index"])
        for r in corpus
    ]

    cases_out = []
    buckets: Counter = Counter()
    total = 0

    for cid, info in TARGETS.items():
        scores = bm25.get_scores(_tok(queries[cid]))
        order = sorted(range(len(corpus)), key=lambda i: scores[i], reverse=True)
        pos = [0] * len(corpus)  # corpus row index -> 1-based rank
        for p, i in enumerate(order):
            pos[i] = p + 1

        top20_papers = Counter(
            f"{_surname(meta[i][0])} {meta[i][1]}" for i in order[:20]
        )
        dom_paper, dom_count = top20_papers.most_common(1)[0] if top20_papers else ("?", 0)

        targets_out = []
        for (asub, yr), idxs in info["targets"].items():
            for idx in sorted(idxs):
                rank = None
                score = None
                for i, (a, y, ci) in enumerate(meta):
                    if asub.lower() in a.lower() and y == yr and ci == idx:
                        rank = pos[i]
                        score = float(scores[i])
                        break
                total += 1
                buckets[_bucket(rank)] += 1
                targets_out.append(
                    {"paper": f"{asub} {yr}", "chunk": idx, "rank": rank,
                     "bm25_score": round(score, 3) if score is not None else None}
                )

        cases_out.append(
            {
                "id": cid,
                "tier": info.get("tier", "core"),
                "dominant_paper_in_top20": f"{dom_paper} ({dom_count}/20)",
                "targets": targets_out,
            }
        )

    return {
        "mode": "bm25",
        "corpus_size": len(corpus),
        "rank_histogram": dict(sorted(buckets.items(), key=lambda kv: kv[0])),
        "total_targets": total,
        "cases": cases_out,
    }


def _print(report: dict) -> None:
    for c in report["cases"]:
        print("=" * 80)
        print(f"{c['id']}  (lexical dominant: {c['dominant_paper_in_top20']})")
        for t in c["targets"]:
            where = f"rank {t['rank']:>5} (bm25 {t['bm25_score']})" if t["rank"] else "not found"
            print(f"    {t['paper']:<22} ch{t['chunk']:<3}: {where}")
    print("=" * 80)
    print(f"BM25 RANK HISTOGRAM (corpus={report['corpus_size']} chunks):")
    order = ["1-5", "6-20", "21-60", "61-200", "201-1000", ">1000"]
    for b in order:
        n = report["rank_histogram"].get(b, 0)
        print(f"  {b:>9}: {n:>2} {'#' * n}")
    print(f"  total targets: {report['total_targets']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure BM25 lexical rank of target chunks")
    ap.add_argument("--output", type=str, help="Save report JSON to this path")
    args = ap.parse_args()

    report = measure_bm25()
    _print(report)
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2))
        print(f"\nSaved report to {args.output}")


if __name__ == "__main__":
    main()
