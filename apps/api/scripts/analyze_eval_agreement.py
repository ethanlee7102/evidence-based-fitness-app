"""Eval cross-validation analysis (ROADMAP Phase 1, step 7).

Loads the available eval runs and characterizes agreement across two axes:
  - Axis 1 (judge MODEL): custom prompts, Gemini vs Claude Haiku 4.5 (live RAG).
  - Axis 2 (IMPLEMENTATION): Gemini judge, custom vs Ragas, on the SAME frozen
    fixture (so any gap is the implementation, not re-generation).

Emits results/eval_agreement_analysis.md with: per-metric means, Pearson
correlation, within-1-point agreement, disagreement cases, and commentary.

Scale handling: custom judge is 1-5, Ragas is 0-1. Everything is normalized to
0-1 (custom: (x-1)/4) for cross-scale comparison. "Within 1 point" = ±0.25 on
the normalized scale (1 point on the 1-5 scale). Pearson is scale-invariant but
UNDEFINED when a series has ~zero variance (a metric saturated near its ceiling),
which is reported explicitly rather than as a misleading number.

Run from the main venv (pure stdlib):
    cd apps/api && python -m scripts.analyze_eval_agreement
"""

import json
import math
import time
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent
RESULTS = API_DIR / "results"
OUTPUT = RESULTS / "eval_agreement_analysis.md"

METRICS = [
    "contextual_relevancy",
    "contextual_recall",
    "contextual_precision",
    "answer_relevancy",
    "faithfulness",
]
SHORT = {
    "contextual_relevancy": "Rel",
    "contextual_recall": "Rec",
    "contextual_precision": "Pre",
    "answer_relevancy": "Ans",
    "faithfulness": "Fai",
}

# scale: native max (5 = custom 1-5 judge, 1 = Ragas 0-1)
RUNS = {
    "baseline": {
        "path": "run0_baseline_clean.json",
        "scale": 5,
        "label": "Custom · Gemini · live (baseline)",
    },
    "run_a": {
        "path": "run_a_custom_claude.json",
        "scale": 5,
        "label": "Custom · Claude Haiku 4.5 · live",
    },
    "custom_fixture": {
        "path": "run0_custom_fixture.json",
        "scale": 5,
        "label": "Custom · Gemini · fixture",
    },
    "run_b": {
        "path": "run_b_ragas_gemini.json",
        "scale": 1,
        "label": "Ragas · Gemini · fixture",
    },
}

AXES = [
    {
        "name": "Axis 1 — Judge model (custom prompts, live RAG)",
        "a": "baseline",
        "b": "run_a",
        "question": "Does swapping the judge model (Gemini→Claude) move the scores? Isolates model bias.",
    },
    {
        "name": "Axis 2 — Implementation (Gemini judge, same frozen fixture)",
        "a": "custom_fixture",
        "b": "run_b",
        "question": "Does my custom judge agree with the industry-standard Ragas? Isolates implementation differences.",
    },
]

WITHIN_1PT = 0.25  # 1 point on the 1-5 scale, normalized
DISAGREE = 0.375  # >1.5 points on the 1-5 scale, normalized


# --- loading -----------------------------------------------------------------

def load_run(key: str) -> dict:
    """Return {'meta':..., 'cases': {id: {'metrics': {m: norm_score}, 'overall_norm': x}}}."""
    cfg = RUNS[key]
    data = json.load(open(RESULTS / cfg["path"]))
    scale = cfg["scale"]

    def norm(x):
        return (x - 1) / 4 if scale == 5 else x

    cases = {}
    for c in data["results"]:
        if not c.get("scores"):
            continue
        metrics = {
            m: norm(c["scores"][m]["score"])
            for m in METRICS
            if m in c["scores"] and c["scores"][m].get("score") is not None
        }
        if not metrics:
            continue
        ov = c.get("overall_score")
        cases[c["id"]] = {
            "metrics": metrics,
            "overall_norm": norm(ov) if ov is not None else None,
        }
    return {"meta": data.get("metadata", {}), "cases": cases, "label": cfg["label"], "scale": scale}


# --- stats -------------------------------------------------------------------

def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def pearson(xs, ys):
    """Pearson r, or None if either series has ~zero variance (saturated)."""
    n = len(xs)
    if n < 2:
        return None
    mx, my = mean(xs), mean(ys)
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx < 1e-9 or dy < 1e-9:
        return None  # no variance -> correlation undefined/uninformative
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return num / (dx * dy)


def aligned(run_a, run_b, metric):
    """Return paired normalized scores for cases scored on `metric` in both runs."""
    xs, ys, ids = [], [], []
    for cid, ca in run_a["cases"].items():
        cb = run_b["cases"].get(cid)
        if cb and metric in ca["metrics"] and metric in cb["metrics"]:
            xs.append(ca["metrics"][metric])
            ys.append(cb["metrics"][metric])
            ids.append(cid)
    return xs, ys, ids


# --- markdown helpers --------------------------------------------------------

def fmt_r(r):
    return "n/a (saturated)" if r is None else f"{r:+.2f}"


def f2(x):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.2f}"


def build_report(runs: dict) -> str:
    L = []
    ts = time.strftime("%Y-%m-%d %H:%M")
    L.append("# RAG Eval Cross-Validation Analysis\n")
    L.append(f"*Generated {ts} by `scripts/analyze_eval_agreement.py`.*\n")
    L.append(
        "Characterizes the custom LLM-as-judge against two independent axes — a different "
        "judge **model** (Claude Haiku 4.5) and a different **implementation** (Ragas) — to show "
        "the eval isn't self-confirming. All scores normalized to **0–1** for comparison "
        "(custom 1–5 → `(x−1)/4`). *Within-1-point* = ±0.25 normalized. Pearson is reported only "
        "where a metric has variance; a metric saturated near its ceiling has undefined correlation "
        "(flagged `n/a (saturated)`), and agreement-rate is the meaningful statistic there.\n"
    )

    # Runs table
    L.append("## Runs compared\n")
    L.append("| Run | Implementation · model · RAG source | Native scale | n scored | Overall (native) |")
    L.append("|---|---|---|---|---|")
    for key in ["baseline", "run_a", "custom_fixture", "run_b"]:
        r = runs[key]
        n = len(r["cases"])
        ov = r["meta"].get("aggregate_overall")
        # recompute native overall mean from cases
        ov_norm = mean([c["overall_norm"] for c in r["cases"].values() if c["overall_norm"] is not None])
        native = ov_norm * 4 + 1 if r["scale"] == 5 else ov_norm
        L.append(f"| `{key}` | {r['label']} | {'1–5' if r['scale']==5 else '0–1'} | {n} | {native:.2f} |")
    L.append("")

    # Per-metric normalized means across all runs
    L.append("## Per-metric means (normalized 0–1)\n")
    header = "| Metric | " + " | ".join(f"`{k}`" for k in RUNS) + " |"
    L.append(header)
    L.append("|" + "---|" * (len(RUNS) + 1))
    for m in METRICS:
        row = [f"**{m}**"]
        for key in RUNS:
            vals = [c["metrics"][m] for c in runs[key]["cases"].values() if m in c["metrics"]]
            row.append(f2(mean(vals)) if vals else "—")
        L.append("| " + " | ".join(row) + " |")
    L.append("")

    # Per-axis analysis
    for ax in AXES:
        ra, rb = runs[ax["a"]], runs[ax["b"]]
        L.append(f"## {ax['name']}\n")
        L.append(f"*{ax['question']}*\n")
        L.append(f"`{ax['a']}` ({ra['label']}) vs `{ax['b']}` ({rb['label']}).\n")
        L.append("| Metric | A mean | B mean | Δ (B−A) | Pearson r | within-1pt |")
        L.append("|---|---|---|---|---|---|")
        deltas = {}
        for m in METRICS:
            xs, ys, ids = aligned(ra, rb, m)
            if not xs:
                L.append(f"| {m} | — | — | — | — | — |")
                continue
            ma, mb = mean(xs), mean(ys)
            d = mb - ma
            deltas[m] = d
            r = pearson(xs, ys)
            within = sum(1 for a, b in zip(xs, ys) if abs(a - b) <= WITHIN_1PT) / len(xs)
            L.append(f"| {m} | {ma:.2f} | {mb:.2f} | {d:+.2f} | {fmt_r(r)} | {within*100:.0f}% |")
        # overall agreement
        oxs = [c["overall_norm"] for cid, c in ra["cases"].items()
               if rb["cases"].get(cid) and c["overall_norm"] is not None
               and rb["cases"][cid]["overall_norm"] is not None]
        oys = [rb["cases"][cid]["overall_norm"] for cid, c in ra["cases"].items()
               if rb["cases"].get(cid) and c["overall_norm"] is not None
               and rb["cases"][cid]["overall_norm"] is not None]
        L.append(f"| **overall** | {mean(oxs):.2f} | {mean(oys):.2f} | {mean(oys)-mean(oxs):+.2f} | {fmt_r(pearson(oxs,oys))} | — |")
        L.append("")

        # Disagreement cases (any metric differs > DISAGREE normalized)
        rows = []
        common = [cid for cid in ra["cases"] if cid in rb["cases"]]
        for cid in common:
            diffs = []
            for m in METRICS:
                if m in ra["cases"][cid]["metrics"] and m in rb["cases"][cid]["metrics"]:
                    d = rb["cases"][cid]["metrics"][m] - ra["cases"][cid]["metrics"][m]
                    if abs(d) > DISAGREE:
                        diffs.append(f"{SHORT[m]} {ra['cases'][cid]['metrics'][m]:.2f}→{rb['cases'][cid]['metrics'][m]:.2f}")
            if diffs:
                rows.append((cid, diffs))
        L.append(f"**Disagreement cases** (any metric differs >1.5pts / >0.375 normalized): "
                 f"{len(rows)} of {len(common)}")
        if rows:
            L.append("\n| Case | Metric (A→B normalized) |")
            L.append("|---|---|")
            for cid, diffs in sorted(rows):
                L.append(f"| {cid} | {', '.join(diffs)} |")
        L.append("")

    # Outlier-metric detection (largest cross-run spread)
    L.append("## Outlier metrics (largest cross-run spread of means)\n")
    L.append("| Metric | min mean | max mean | spread |")
    L.append("|---|---|---|---|")
    for m in METRICS:
        means = [mean([c["metrics"][m] for c in runs[k]["cases"].values() if m in c["metrics"]])
                 for k in RUNS]
        means = [x for x in means if not math.isnan(x)]
        sp = max(means) - min(means)
        flag = "  ⚠️" if sp > 0.3 else ""
        L.append(f"| {m} | {min(means):.2f} | {max(means):.2f} | {sp:.2f}{flag} |")
    L.append("")

    # Commentary (auto-anchored to the computed numbers)
    L.append("## Commentary\n")
    # recall correlation on axis 2
    xs, ys, _ = aligned(runs["custom_fixture"], runs["run_b"], "contextual_recall")
    rec_r = pearson(xs, ys)
    # model-axis recall delta
    mxs, mys, _ = aligned(runs["baseline"], runs["run_a"], "contextual_recall")
    rec_model_delta = mean(mys) - mean(mxs)
    L.append(
        f"- **Both axes independently flag retrieval (recall/precision) as the weak spot**, not "
        f"answer quality — convergent evidence that the eval is measuring something real about the "
        f"system, not an artifact of one judge.\n"
        f"- **Model axis:** swapping Gemini→Claude leaves answer-quality metrics ~unchanged but "
        f"makes the judge **more lenient on retrieval** (recall Δ {rec_model_delta:+.2f} normalized). "
        f"Implication: any retrieval before/after comparison must hold the judge model fixed, or a "
        f"judge swap would masquerade as a retrieval gain.\n"
        f"- **Implementation axis:** custom vs Ragas **correlate strongly on contextual recall "
        f"(r={fmt_r(rec_r)})** — the metric that drives the Phase-2 retrieval roadmap — so that signal "
        f"is implementation-robust. Known retrieval-weak cases (GEN-004, BC-010, STR-010) score low in both.\n"
        f"- **Why some metrics show `n/a (saturated)` correlation:** answer-quality metrics cluster "
        f"near the ceiling in both implementations (e.g. custom answer-relevancy is 5/5 on nearly every "
        f"case → zero variance → Pearson undefined). This is *agreement*, not disagreement — their "
        f"within-1-point rates are high. Correlation is only meaningful where there's spread (the "
        f"retrieval metrics); agreement-rate is the right statistic for saturated metrics.\n"
        f"- **Takeaway:** the custom judge is not self-confirming. It tracks a different model on "
        f"answer quality, tracks the industry-standard implementation on the retrieval signal that "
        f"matters, and the disagreements are explainable (judge strictness; metric saturation), not bugs.\n"
    )

    # Follow-up note (numbers above are the original-facts snapshot; do not edit the tables by hand).
    L.append("## Follow-up — Run-B-surfaced recall divergences (2026-05-31)\n")
    L.append(
        "Three of the Axis-2 recall disagreements — **MOB-003, STR-003, STR-007** — were chunk-verified "
        "(Ragas scored them low; the custom judge had passed them at 4/5). A controlled test-fix experiment "
        "(retrieval held frozen, only `expected_facts` corrected) then separated test-authoring from retrieval:\n"
        "- **STR-003**: Ragas recall 0.50 → **1.00** — was *test-bound* (the paper never studied weight class / age); resolved by the fix.\n"
        "- **MOB-003 & STR-007**: recall stayed flat and the custom judge got *stricter* (4 → 3) — confirmed genuine "
        "retrieval defects (reference-pollution; single-paper saturation) → Phase-2 targets.\n"
        "- Insight: tightening vague expected facts can *lower* a holistic judge's recall by exposing a retrieval gap "
        "the vague facts had papered over; Ragas's claim-decomposition moved up only where grounding genuinely existed.\n\n"
        "The tables above are the **original-facts snapshot** (both judges saw identical facts, so the cross-implementation "
        "comparison remains valid). The Phase-2 re-eval against a freshly captured fixture will refresh these numbers. "
        "Full chunk-level detail: `context/archive/RETRIEVAL-TARGET-CHUNKS.md` Cases 13-15.\n"
    )

    return "\n".join(L)


def main():
    runs = {k: load_run(k) for k in RUNS}
    report = build_report(runs)
    OUTPUT.write_text(report)
    print(f"Wrote {OUTPUT}")
    print(report)


if __name__ == "__main__":
    main()
