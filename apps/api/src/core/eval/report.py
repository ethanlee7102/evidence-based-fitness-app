"""Report generation for RAG evaluation — console summary + JSON export."""

import json
import logging
import statistics
from pathlib import Path

logger = logging.getLogger(__name__)

METRIC_NAMES = [
    "contextual_relevancy",
    "contextual_recall",
    "contextual_precision",
    "answer_relevancy",
    "faithfulness",
]

METRIC_SHORT = {
    "contextual_relevancy": "Rel",
    "contextual_recall": "Rec",
    "contextual_precision": "Pre",
    "answer_relevancy": "Ans",
    "faithfulness": "Fai",
}


def compute_aggregates(report: dict) -> dict:
    """Compute aggregate statistics from evaluation results.

    Adds 'aggregate', 'by_category', and 'by_difficulty' keys to the report.
    Skips failed cases and out-of-scope cases (no scores).
    """
    results = report["results"]
    scored = [r for r in results if r.get("scores") and not r.get("error")]

    if not scored:
        report["aggregate"] = {"note": "No scored results"}
        report["by_category"] = {}
        report["by_difficulty"] = {}
        return report

    # Per-metric aggregates
    aggregate = {}
    for metric in METRIC_NAMES:
        values = [
            r["scores"][metric]["score"]
            for r in scored
            if metric in r.get("scores", {})
        ]
        if values:
            aggregate[metric] = {
                "mean": round(statistics.mean(values), 2),
                "std": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
                "min": min(values),
                "max": max(values),
                "n": len(values),
            }

    # Overall
    overall_values = [r["overall_score"] for r in scored if r.get("overall_score")]
    if overall_values:
        aggregate["overall"] = {
            "mean": round(statistics.mean(overall_values), 2),
            "std": round(statistics.stdev(overall_values), 2) if len(overall_values) > 1 else 0.0,
            "min": round(min(overall_values), 2),
            "max": round(max(overall_values), 2),
            "n": len(overall_values),
        }

    report["aggregate"] = aggregate

    # By category
    categories: dict[str, list] = {}
    for r in scored:
        cat = r.get("category") or "uncategorized"
        categories.setdefault(cat, []).append(r)

    by_category = {}
    for cat, cat_results in sorted(categories.items()):
        cat_agg = {}
        for metric in METRIC_NAMES:
            values = [
                r["scores"][metric]["score"]
                for r in cat_results
                if metric in r.get("scores", {})
            ]
            if values:
                cat_agg[metric] = round(statistics.mean(values), 1)
        cat_agg["n"] = len(cat_results)
        by_category[cat] = cat_agg
    report["by_category"] = by_category

    # By difficulty
    difficulties: dict[str, list] = {}
    for r in scored:
        diff = r.get("difficulty", "unknown")
        difficulties.setdefault(diff, []).append(r)

    by_difficulty = {}
    for diff, diff_results in sorted(difficulties.items()):
        diff_agg = {}
        for metric in METRIC_NAMES:
            values = [
                r["scores"][metric]["score"]
                for r in diff_results
                if metric in r.get("scores", {})
            ]
            if values:
                diff_agg[metric] = round(statistics.mean(values), 1)
        diff_agg["n"] = len(diff_results)
        by_difficulty[diff] = diff_agg
    report["by_difficulty"] = by_difficulty

    return report


def print_summary(report: dict) -> None:
    """Print formatted console summary of evaluation results."""
    meta = report["metadata"]
    agg = report.get("aggregate", {})
    results = report["results"]

    duration_m = meta["duration_s"] / 60
    bar = "=" * 64

    print(f"\n{bar}")
    print(f"RAG Evaluation Report — {meta['timestamp'][:10]}")
    print(
        f"Model: {meta['model']} | Judge: {meta['judge_model']} | "
        f"Cases: {meta['total_cases']} run, {meta['failed_cases']} failed"
    )
    print(f"Mode: {meta['judge_mode']} | Duration: {duration_m:.1f}m")
    if meta.get("metrics_filter"):
        print(f"Metrics filter: {meta['metrics_filter']}")
    print(bar)

    # Aggregate scores
    if agg and "overall" in agg:
        print("\nAGGREGATE SCORES (mean +/- std)")
        for metric in METRIC_NAMES:
            if metric in agg:
                m = agg[metric]
                label = metric.replace("_", " ").title()
                print(f"  {label:25s} {m['mean']:.1f} +/- {m['std']:.1f}")
        print(f"  {'Overall':25s} {agg['overall']['mean']:.2f}")
    else:
        print("\nNo aggregate scores available.")

    # By category
    by_cat = report.get("by_category", {})
    if by_cat:
        print(f"\nBY CATEGORY")
        for cat, cat_agg in by_cat.items():
            parts = [
                f"{METRIC_SHORT.get(m, m[:3])}={cat_agg[m]}"
                for m in METRIC_NAMES
                if m in cat_agg
            ]
            print(f"  {cat} (n={cat_agg['n']}):  {' '.join(parts)}")

    # By difficulty
    by_diff = report.get("by_difficulty", {})
    if by_diff:
        print(f"\nBY DIFFICULTY")
        for diff, diff_agg in by_diff.items():
            parts = [
                f"{METRIC_SHORT.get(m, m[:3])}={diff_agg[m]}"
                for m in METRIC_NAMES
                if m in diff_agg
            ]
            print(f"  {diff} (n={diff_agg['n']}):  {' '.join(parts)}")

    # Worst performers (bottom 3 by overall_score)
    scored = [
        r for r in results
        if r.get("overall_score") is not None and not r.get("error")
    ]
    if scored:
        worst = sorted(scored, key=lambda r: r["overall_score"])[:3]
        print(f"\nWORST PERFORMERS (bottom 3)")
        for i, r in enumerate(worst, 1):
            low_metrics = []
            if r.get("scores"):
                for m in METRIC_NAMES:
                    if m in r["scores"] and r["scores"][m]["score"] <= 3:
                        short = METRIC_SHORT.get(m, m[:3])
                        low_metrics.append(f"{short}={r['scores'][m]['score']}")
            detail = f" — {', '.join(low_metrics)}" if low_metrics else ""
            print(f"  {i}. {r['id']} ({r['overall_score']:.1f}){detail}")

    # Out-of-scope results
    oos = [r for r in results if "out-of-scope" in r.get("tags", [])]
    if oos:
        print(f"\nOUT-OF-SCOPE ({len(oos)} cases)")
        for r in oos:
            rag_result = r.get("rag_result") or {}
            grounded = rag_result.get("grounded", "?")
            status = "PASS (ungrounded)" if not grounded else "FAIL (grounded)"
            print(f"  {r['id']}: {status}")

    # Errors
    errors = [r for r in results if r.get("error")]
    if errors:
        print(f"\nERRORS ({len(errors)} cases)")
        for r in errors:
            print(f"  {r['id']}: {r['error'][:80]}")

    print(f"\n{bar}\n")


def save_json_report(report: dict, path: str) -> None:
    """Save full report as JSON file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Report saved to {output_path}")
