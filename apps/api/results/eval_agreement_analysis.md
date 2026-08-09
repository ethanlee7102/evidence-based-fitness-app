# RAG Eval Cross-Validation Analysis

*Generated 2026-08-08 15:38 by `scripts/analyze_eval_agreement.py`.*

Characterizes the custom LLM-as-judge against two independent axes — a different judge **model** (Claude Haiku 4.5) and a different **implementation** (Ragas) — to show the eval isn't self-confirming. All scores normalized to **0–1** for comparison (custom 1–5 → `(x−1)/4`). *Within-1-point* = ±0.25 normalized. Pearson is reported only where a metric has variance; a metric saturated near its ceiling has undefined correlation (flagged `n/a (saturated)`), and agreement-rate is the meaningful statistic there.

## Runs compared

| Run | Implementation · model · RAG source | Native scale | n scored | Overall (native) |
|---|---|---|---|---|
| `baseline` | Custom 1-5 · Gemini · live (old baseline) | 1–5 | 98 | 4.58 |
| `run_a` | Custom 1-5 · Claude Haiku 4.5 · live | 1–5 | 98 | 4.74 |
| `holistic_canonical` | Custom 1-5 holistic · Gemini · fixture (old facts) | 1–5 | 98 | 4.58 |
| `binary_v1` | Custom binary · Gemini · fixture v1 (old facts) | 0–1 | 98 | 0.89 |
| `binary_v2` | Custom binary · Gemini · fixture v2 (CURRENT baseline) | 0–1 | 98 | 0.90 |
| `claude_v2` | Custom binary · Claude Haiku 4.5 · fixture v2 | 0–1 | 98 | 0.94 |
| `ragas_v2` | Ragas · Gemini · fixture v2 | 0–1 | 98 | 0.87 |

## Per-metric means (normalized 0–1)

| Metric | `baseline` | `run_a` | `holistic_canonical` | `binary_v1` | `binary_v2` | `claude_v2` | `ragas_v2` |
|---|---|---|---|---|---|---|---|
| **contextual_relevancy** | 0.90 | 0.97 | 0.92 | 0.88 | 0.88 | 0.93 | 0.99 |
| **contextual_recall** | 0.79 | 0.91 | 0.80 | 0.75 | 0.79 | 0.87 | 0.79 |
| **contextual_precision** | 0.83 | 0.88 | 0.78 | 0.95 | 0.96 | 0.98 | 0.80 |
| **answer_relevancy** | 1.00 | 0.98 | 0.99 | — | — | — | 0.83 |
| **faithfulness** | 0.96 | 0.93 | 0.98 | 0.98 | 0.98 | 1.00 | 0.91 |

## Axis 1 — Judge model (1-5 custom prompts, live RAG)

*Does swapping the judge model (Gemini→Claude) move the scores? Isolates model bias.*

`baseline` (Custom 1-5 · Gemini · live (old baseline)) vs `run_a` (Custom 1-5 · Claude Haiku 4.5 · live).

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

## Axis 2 — Implementation (binary custom vs Ragas, v2 matched facts)

*Does the binary custom judge agree with industry-standard Ragas? Both native 0-1 on identical retrieval AND matched (refined) facts — the cleanest apples-to-apples the project has. Recall agreement rose from r=0.70 (v1) to r=0.75 (v2) after the fact refinement.*

`binary_v2` (Custom binary · Gemini · fixture v2 (CURRENT baseline)) vs `ragas_v2` (Ragas · Gemini · fixture v2).

| Metric | A mean | B mean | Δ (B−A) | Pearson r | within-1pt |
|---|---|---|---|---|---|
| contextual_relevancy | 0.88 | 0.99 | +0.11 | -0.06 | 91% |
| contextual_recall | 0.79 | 0.79 | -0.01 | +0.75 | 83% |
| contextual_precision | 0.96 | 0.80 | -0.16 | +0.30 | 73% |
| answer_relevancy | — | — | — | — | — |
| faithfulness | 0.98 | 0.91 | -0.07 | +0.24 | 94% |
| **overall** | 0.90 | 0.87 | -0.04 | +0.49 | — |

**Disagreement cases** (any metric differs >1.5pts / >0.375 normalized): 23 of 98

| Case | Metric (A→B normalized) |
|---|---|
| BC-010 | Pre 1.00→0.00 |
| BFR-001 | Rel 0.40→1.00 |
| CVD-001 | Rel 0.40→1.00 |
| CVD-007 | Pre 0.95→0.37 |
| GEN-001 | Pre 1.00→0.20 |
| HYP-004 | Pre 1.00→0.50 |
| HYP-008 | Pre 1.00→0.42 |
| INJ-009 | Pre 1.00→0.37 |
| MH-005 | Rel 0.60→1.00, Pre 1.00→0.59 |
| MH-006 | Pre 1.00→0.59 |
| MOB-001 | Pre 1.00→0.53 |
| MOB-003 | Rel 0.40→1.00 |
| MOB-005 | Rel 0.60→1.00 |
| NUT-008 | Pre 1.00→0.00 |
| NUT-023 | Rel 0.60→1.00 |
| PROG-003 | Pre 1.00→0.33 |
| PROG-008 | Rel 0.60→1.00 |
| PROG-012 | Pre 1.00→0.33 |
| REC-001 | Pre 1.00→0.50 |
| STR-001 | Pre 1.00→0.53 |
| STR-007 | Rel 0.60→1.00, Pre 0.70→0.20 |
| STR-009 | Pre 1.00→0.58 |
| STR-010 | Rel 0.40→1.00, Pre 0.42→0.00 |

## Axis 3 — Metric maturity (old 1-5 holistic vs binary v1, old facts, FROZEN)

*How did migrating the SAME judge from emitted 1-5 Likert to computed binary atoms move each metric? Both on the OLD fact set + byte-identical retrieval, so every delta is pure judge methodology (kept on v1 facts precisely to hold that isolation).*

`holistic_canonical` (Custom 1-5 holistic · Gemini · fixture (old facts)) vs `binary_v1` (Custom binary · Gemini · fixture v1 (old facts)).

| Metric | A mean | B mean | Δ (B−A) | Pearson r | within-1pt |
|---|---|---|---|---|---|
| contextual_relevancy | 0.92 | 0.88 | -0.04 | +0.61 | 95% |
| contextual_recall | 0.80 | 0.75 | -0.05 | +0.67 | 89% |
| contextual_precision | 0.78 | 0.95 | +0.18 | +0.41 | 77% |
| answer_relevancy | — | — | — | — | — |
| faithfulness | 0.98 | 0.98 | -0.00 | +0.37 | 99% |
| **overall** | 0.89 | 0.89 | -0.00 | +0.62 | — |

**Disagreement cases** (any metric differs >1.5pts / >0.375 normalized): 25 of 98

| Case | Metric (A→B normalized) |
|---|---|
| BC-009 | Pre 0.50→1.00 |
| BC-010 | Rec 0.50→0.00, Pre 0.50→1.00 |
| BFR-001 | Pre 0.50→1.00 |
| BFR-003 | Pre 0.50→1.00 |
| BFR-004 | Rec 0.75→0.33, Pre 0.50→1.00 |
| BFR-006 | Pre 0.50→0.95 |
| BH-005 | Pre 0.50→1.00 |
| BH-007 | Pre 0.50→0.95 |
| CVD-001 | Pre 0.25→0.75 |
| GEN-004 | Pre 0.50→1.00 |
| GEN-006 | Rec 1.00→0.00 |
| HYP-007 | Pre 0.50→0.89 |
| MH-005 | Pre 0.50→1.00 |
| MOB-003 | Rel 1.00→0.40 |
| NUT-003 | Pre 0.50→1.00 |
| NUT-004 | Pre 0.50→0.89 |
| NUT-025 | Rec 0.50→1.00 |
| NUT-026 | Pre 0.50→0.95 |
| PROG-006 | Pre 0.25→0.80 |
| PROG-008 | Pre 0.50→1.00 |
| REC-006 | Pre 0.50→0.95 |
| REC-008 | Pre 0.50→0.95 |
| STR-002 | Pre 0.50→0.89 |
| STR-007 | Rel 1.00→0.60 |
| STR-010 | Rel 1.00→0.40 |

## Axis 4 — Cross-model self-preference check (binary Gemini vs Claude, v2)

*Is the primary Gemini number a same-family self-preference artifact? Recall judges the retrieved chunks (Voyage, not Gemini), so a Gemini↔Claude gap here is judge strictness, not self-preference.*

`binary_v2` (Custom binary · Gemini · fixture v2 (CURRENT baseline)) vs `claude_v2` (Custom binary · Claude Haiku 4.5 · fixture v2).

| Metric | A mean | B mean | Δ (B−A) | Pearson r | within-1pt |
|---|---|---|---|---|---|
| contextual_relevancy | 0.88 | 0.93 | +0.04 | +0.58 | 96% |
| contextual_recall | 0.79 | 0.87 | +0.08 | +0.56 | 72% |
| contextual_precision | 0.96 | 0.98 | +0.02 | +0.52 | 99% |
| answer_relevancy | — | — | — | — | — |
| faithfulness | 0.98 | 1.00 | +0.02 | -0.06 | 98% |
| **overall** | 0.90 | 0.94 | +0.04 | +0.53 | — |

**Disagreement cases** (any metric differs >1.5pts / >0.375 normalized): 7 of 98

| Case | Metric (A→B normalized) |
|---|---|
| BC-004 | Rec 0.25→0.75 |
| BFR-001 | Rel 0.40→0.80 |
| CVD-001 | Rel 0.40→1.00 |
| HYP-004 | Rec 0.25→0.75 |
| INJ-007 | Rec 0.50→1.00 |
| MOB-003 | Rel 0.40→0.80 |
| STR-010 | Rel 0.40→1.00, Pre 0.42→1.00 |

## Outlier metrics (largest cross-run spread of means)

| Metric | min mean | max mean | spread |
|---|---|---|---|
| contextual_relevancy | 0.88 | 0.99 | 0.11 |
| contextual_recall | 0.75 | 0.91 | 0.16 |
| contextual_precision | 0.78 | 0.98 | 0.20 |
| answer_relevancy | 0.83 | 1.00 | 0.17 |
| faithfulness | 0.91 | 1.00 | 0.09 |

## Commentary

- **Recall is the weak spot on every axis**, not answer quality — convergent evidence the eval measures something real about retrieval, not a single-judge artifact.
- **Implementation axis (binary custom vs Ragas, v2):** the two independent implementations agree on recall at **r=+0.75** on native-0-1 identical retrieval with matched facts — the cleanest apples-to-apples cross-check the project has. Refining the facts (splitting compounds + correcting source-overstated ones) *raised* agreement from r=+0.70 (v1 facts) — removing noise both judges tripped on, not imposing our own view. The custom judge is not self-confirming.
- **Cross-model self-preference check (v2 binary, Gemini vs Claude):** Claude is more lenient on recall (Δ +0.08) but tracks Gemini (r=+0.56). Crucially, recall judges the **retrieved chunks (Voyage, not Gemini)** — so a Gemini↔Claude gap is judge *strictness*, not same-family self-preference, which structurally cannot apply to the retrieval metrics.
- **Model axis (1-5 live):** Gemini→Claude leaves answer-quality metrics ~unchanged but is more lenient on retrieval (recall Δ +0.12 normalized) — so a retrieval A/B must hold the judge model fixed, else a judge swap masquerades as a retrieval gain.
- **Maturity axis (1-5 holistic → binary v1, identical retrieval + facts):** migrating the judge moved **precision +0.18** and **recall -0.05** (normalized) with the chunks byte-identical — so both deltas are *measurement*, not system. The precision rise is AP's ceiling behavior (a relevant chunk at rank 1 in ~97% of cases saturates Average Precision), whereas the old holistic 1-5 was dragged down by Likert reluctance-to-give-5s plus the (x−1)/4 normalization. Recall went the other way — *stricter* — per-fact binary beats a holistic 'most facts found'.
- **Saturation is honest, not a bug:** faithfulness (~0.98) and the answer-relevancy gate (100% pass) sit near the ceiling because the system genuinely doesn't hallucinate and stays on-topic; the binary judge treats answer-relevancy as a gate, so it shows `—` on the 0-1 axes. Recall is the metric that varies and carries the signal.

## Follow-up — Run-B-surfaced recall divergences (2026-05-31)

Three of the Axis-2 recall disagreements — **MOB-003, STR-003, STR-007** — were chunk-verified (Ragas scored them low; the custom judge had passed them at 4/5). A controlled test-fix experiment (retrieval held frozen, only `expected_facts` corrected) then separated test-authoring from retrieval:
- **STR-003**: Ragas recall 0.50 → **1.00** — was *test-bound* (the paper never studied weight class / age); resolved by the fix.
- **MOB-003 & STR-007**: recall stayed flat and the custom judge got *stricter* (4 → 3) — confirmed genuine retrieval defects (reference-pollution; single-paper saturation) → Phase-2 targets.
- Insight: tightening vague expected facts can *lower* a holistic judge's recall by exposing a retrieval gap the vague facts had papered over; Ragas's claim-decomposition moved up only where grounding genuinely existed.

The tables above are the **original-facts snapshot** (both judges saw identical facts, so the cross-implementation comparison remains valid). The Phase-2 re-eval against a freshly captured fixture will refresh these numbers. Full chunk-level detail: `context/archive/RETRIEVAL-TARGET-CHUNKS.md` Cases 13-15.
