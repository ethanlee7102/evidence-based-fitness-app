"""Measure retrieval against the verified target chunks for the recall-bound cases.

Judge-independent success metric for Phase 2 retrieval work (diversification,
top_k bump, reranking). For each of the 6 retrieval-bound recall failures, the
recall diagnostic verified the *specific* chunks that successful retrieval must
surface into top-k (see context/archive/RETRIEVAL-TARGET-CHUNKS.md). This script
runs live retrieval for those queries and reports:

    (primary target chunks in top-5) / (total primary target chunks)

independent of the LLM judge. Run before and after each retrieval change and
diff the ratio — if it rises, retrieval improved; if it rises but eval recall
doesn't, the bottleneck has shifted to the judge.

Usage:
    python -m scripts.measure_target_chunks                       # print only
    python -m scripts.measure_target_chunks --top-k 20            # candidate depth
    python -m scripts.measure_target_chunks --output results/target_chunks_after_rerank.json
"""

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path

from src.core.retrieval import retrieve_chunks

DATASET = Path("tests/eval/test_dataset.json")

# Verified primary target chunks per retrieval-bound case.
# Source: context/archive/RETRIEVAL-TARGET-CHUNKS.md (chunk indices verified by
# end-to-end chunk reading). (first-author-substring, year) -> {chunk_index, ...}
TARGETS: dict[str, dict] = {
    # --- core 6 (original diagnostic, recall=2 cases) ---
    "NUT-016": {
        "tier": "core",
        "doc_current_top5": "all 5 Kazeminasab",
        "targets": {("Conde", 2024): {20}, ("Aragon", 2022): {4}},
    },
    "BC-010": {
        "tier": "core",
        "doc_current_top5": "2 McCarthy & Berg + 3 Willoughby",
        "targets": {("Ruiz", 2021): {7, 1}},
    },
    "GEN-004": {
        "tier": "core",
        "doc_current_top5": "all 5 Nuckols",
        "targets": {("Refalo", 2025): {1, 33}, ("James", 2025): {22, 23}},
    },
    "CVD-001": {
        "tier": "core",
        "doc_current_top5": "all 5 Edwards",
        "targets": {("Correia", 2023): {0, 4}},
    },
    "BFR-004": {
        "tier": "core",
        "doc_current_top5": "all 5 Nascimento",
        "targets": {("Patterson", 2019): {18, 21, 2}},
    },
    "STR-010": {
        "tier": "core",
        "doc_current_top5": "Wang{2,0,30} + Thapa{36,33}",
        "targets": {("Thapa", 2024): {4}, ("Wang", 2023): {1}},
    },
    # --- extended (added 2026-05-30 from the full recall<=3 sweep) ---
    "GEN-001": {
        "tier": "ext",
        "doc_current_top5": "all 5 Delaire 2025",
        "targets": {("Govindasamy", 2025): {2, 3}, ("øien", 2025): {9, 14}},
    },
    "NUT-014": {
        "tier": "ext",
        "doc_current_top5": "4/5 reference-list chunks",
        "targets": {("Williamson", 2021): {6}, ("Keenan", 2020): {31}, ("Ho", 2024): {21}},
    },
    "NUT-022": {
        "tier": "ext",
        "doc_current_top5": "Han-saturated (11/20)",
        "targets": {("Wicin", 2019): {4, 10}},
    },
    "BC-004": {
        "tier": "ext",
        "doc_current_top5": "Xie-saturated",
        "targets": {("Ruiz", 2021): {7}, ("Lahav", 2026): {8}},
    },
    "BFR-001": {
        "tier": "ext",
        "doc_current_top5": "definitional + reference chunks",
        "targets": {("Davids", 2023): {7, 8, 12, 13}, ("Patterson", 2019): {5, 8}},
    },
    "PROG-006": {
        "tier": "ext",  # facts 1-2 only; facts 2-3 have test-authoring issues
        "doc_current_top5": "4 Iversen + 1 Krzysztofik",
        "targets": {("Fonseca", 2023): {0, 1, 78}},
    },
}


def _surname(authors: str) -> str:
    """First-author surname for display (handles 'Smith et al.' / 'Smith, J.')."""
    if not authors:
        return "?"
    return authors.replace(",", " ").split()[0]


def _load_queries() -> dict[str, str]:
    ds = json.loads(DATASET.read_text())
    cases = ds["test_cases"] if isinstance(ds, dict) and "test_cases" in ds else ds
    return {c["id"]: c["question"] for c in cases}


async def measure(top_k: int) -> dict:
    queries = _load_queries()
    cases_out = []
    grand_primary = 0
    grand_top5 = 0
    grand_top20 = 0

    for cid, info in TARGETS.items():
        res = await retrieve_chunks(queries[cid], top_k=top_k)
        ranked = [(c.authors, c.year, c.chunk_index) for c in res.chunks]
        top5_comp = Counter(f"{_surname(a)} {y}" for a, y, _ in ranked[:5])

        targets_out = []
        for (asub, yr), idxs in info["targets"].items():
            for idx in sorted(idxs):
                rank = None
                for i, (a, y, ci) in enumerate(ranked):
                    if asub.lower() in a.lower() and y == yr and ci == idx:
                        rank = i + 1
                        break
                grand_primary += 1
                if rank and rank <= 5:
                    grand_top5 += 1
                if rank and rank <= 20:
                    grand_top20 += 1
                targets_out.append(
                    {"paper": f"{asub} {yr}", "chunk": idx, "rank": rank}
                )

        in5 = sum(1 for t in targets_out if t["rank"] and t["rank"] <= 5)
        in20 = sum(1 for t in targets_out if t["rank"] and t["rank"] <= 20)
        cases_out.append(
            {
                "id": cid,
                "tier": info.get("tier", "core"),
                "doc_current_top5": info["doc_current_top5"],
                "actual_top5_papers": dict(top5_comp),
                "primary_total": len(targets_out),
                "primary_in_top5": in5,
                "primary_in_top20": in20,
                "targets": targets_out,
            }
        )

    def _subtotal(tier):
        cs = [c for c in cases_out if c["tier"] == tier]
        tot = sum(c["primary_total"] for c in cs)
        t5 = sum(c["primary_in_top5"] for c in cs)
        t20 = sum(c["primary_in_top20"] for c in cs)
        return {"in_top5": f"{t5}/{tot}", "in_top20": f"{t20}/{tot}"}

    return {
        "top_k": top_k,
        "metric_primary_in_top5": f"{grand_top5}/{grand_primary}",
        "metric_primary_in_top20": f"{grand_top20}/{grand_primary}",
        "metric_core6": _subtotal("core"),
        "metric_extended": _subtotal("ext"),
        "cases": cases_out,
    }


def _print(report: dict) -> None:
    for c in report["cases"]:
        print("=" * 80)
        print(f"{c['id']}  (PRIMARY {c['primary_in_top5']}/{c['primary_total']} in top-5, "
              f"{c['primary_in_top20']}/{c['primary_total']} in top-20)")
        print(f"  doc-claimed current top-5: {c['doc_current_top5']}")
        print(f"  actual top-5 papers:       {c['actual_top5_papers']}")
        for t in c["targets"]:
            if t["rank"] is None:
                where = "NOT in top-20"
            elif t["rank"] <= 5:
                where = f"top-5 (rank {t['rank']})"
            else:
                where = f"top-20 (rank {t['rank']})"
            print(f"    {t['paper']} ch{t['chunk']}: {where}")
    print("=" * 80)
    print(f"ALL CASES:   {report['metric_primary_in_top5']} primary chunks in top-5 "
          f"| {report['metric_primary_in_top20']} in top-20  (top_k={report['top_k']})")
    print(f"  core 6:    {report['metric_core6']['in_top5']} in top-5 "
          f"| {report['metric_core6']['in_top20']} in top-20")
    print(f"  extended:  {report['metric_extended']['in_top5']} in top-5 "
          f"| {report['metric_extended']['in_top20']} in top-20")


async def main() -> None:
    ap = argparse.ArgumentParser(description="Measure retrieval vs verified target chunks")
    ap.add_argument("--top-k", type=int, default=20, help="Candidate depth to inspect")
    ap.add_argument("--output", type=str, help="Save report JSON to this path")
    args = ap.parse_args()

    report = await measure(args.top_k)
    _print(report)
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2))
        print(f"\nSaved report to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
