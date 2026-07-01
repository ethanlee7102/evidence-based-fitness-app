"""Apply each per-paper-cap variant to ONE frozen reranked pool — noise-free cap A/B.

The cap is pure post-processing on the reranked pool, so the only honest way to compare
cap settings is to hold the pool fixed and vary only the cap. (Capturing a fresh retrieval
per config injects Voyage-embedding non-determinism — ~22% of top-5s differ run-to-run.)

Input: a frozen pool fixture from
    capture_rag_fixture --retrieval-only --top-n 20 --output <pool>.json
Output: one judged-ready fixture per cap config (top-5, full chunk text, empty answer —
judge with `evaluate_rag --from-fixture <out> --metrics retrieval`).

Usage:
    python -m scripts.derive_cap_fixtures --pool results/rag_outputs_fixture_voyage_pool20.json
"""

import argparse
import json
from pathlib import Path

from src.core.reranker import apply_per_paper_cap, apply_score_gated_cap
from src.schema.rag import ChunkResponse

TOP_N = 5

# name -> (description, function mapping reranked chunks -> kept top-5)
CONFIGS = {
    "nocap": ("no cap", lambda ch: apply_per_paper_cap(ch, cap=0, top_n=TOP_N)),
    "cap2": ("hard cap=2", lambda ch: apply_per_paper_cap(ch, cap=2, top_n=TOP_N)),
    "sgnorm010": (
        "score-gated cap=2, normalized margin 0.10",
        lambda ch: apply_score_gated_cap(ch, cap=2, margin=0.10, top_n=TOP_N, normalize=True),
    ),
    "sgnorm015": (
        "score-gated cap=2, normalized margin 0.15 (peak discrimination)",
        lambda ch: apply_score_gated_cap(ch, cap=2, margin=0.15, top_n=TOP_N, normalize=True),
    ),
}


def main() -> None:
    ap = argparse.ArgumentParser(description="Derive per-cap top-5 fixtures from one frozen pool")
    ap.add_argument("--pool", required=True, help="Frozen reranked pool fixture (top-N, full text)")
    ap.add_argument("--out-prefix", default="results/frozen_", help="Output path prefix")
    args = ap.parse_args()

    pool = json.loads(Path(args.pool).read_text())
    cases = pool["cases"]
    print(f"Loaded frozen pool: {len(cases)} cases from {args.pool}")

    for name, (desc, fn) in CONFIGS.items():
        out_cases = []
        for case in cases:
            # chunks are stored in reranked order with rerank_score — rebuild and cap.
            chunks = [ChunkResponse(**c) for c in case["chunks"]]
            kept = fn(chunks)
            entry = dict(case)  # carry id/question/expected_facts/category/etc.
            entry["answer"] = ""  # retrieval-only judging (generation metrics skipped)
            entry["chunks"] = [c.model_dump(mode="json") for c in kept]
            out_cases.append(entry)

        out = {
            "metadata": {
                "derived_from": args.pool,
                "cap_config": name,
                "cap_description": desc,
                "top_n": TOP_N,
                "total_cases": len(out_cases),
            },
            "cases": out_cases,
        }
        path = f"{args.out_prefix}{name}.json"
        Path(path).write_text(json.dumps(out, indent=2, default=str))
        avg = sum(len(c["chunks"]) for c in out_cases) / len(out_cases)
        print(f"  {name:<10} ({desc}): wrote {path}  (avg {avg:.2f} chunks/case)")


if __name__ == "__main__":
    main()
