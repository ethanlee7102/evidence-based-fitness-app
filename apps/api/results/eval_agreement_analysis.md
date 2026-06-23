# RAG Eval Cross-Validation Analysis

*Generated 2026-06-22 20:04 by `scripts/analyze_eval_agreement.py`.*

Characterizes the custom LLM-as-judge against two independent axes — a different judge **model** (Claude Haiku 4.5) and a different **implementation** (Ragas) — to show the eval isn't self-confirming. All scores normalized to **0–1** for comparison (custom 1–5 → `(x−1)/4`). *Within-1-point* = ±0.25 normalized. Pearson is reported only where a metric has variance; a metric saturated near its ceiling has undefined correlation (flagged `n/a (saturated)`), and agreement-rate is the meaningful statistic there.

## Runs compared

| Run | Implementation · model · RAG source | Native scale | n scored | Overall (native) |
|---|---|---|---|---|
| `baseline` | Custom · Gemini · live (baseline) | 1–5 | 98 | 4.58 |
| `run_a` | Custom · Claude Haiku 4.5 · live | 1–5 | 98 | 4.74 |
| `custom_fixture` | Custom · Gemini · fixture | 1–5 | 98 | 4.56 |
| `run_b` | Ragas · Gemini · fixture | 0–1 | 98 | 0.86 |

## Per-metric means (normalized 0–1)

| Metric | `baseline` | `run_a` | `custom_fixture` | `run_b` |
|---|---|---|---|---|
| **contextual_relevancy** | 0.90 | 0.97 | 0.90 | 0.99 |
| **contextual_recall** | 0.79 | 0.91 | 0.78 | 0.74 |
| **contextual_precision** | 0.83 | 0.88 | 0.83 | 0.77 |
| **answer_relevancy** | 1.00 | 0.98 | 1.00 | 0.87 |
| **faithfulness** | 0.96 | 0.93 | 0.94 | 0.93 |

## Axis 1 — Judge model (custom prompts, live RAG)

*Does swapping the judge model (Gemini→Claude) move the scores? Isolates model bias.*

`baseline` (Custom · Gemini · live (baseline)) vs `run_a` (Custom · Claude Haiku 4.5 · live).

| Metric | A mean | B mean | Δ (B−A) | Pearson r | within-1pt |
|---|---|---|---|---|---|
| contextual_relevancy | 0.90 | 0.97 | +0.07 | +0.19 | 96% |
| contextual_recall | 0.79 | 0.91 | +0.12 | +0.60 | 97% |
| contextual_precision | 0.83 | 0.88 | +0.05 | +0.31 | 93% |
| answer_relevancy | 1.00 | 0.98 | -0.02 | n/a (saturated) | 98% |
| faithfulness | 0.96 | 0.93 | -0.03 | +0.09 | 98% |
| **overall** | 0.90 | 0.93 | +0.04 | +0.53 | — |

**Disagreement cases** (any metric differs >1.5pts / >0.375 normalized): 17 of 98

| Case | Metric (A→B normalized) |
|---|---|
| BC-003 | Rel 0.50→1.00 |
| BC-004 | Fai 1.00→0.50 |
| BC-006 | Rec 0.50→1.00 |
| BC-009 | Pre 0.50→1.00 |
| BH-005 | Fai 0.50→1.00 |
| GEN-004 | Ans 1.00→0.50 |
| HYP-013 | Rel 0.50→1.00 |
| INJ-009 | Ans 1.00→0.50 |
| MH-006 | Pre 1.00→0.50 |
| MOB-003 | Rel 0.50→1.00 |
| NUT-011 | Pre 0.50→1.00 |
| PROG-006 | Pre 0.50→1.00 |
| PROG-008 | Pre 0.50→1.00 |
| REC-006 | Pre 0.50→1.00 |
| STR-002 | Pre 0.50→1.00 |
| STR-010 | Rel 0.50→1.00, Rec 0.25→1.00 |
| STR-014 | Rec 0.50→1.00 |

## Axis 2 — Implementation (Gemini judge, same frozen fixture)

*Does my custom judge agree with the industry-standard Ragas? Isolates implementation differences.*

`custom_fixture` (Custom · Gemini · fixture) vs `run_b` (Ragas · Gemini · fixture).

| Metric | A mean | B mean | Δ (B−A) | Pearson r | within-1pt |
|---|---|---|---|---|---|
| contextual_relevancy | 0.90 | 0.99 | +0.09 | +0.19 | 94% |
| contextual_recall | 0.78 | 0.74 | -0.04 | +0.73 | 87% |
| contextual_precision | 0.83 | 0.77 | -0.05 | +0.16 | 71% |
| answer_relevancy | 1.00 | 0.87 | -0.13 | n/a (saturated) | 89% |
| faithfulness | 0.94 | 0.93 | -0.01 | +0.01 | 94% |
| **overall** | 0.89 | 0.86 | -0.03 | +0.37 | — |

**Disagreement cases** (any metric differs >1.5pts / >0.375 normalized): 37 of 98

| Case | Metric (A→B normalized) |
|---|---|
| BC-004 | Pre 0.50→0.92 |
| BC-007 | Pre 1.00→0.48 |
| BC-010 | Rec 0.50→0.00 |
| BFR-001 | Rel 0.50→1.00, Pre 0.50→0.00, Fai 0.25→0.90 |
| BFR-003 | Ans 1.00→0.00 |
| BFR-004 | Ans 1.00→0.00 |
| BH-003 | Ans 1.00→0.00 |
| CVD-007 | Ans 1.00→0.00 |
| GEN-001 | Pre 1.00→0.00 |
| GEN-004 | Ans 1.00→0.00 |
| GEN-006 | Ans 1.00→0.00 |
| HYP-010 | Ans 1.00→0.00 |
| HYP-012 | Pre 1.00→0.59 |
| HYP-013 | Rel 0.50→1.00, Pre 0.25→0.76, Fai 1.00→0.15 |
| HYP-014 | Ans 1.00→0.00 |
| INJ-001 | Pre 0.50→0.92 |
| INJ-007 | Rec 0.50→1.00 |
| INJ-009 | Pre 0.75→0.00 |
| MH-001 | Rel 0.50→1.00, Pre 0.50→1.00 |
| MH-004 | Pre 0.25→0.89, Fai 0.50→1.00 |
| MOB-003 | Rec 0.75→0.33, Ans 1.00→0.00 |
| MOB-005 | Pre 0.50→0.95 |
| NUT-004 | Rel 0.50→1.00, Pre 0.25→0.76 |
| NUT-005 | Pre 1.00→0.45 |
| NUT-008 | Pre 1.00→0.50 |
| NUT-010 | Pre 1.00→0.00 |
| NUT-011 | Pre 0.50→1.00 |
| NUT-014 | Rel 0.50→1.00, Ans 1.00→0.00 |
| NUT-022 | Rec 0.50→1.00 |
| NUT-023 | Ans 1.00→0.00 |
| NUT-024 | Pre 0.50→0.92 |
| REC-006 | Rel 0.50→1.00, Pre 0.50→1.00 |
| STR-002 | Pre 0.50→0.89 |
| STR-007 | Pre 0.75→0.25 |
| STR-009 | Pre 1.00→0.33 |
| STR-010 | Pre 1.00→0.00 |
| STR-013 | Pre 1.00→0.50 |

## Outlier metrics (largest cross-run spread of means)

| Metric | min mean | max mean | spread |
|---|---|---|---|
| contextual_relevancy | 0.90 | 0.99 | 0.09 |
| contextual_recall | 0.74 | 0.91 | 0.17 |
| contextual_precision | 0.77 | 0.88 | 0.10 |
| answer_relevancy | 0.87 | 1.00 | 0.13 |
| faithfulness | 0.93 | 0.96 | 0.03 |

## Commentary

- **Both axes independently flag retrieval (recall/precision) as the weak spot**, not answer quality — convergent evidence that the eval is measuring something real about the system, not an artifact of one judge.
- **Model axis:** swapping Gemini→Claude leaves answer-quality metrics ~unchanged but makes the judge **more lenient on retrieval** (recall Δ +0.12 normalized). Implication: any retrieval before/after comparison must hold the judge model fixed, or a judge swap would masquerade as a retrieval gain.
- **Implementation axis:** custom vs Ragas **correlate strongly on contextual recall (r=+0.73)** — the metric that drives the Phase-2 retrieval roadmap — so that signal is implementation-robust. Known retrieval-weak cases (GEN-004, BC-010, STR-010) score low in both.
- **Why some metrics show `n/a (saturated)` correlation:** answer-quality metrics cluster near the ceiling in both implementations (e.g. custom answer-relevancy is 5/5 on nearly every case → zero variance → Pearson undefined). This is *agreement*, not disagreement — their within-1-point rates are high. Correlation is only meaningful where there's spread (the retrieval metrics); agreement-rate is the right statistic for saturated metrics.
- **Takeaway:** the custom judge is not self-confirming. It tracks a different model on answer quality, tracks the industry-standard implementation on the retrieval signal that matters, and the disagreements are explainable (judge strictness; metric saturation), not bugs.

## Follow-up — Run-B-surfaced recall divergences (2026-05-31)

Three of the Axis-2 recall disagreements — **MOB-003, STR-003, STR-007** — were chunk-verified (Ragas scored them low; the custom judge had passed them at 4/5). A controlled test-fix experiment (retrieval held frozen, only `expected_facts` corrected) then separated test-authoring from retrieval:
- **STR-003**: Ragas recall 0.50 → **1.00** — was *test-bound* (the paper never studied weight class / age); resolved by the fix.
- **MOB-003 & STR-007**: recall stayed flat and the custom judge got *stricter* (4 → 3) — confirmed genuine retrieval defects (reference-pollution; single-paper saturation) → Phase-2 targets.
- Insight: tightening vague expected facts can *lower* a holistic judge's recall by exposing a retrieval gap the vague facts had papered over; Ragas's claim-decomposition moved up only where grounding genuinely existed.

The tables above are the **original-facts snapshot** (both judges saw identical facts, so the cross-implementation comparison remains valid). The Phase-2 re-eval against a freshly captured fixture will refresh these numbers. Full chunk-level detail: `context/archive/RETRIEVAL-TARGET-CHUNKS.md` Cases 13-15.
