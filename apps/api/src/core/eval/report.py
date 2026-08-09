"""Report generation for the binary RAG evaluation — console summary + JSON export.

Metrics are proportions in [0, 1] computed from binary atoms (see `binary_judge.py`),
not 1-5 Likert ratings. Four are scored (relevancy, recall, precision, faithfulness);
answer_relevancy is a pass/fail GATE, reported separately, never in the aggregates.

Aggregation rules that encode the migration's decisions:
  - A metric with `score is None` ERRORED — it is EXCLUDED from its mean and counted
    in `n_errored`, never treated as a 0 or a midpoint.
  - The headline number is recall ("% expected facts retrieved").
  - `overall` (mean of the 4 scored proportions) is secondary, for regression diffs.
"""

import json
import logging
import statistics
from pathlib import Path

logger = logging.getLogger(__name__)

# NOTE: these mirror `binary_judge.SCORED_METRICS` / `GATE_METRIC` / `HEADLINE_METRIC`
# (the canonical source). They are duplicated here deliberately: `ragas_runner.py`
# loads this file STANDALONE via importlib to reuse compute_aggregates without
# dragging the eval package __init__ (and the RAG->supabase chain) into venv-ragas,
# which requires report.py to have NO intra-package imports. The 5 metric keys are
# fixed for the whole project; keep them in sync if binary_judge ever changes them.
GATE_METRIC = "answer_relevancy"
HEADLINE_METRIC = "contextual_recall"
# Scored metrics only — the gate is handled separately.
METRIC_NAMES = [
    "contextual_relevancy",
    "contextual_recall",
    "contextual_precision",
    "faithfulness",
]
SCORED_METRICS = tuple(METRIC_NAMES)

METRIC_SHORT = {
    "contextual_relevancy": "Rel",
    "contextual_recall": "Rec",
    "contextual_precision": "Pre",
    "faithfulness": "Fai",
    "answer_relevancy": "Ans",
}

# Order metrics appear in the aggregate table. answer_relevancy is included so a
# Ragas cross-validation report (where it is a SCORED metric, {"score": 0.x}) shows
# it; on the binary report it carries no "score" (it is a gate) and is skipped
# automatically. report.py is loaded STANDALONE by ragas_runner.py (see header
# note), so aggregation must handle BOTH schemas.
_TABLE_ORDER = [*METRIC_NAMES, GATE_METRIC]

# A scored metric below this reads as a real weakness in the console summary.
LOW_METRIC = 0.5

# Sentinel: the metric dict has NO "score" key at all (a gate, or absent) — which
# is different from an errored scored-metric whose "score" is explicitly None.
_MISSING = object()


def _raw_score(result: dict, metric: str):
    """The metric's score value, or _MISSING when it carries no 'score' key."""
    md = (result.get("scores") or {}).get(metric)
    if not isinstance(md, dict) or "score" not in md:
        return _MISSING
    return md["score"]  # float, or None when the metric errored


def _metric_score(result: dict, metric: str):
    """The numeric score for `metric`, or None if absent/errored (for display)."""
    v = _raw_score(result, metric)
    return None if v is _MISSING else v


def _metric_present(results: list[dict], metric: str) -> bool:
    """True if any result carries a 'score' key for `metric` (a scored metric,
    not a gate). Distinguishes Ragas's scored answer_relevancy from the binary
    report's gate-shaped one."""
    return any(_raw_score(r, metric) is not _MISSING for r in results)


def _has_gate(results: list[dict]) -> bool:
    """True if answer_relevancy is gate-shaped (binary report) rather than a
    scored metric (Ragas report)."""
    for r in results:
        md = (r.get("scores") or {}).get(GATE_METRIC)
        if isinstance(md, dict) and "passed" in md:
            return True
    return False


def _scored_results(report: dict) -> list[dict]:
    """Cases that were judged (have a scores dict) and didn't error at the case
    level. OOS/0-fact cases (scores=None) are excluded."""
    return [
        r for r in report["results"] if r.get("scores") and not r.get("error")
    ]


def _metric_values(results: list[dict], metric: str) -> list[float]:
    """Non-errored numeric scores for `metric` across the given results."""
    out = []
    for r in results:
        v = _raw_score(r, metric)
        if v is not _MISSING and v is not None:
            out.append(v)
    return out


def compute_aggregates(report: dict) -> dict:
    """Compute aggregate statistics from binary-eval results.

    Adds 'aggregate', 'by_category', and 'by_difficulty'. The 'aggregate' block
    carries per-metric proportions, a recall 'headline', a blended 'overall', the
    answer-relevancy 'gate' pass-rate, and any 'errored_metrics'.
    """
    scored = _scored_results(report)

    if not scored:
        report["aggregate"] = {"note": "No scored results"}
        report["by_category"] = {}
        report["by_difficulty"] = {}
        return report

    aggregate: dict = {}

    # Per-metric proportions (errored metrics excluded, counted separately).
    # Iterate _TABLE_ORDER: answer_relevancy is included so a Ragas report shows
    # it; on the binary report it has no "score" (gate) so _metric_present is
    # False and it is skipped here, handled by the gate block below instead.
    for metric in _TABLE_ORDER:
        if not _metric_present(scored, metric):
            continue
        values = _metric_values(scored, metric)
        n_errored = sum(1 for r in scored if _raw_score(r, metric) is None)
        if values:
            aggregate[metric] = {
                "mean": round(statistics.mean(values), 3),
                "std": round(statistics.stdev(values), 3) if len(values) > 1 else 0.0,
                "min": round(min(values), 3),
                "max": round(max(values), 3),
                "n": len(values),
                "n_errored": n_errored,
            }
        elif n_errored:
            aggregate[metric] = {"n": 0, "n_errored": n_errored}

    # Headline = recall ("% expected facts retrieved").
    if HEADLINE_METRIC in aggregate and "mean" in aggregate[HEADLINE_METRIC]:
        aggregate["headline"] = {"recall": aggregate[HEADLINE_METRIC]["mean"]}

    # Blended overall (secondary) — mean of the per-case overall_scores.
    overall_values = [
        r["overall_score"] for r in scored if r.get("overall_score") is not None
    ]
    if overall_values:
        aggregate["overall"] = {
            "mean": round(statistics.mean(overall_values), 3),
            "std": round(statistics.stdev(overall_values), 3)
            if len(overall_values) > 1
            else 0.0,
            "min": round(min(overall_values), 3),
            "max": round(max(overall_values), 3),
            "n": len(overall_values),
        }

    # Answer-relevancy gate (pass/fail tripwire) — only on the binary report,
    # where answer_relevancy is gate-shaped. On a Ragas report it is a scored
    # metric (handled in the loop above), so there is no gate to summarize.
    if _has_gate(scored):
        aggregate["answer_relevancy_gate"] = _gate_aggregate(scored)

    # Errored metrics — surfaced, not silently dropped.
    errored = []
    for r in scored:
        for metric in (*SCORED_METRICS, GATE_METRIC):
            md = (r.get("scores") or {}).get(metric, {})
            if md.get("error"):
                errored.append({"id": r["id"], "metric": metric, "error": md["error"]})
    if errored:
        aggregate["errored_metrics"] = errored

    report["aggregate"] = aggregate
    report["by_category"] = _group_means(scored, "category", "uncategorized")
    report["by_difficulty"] = _group_means(scored, "difficulty", "unknown")
    return report


def _gate_aggregate(scored: list[dict]) -> dict:
    """Pass-rate over the answer-relevancy gate. Errored gate verdicts (passed=None)
    are excluded from the rate and counted separately."""
    passed = failures = errored = 0
    failure_ids: list[str] = []
    for r in scored:
        gate = (r.get("scores") or {}).get(GATE_METRIC, {})
        verdict = gate.get("passed")
        if verdict is True:
            passed += 1
        elif verdict is False:
            failures += 1
            failure_ids.append(r["id"])
        else:  # None -> errored / no verdict
            errored += 1
    total = passed + failures
    return {
        "pass_rate": round(passed / total, 3) if total else None,
        "n": total,
        "passed": passed,
        "failures": failure_ids,
        "n_errored": errored,
    }


def _group_means(scored: list[dict], key: str, default: str) -> dict:
    """Per-group per-metric means (2 dp) over the scored metrics."""
    groups: dict[str, list] = {}
    for r in scored:
        groups.setdefault(r.get(key) or default, []).append(r)

    out = {}
    for group, group_results in sorted(groups.items()):
        agg = {}
        for metric in _TABLE_ORDER:
            values = _metric_values(group_results, metric)
            if values:
                agg[metric] = round(statistics.mean(values), 2)
        agg["n"] = len(group_results)
        out[group] = agg
    return out


def print_summary(report: dict) -> None:
    """Print formatted console summary of the binary evaluation."""
    meta = report["metadata"]
    agg = report.get("aggregate", {})
    results = report["results"]

    duration_m = meta["duration_s"] / 60
    bar = "=" * 64

    print(f"\n{bar}")
    print(f"Binary RAG Evaluation Report — {meta['timestamp'][:10]}")
    print(
        f"Model: {meta['model']} | Judge: {meta['judge_model']} | "
        f"Cases: {meta['total_cases']} run, {meta['failed_cases']} failed"
    )
    print(f"Mode: {meta['judge_mode']} | Duration: {duration_m:.1f}m")
    if meta.get("metrics_filter"):
        print(f"Metrics filter: {meta['metrics_filter']}")
    print(bar)

    # Headline
    headline = agg.get("headline", {})
    if "recall" in headline:
        print(f"\nHEADLINE — Recall (% expected facts retrieved): {headline['recall']:.3f}")

    # Aggregate proportions
    if agg and any(m in agg for m in _TABLE_ORDER):
        print("\nAGGREGATE SCORES (proportion 0-1, mean +/- std)")
        for metric in _TABLE_ORDER:
            if metric in agg and "mean" in agg[metric]:
                m = agg[metric]
                label = metric.replace("_", " ").title()
                errnote = f"  ({m['n_errored']} errored)" if m.get("n_errored") else ""
                print(f"  {label:25s} {m['mean']:.3f} +/- {m['std']:.3f}  (n={m['n']}){errnote}")
        if "overall" in agg:
            print(f"  {'Overall (blended)':25s} {agg['overall']['mean']:.3f}")
    else:
        print("\nNo aggregate scores available.")

    # Answer-relevancy gate
    gate = agg.get("answer_relevancy_gate")
    if gate and gate.get("pass_rate") is not None:
        line = f"\nANSWER-RELEVANCY GATE: {gate['passed']}/{gate['n']} pass ({gate['pass_rate']:.3f})"
        if gate["failures"]:
            line += f" | fail: {', '.join(gate['failures'])}"
        if gate.get("n_errored"):
            line += f" | {gate['n_errored']} errored"
        print(line)

    # By category
    by_cat = report.get("by_category", {})
    if by_cat:
        print("\nBY CATEGORY")
        for cat, cat_agg in by_cat.items():
            parts = [
                f"{METRIC_SHORT.get(m, m[:3])}={cat_agg[m]}"
                for m in _TABLE_ORDER
                if m in cat_agg
            ]
            print(f"  {cat} (n={cat_agg['n']}):  {' '.join(parts)}")

    # By difficulty
    by_diff = report.get("by_difficulty", {})
    if by_diff:
        print("\nBY DIFFICULTY")
        for diff, diff_agg in by_diff.items():
            parts = [
                f"{METRIC_SHORT.get(m, m[:3])}={diff_agg[m]}"
                for m in _TABLE_ORDER
                if m in diff_agg
            ]
            print(f"  {diff} (n={diff_agg['n']}):  {' '.join(parts)}")

    # Worst performers (bottom 3 by blended overall)
    ranked = [
        r for r in results
        if r.get("overall_score") is not None and not r.get("error")
    ]
    if ranked:
        worst = sorted(ranked, key=lambda r: r["overall_score"])[:3]
        print("\nWORST PERFORMERS (bottom 3 by blended overall)")
        for i, r in enumerate(worst, 1):
            low = [
                f"{METRIC_SHORT.get(m, m[:3])}={s:.2f}"
                for m in METRIC_NAMES
                if (s := _metric_score(r, m)) is not None and s < LOW_METRIC
            ]
            detail = f" — {', '.join(low)}" if low else ""
            print(f"  {i}. {r['id']} ({r['overall_score']:.2f}){detail}")

    # Errored metrics
    errored = agg.get("errored_metrics")
    if errored:
        print(f"\nERRORED METRICS ({len(errored)}, excluded from aggregates)")
        for e in errored:
            print(f"  {e['id']}/{e['metric']}: {e['error'][:70]}")

    # Out-of-scope results
    oos = [r for r in results if "out-of-scope" in r.get("tags", [])]
    if oos:
        print(f"\nOUT-OF-SCOPE ({len(oos)} cases)")
        for r in oos:
            rag_result = r.get("rag_result") or {}
            grounded = rag_result.get("grounded", "?")
            status = "PASS (ungrounded)" if not grounded else "FAIL (grounded)"
            print(f"  {r['id']}: {status}")

    # Case-level errors
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
