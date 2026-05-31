# Retrieval Target Chunks — Success Criteria

Specific chunks (paper + chunk_index) that retrieval improvements must surface into top-k for each of the 6 retrieval-bound recall=2 failure cases. Use this as the binary success metric independent of the LLM judge.

**Post test-cleanup state** (test edits applied 2026-05-10 — see `test_dataset.json.bak.2026-05-10` for the pre-edit version). The expected facts in the test dataset are now grounded in claims the source papers actually make, so retrieval failures on these cases are pure retrieval failures — not test-authoring artifacts.

---

## Test Methodology

After applying any retrieval change (per-paper diversification, top_k bump, reranking, etc.):

```python
from src.core.retrieval import retrieve_chunks
result = await retrieve_chunks(query, top_k=8)
retrieved = [(c.paper_id, c.chunk_index) for c in result.chunks]
# Score = (target chunks surfaced ÷ total target chunks for this query)
```

A retrieval change is successful for a case when the **bolded "primary target chunks"** below appear in top-k. Secondary targets are confirmatory but not load-bearing.

**Automated harness**: `apps/api/scripts/measure_target_chunks.py` runs this measurement for all 6 cases and prints/saves the `(primary in top-5)/total` ratio. Run it before and after each retrieval change:
```bash
python -m scripts.measure_target_chunks --output results/target_chunks_<label>.json
```

---

## Baseline Measurement — 2026-05-30 (pre-Phase-2)

Ran `measure_target_chunks.py --top-k 20` against current retrieval (vector-only, top_k=5 production, no diversification/reranking). Saved: `apps/api/results/target_chunks_baseline.json`. **This is the "before" snapshot to diff against after diversification + reranking land.**

**Headline (core 6): `0/15` primary target chunks in top-5. `3/15` in top-20** (all three at the extreme edge — Wang ch1 @rank 6, Refalo ch33 @20, Patterson ch2 @20).

**Expanded 2026-05-30 (core 6 + 5 new retrieval-fixable cases from the full recall≤3 sweep — Cases 7-11 below; PROG-006 facts 1-2 included): `0/35` in top-5, `9/35` in top-20.** Every primary target chunk across all 11 retrieval-fixable cases is currently absent from top-5. `scripts/measure_target_chunks.py` reports both the core-6 and extended subtotals each run. Saved: `results/target_chunks_baseline.json`.

| Case | Primary in top-5 | Primary in top-20 | Live top-5 composition | Diagnostic prediction held? |
|---|:---:|:---:|---|:---:|
| NUT-016 | 0/2 | 0/2 | 5× Kazeminasab 2025 | ✅ saturation confirmed |
| BC-010 | 0/2 | 0/2 | 2× McCarthy & Berg + 3× Willoughby | ✅ |
| GEN-004 | 0/4 | 1/4 | 5× Nuckols 2026 | ✅ (Refalo ch33 @20 only) |
| CVD-001 | 0/2 | 0/2 | 5× Edwards 2024 | ✅ saturation confirmed |
| BFR-004 | 0/3 | 1/3 | 5× Nascimento 2022 | ✅ (Patterson ch2 @20 only) |
| STR-010 | 0/2 | 1/2 | 3× Wang 2023 + 2× Thapa 2024 | ✅ Wang ch1 @6, Thapa ch4 absent |

**Chunk indices are stable** since the 2026-03-19 diagnostic — the STR-010 prediction ("Wang ch1 in top-20 not top-5; Thapa ch4 not in top-20") reproduced exactly. No reingestion drift; the target indices below are still valid.

### ⚠️ NUT-016 has decoupled — measure it by chunks, NOT recall
In the fresh clean baseline (`run0_baseline_clean.json`), **NUT-016 scores Contextual Recall = 4** — yet its retrieval is *still fully saturated on Kazeminasab* (0/2 targets, not even in top-20). The recall recovered purely because the **2026-05-10 test edit removed the contradicted VO2max fact**, and the remaining (corrected) facts are satisfiable from the saturating paper alone. **Implication for Phase 2: NUT-016 will show no recall-score movement (already 4, no headroom) even if diversification correctly surfaces Conde + Aragon. Judge it on the chunk metric (0/2 → 2/2), not the recall number.** This is the canonical case for why this judge-independent doc exists.

### Fresh baseline recall (2026-05-30) for cross-reference
NUT-016 = 4 (masked, see above) · BC-010 = 2 · GEN-004 = 1 (worst) · CVD-001 = 3 · BFR-004 = 3 · STR-010 = 2. Note CVD-001 and BFR-004 sit at recall=3 (not 2) post-cleanup but retrieval is identically saturated — confirming the diagnostic's caveat that single-paper saturation extends into the recall=3 band.

---

## Case 1: NUT-016 — Intermittent fasting + performance/fat loss

**Query**: *"Does intermittent fasting negatively affect exercise performance or fat loss compared to regular eating patterns?"*

**Current top-5**: All 5 from Kazeminasab 2025 (single-paper saturation).

**Goal**: surface at least one chunk from each of Conde-Pipó 2024 and Aragon 2022.

| Paper | chunk | Priority | Verbatim content |
|---|---|---|---|
| Conde-Pipó 2024 | **20** | PRIMARY | Conclusions: *"the scientific evidence indicates that intermittent fasting does not negatively affect sports performance... As far as strength is concerned, it is not compromised by intermittent fasting"* |
| Conde-Pipó 2024 | 18 | Secondary | Discussion: *"in the TRF modality (16/8), there do not seem to be differences in the performance of physical capacities: aerobic, anaerobic, and strength and power"* |
| Conde-Pipó 2024 | 17 | Secondary | Discussion: adherence importance for IF success |
| Aragon 2022 | **4** | PRIMARY | *"Investigations of zero-calorie ADF... showed similar effectiveness and tolerability compared to DCR"* |

---

## Case 2: BC-010 — Supplements during weight loss

**Query**: *"What supplements can help preserve muscle mass during a weight loss diet?"*

**Current top-5**: 2 McCarthy & Berg + 3 Willoughby (partial saturation).

**Goal**: surface at least one chunk from Ruiz-Castellano 2021.

| Paper | chunk | Priority | Verbatim content |
|---|---|---|---|
| Ruiz-Castellano 2021 | **7** | PRIMARY | Macronutrients/Protein: *"One of the main goals during a fat loss phase in strength athletes, in addition to reducing FM, is to preserve FFM... optimal protein intake for resistance-trained athletes during an FM loss phase could be higher"* |
| Ruiz-Castellano 2021 | **1** | PRIMARY | Abstract: *"Protein intake (2.2-3.0 g/kgBW/day)... creatine monohydrate (3-5 g/day) could be incorporated"* |
| Ruiz-Castellano 2021 | 2 | Secondary | Intro: hypocaloric diet → FFM loss framing |

---

## Case 3: GEN-004 — Sex differences in resistance training

**Query**: *"Do men and women respond differently to resistance training in terms of muscle growth, fatigue, and recovery?"*

**Current top-5**: All 5 from Nuckols 2026 (single-paper saturation).

**Goal**: surface at least one chunk from each of Refalo 2025 and James 2025.

| Paper | chunk | Priority | Verbatim content |
|---|---|---|---|
| Refalo 2025 | **1** | PRIMARY | Abstract: *"Absolute increases in muscle size slightly favoured males (SMD=0.19)... relative increases in muscle size were similar between sexes"* — perfect match to expected fact 1 |
| Refalo 2025 | **33** | PRIMARY | Discussion: *"potential sex differences in short-term responses to RT, such as neuromuscular fatigue and muscle damage, may be greater in males"* — matches edited fact 2 |
| James 2025 | **22** | PRIMARY | Sex differences by activity level: type I/II CSA sex differences persist across subgroups |
| James 2025 | **23** | PRIMARY | Sex differences by muscle group: Type II SMD positive (favoring males) in back/trunk and leg |

---

## Case 4: CVD-001 — Resistance training and blood pressure

**Query**: *"Does resistance training and isometric exercise lower blood pressure, and how effective are they compared to medication?"*

**Current top-5**: All 5 from Edwards 2024 (single-paper saturation — but Edwards covers isometric facts which is correct).

**Goal**: surface at least one chunk from Correia 2023 (covers the RT-specific facts that Edwards doesn't).

| Paper | chunk | Priority | Verbatim content |
|---|---|---|---|
| Correia 2023 | **0** | PRIMARY | Abstract: *"SBP and DBP decreased significantly after strength training interventions. The strongest effect... moderate to vigorous load intensity (>60% 1RM)"* — covers facts 1 and 4 in one chunk |
| Correia 2023 | **4** | PRIMARY | Results: specific effect sizes — moderate intensity SBP -10.82 mmHg, DBP -6.96 mmHg |
| Correia 2023 | 1 | Secondary | Intro: BP reduction context |

---

## Case 5: BFR-004 — BFR safety + contraindications

**Query**: *"Is blood flow restriction training safe? What are the risks and contraindications?"*

**Current top-5**: All 5 from Nascimento 2022 (single-paper saturation).

**Goal**: surface at least one chunk from Patterson 2019.

| Paper | chunk | Priority | Verbatim content |
|---|---|---|---|
| Patterson 2019 | **18** | PRIMARY | Safety/VTE: *"the totality of the literature reveals minimal adverse events pertaining to VTE"* + VTE risk factor list (covers facts 1 and 3) |
| Patterson 2019 | **21** | PRIMARY | At-risk populations for VTE: risk factor combination + clinical prediction rules for BFR-RE candidate screening |
| Patterson 2019 | **2** | PRIMARY | Introduction: *"large incidence of numbness following BFR"* — direct match to fact 2 (minor side effects) |
| Patterson 2019 | 1 | Secondary | Abstract: overall safety guidelines |

---

## Case 6: STR-010 — Complex-contrast training

**Query**: *"What is complex-contrast training and how does it compare to plyometric training alone for developing explosive power?"*

**Current top-5**: 3 Wang 2023 chunks + 2 Thapa 2024 chunks (papers retrieved, but wrong chunks).

**Current top-20 status**: Wang ch 1 in top-20 but NOT top-5. Thapa ch 4 NOT in top-20.

**Goal**: surface Thapa ch 4 (the verbatim CCT definition) and Wang ch 1 (the verbatim PLT vs CT comparison) into top-5.

| Paper | chunk | Priority | Current rank | Verbatim content |
|---|---|---|---|---|
| Thapa 2024 | **4** | PRIMARY | Not in top-20 | Background: *"CCT is of further interest as it involves performing high-load and low-load exercises in alternating sequence that might result in post-activation performance enhancement (PAPE)"* + example sequence + effect-size comparisons (covers all 3 edited facts in one chunk) |
| Wang 2023 | **1** | PRIMARY | In top-20, not top-5 | Discussion/Conclusion: *"unloaded PLT and CT have a similar effect on explosive performance in the short term but loaded PLT has a better effect. The improvement of the maximum strength caused by CT was greater than that induced by PLT"* |

This is the chunk-level miss case (papers retrieved, chunks not). Reranking is the most direct fix; top_k bump helps with Wang ch 1.

---

## Cases 7-12 — added 2026-05-30 (full recall≤3 sweep)

Verified via parallel sub-agent reads of every expected paper, cross-referenced against live top-20 retrieval. These extend the retrieval-fixable set from 6 → 11. See `RECALL-FAILURE-DIAGNOSTIC.md` § "Full recall≤3 classification" for the complete picture (including the judge-bound and test-bound cases not listed here).

### Case 7: GEN-001 — RT variables for sarcopenia + mechanisms of age-related muscle loss
**Query**: *"What resistance training variables are important for combating sarcopenia, and what mechanisms drive age-related muscle loss?"*
**Current top-5**: All 5 from Delaire 2025 (single-paper saturation). Tøien and Govindasamy entirely absent from top-20.

| Paper | chunk | Priority | Content |
|---|---|---|---|
| Govindasamy 2025 | **3** | PRIMARY | *only* source for fact 2 mechanisms: *"altered hormones (insulin and thyroid), dysregulation of cytokine (interleukins, tumor necrosis...), altered protein kinetics"* |
| Govindasamy 2025 | **2** | PRIMARY | sarcopenia definition (fact 1): *"age-related muscular disorder characterized by loss of muscle mass and strength... difficulty performing activities of daily living"* |
| Tøien 2025 | **14** | PRIMARY | intensity + frequency (fact 3): *"2-3 training sessions per week... higher frequency associated with larger strength gains"*; 4×4RM @~90% 1RM |
| Tøien 2025 | **9** | PRIMARY | neuromuscular + anti-atrophy (fact 4): *"counteract the loss of muscle cross sectional area and muscle volume"* + efferent neural drive |
| Govindasamy 2025 | 40, 42 | Secondary | intensity/freq dose; MPS (Schulte) |
| Tøien 2025 | 3 | Secondary | intensity dose-response, ≥80% 1RM threshold |

### Case 8: NUT-014 — Intermittent fasting + RT for body composition / muscle retention
**Query**: *"Can I build muscle while doing intermittent fasting, and how does meal timing affect muscle growth?"* (see dataset for exact wording)
**Current top-5**: heavily polluted — **4 of 5 are reference-list/back-matter chunks** (Keenan 34, Aragon 18, Ho 26 refs + Williamson 12 mislabeled "AUTHOR CONTRIBUTIONS"). Only Keenan ch28 is substantive. This case is the strongest single argument for noise-chunk cleanup (ROADMAP #10).

| Paper | chunk | Priority | Content |
|---|---|---|---|
| Williamson 2021 | **6** | PRIMARY | facts 2+3 (MPS window): *"lost opportunity for AA-induced MPS with more feedings may not be compensated... with fewer feedings"* — currently rank 11 |
| Keenan 2020 | **31** | PRIMARY | facts 1+4 (LBM maintenance contingent on protein/energy) — currently rank 15 |
| Ho 2024 | **21** | PRIMARY | fact 1 (TRF+RT preserves FFM) — deep miss (not in top-20) |
| Williamson 2021 | 4, 10 | Secondary | muscle-full refractory period; fewer-meals harm to turnover |
| Keenan 2020 | 29 | Secondary | protein 1.2-1.9 g/kg in included studies |

### Case 9: NUT-022 — Vitamin D and athletic performance
**Query**: *"Does vitamin D supplementation improve athletic performance or strength?"* (see dataset for exact wording)
**Current top-5**: Han-saturated (Han fills 11 of top-20 slots). Fact 1 (quadriceps strength) is covered in top-5; the two quantitative facts live only in Wicinski, which is deep-missed.

| Paper | chunk | Priority | Content |
|---|---|---|---|
| Wicinski 2019 | **4** | PRIMARY | fact 3 — the only chunk with the figure: *"56% of [2313 athletes] had vitamin D inadequacy"* — deep miss |
| Wicinski 2019 | **10** | PRIMARY | fact 2: *"best enhancement... occurs to athletes with critically low baseline status (under 30 ng/mL)... improvements when baseline over 30 ng/mL... unnoticeable"* — deep miss |
| Han 2024 | 3 | Secondary | qualitative prevalence + adequate-level futility (rank 7) |
| Han 2024 | 1, 7 | (already top-5) | fact 1: quadriceps benefit, no bench/handgrip benefit |

### Case 10: BC-004 — Preserving lean mass during a cut
**Query**: *"How do I preserve muscle mass while cutting / in a caloric deficit?"* (see dataset for exact wording)
**Current top-5**: Xie-saturated (5 of top-13). Fact 1 in top-5 (Xie ch17); the precise protein figure and the "only modality" claim are deep-missed.

| Paper | chunk | Priority | Content |
|---|---|---|---|
| Ruiz-Castellano 2021 | **7** | PRIMARY | fact 2 — only home of the figure: *"protein intake of 2.3-3.1 g/kg FFM/day"* — deep miss |
| Lahav 2026 | **8** | PRIMARY | fact 4: *"RT was the only modality associated with preservation and an increase in FFM"* — deep miss (weak echo in Lahav ch0 @rank 10) |
| Lahav 2026 | 1, 10 | Secondary | "only modality" abstract/results variants |
| Ruiz-Castellano 2021 | 5 | Secondary | fact 3: weekly weight-loss rate 0.5-1% |

### Case 11: BFR-001 — How BFR training works / causes growth
**Query**: *"How does blood flow restriction training work and how does it build muscle?"* (see dataset for exact wording)
**Current top-5**: definitional + reference chunks dominate; **all mechanism chunks are outside top-20**. Davids reference chunks (28-32) occupy 5 slots.

| Paper | chunk | Priority | Content |
|---|---|---|---|
| Davids 2023 | **7, 8, 11, 12** | PRIMARY | fact 2 mechanisms: mTOR/anabolic signalling, satellite cells, *"full spectrum of fibre types recruited... metabolite depletion in larger type II fibres"* — all deep miss |
| Davids 2023 | **13** | PRIMARY | "combining mechanical and metabolic stimuli" — deep miss |
| Patterson 2019 | **5, 8** | PRIMARY | fact 3: *"BFR-RE induces comparable increases in muscle mass... 20-40% of maximum strength"* — deep miss |
| Patterson 2019 | 4 | Secondary | cell swelling / edema |
| Patterson 2019 | 2 | (already top-5, rank 2) | fact 1 definition (arterial/venous restriction, cuff) |

### Case 12: PROG-006 — Advanced techniques (drop sets, rest-pause) vs traditional
**Query**: *"What are advanced resistance training techniques like drop sets and rest-pause, and are they better than traditional training?"*
**Current top-5**: 4 Iversen 2021 + 1 Krzysztofik (Iversen isn't even an expected paper; Fonseca absent).
**⚠️ Partial test-bound** — only facts 1-2 are valid retrieval targets; fact 2 over-claims and fact 3 is ungrounded in Fonseca (see test-edit list in `RECALL-FAILURE-DIAGNOSTIC.md`).

| Paper | chunk | Priority | Content |
|---|---|---|---|
| Fonseca 2023 | **1** | PRIMARY | fact 1 — only chunk listing the techniques: *"drop-sets, forced repetitions, rest-pause... pre-exhaustive sets, supersets..."* |
| Fonseca 2023 | **0, 78** | PRIMARY | fact 2 (equivalence): *"ADV does not induce superior skeletal muscle hypertrophy... when compared with TRAD"* |
| Fonseca 2023 | 80 | Secondary | practical-applications restatement |

---

## Excluded Cases (Not Retrieval Problems)

These three are flagged separately because retrieval improvements cannot fix them:

| Case | Status | Required fix |
|---|---|---|
| **INJ-009** | Wu 2025 ch 24 already in top-5 | Judge prompt tightening — answer chunk retrieved but judge missed fact connection |
| **CVD-003** | Lee 2024 ch 2 already in top-5; test fact 2 rewritten on 2026-05-10 | After rerun, judge should now credit chunk 2 against the rewritten fact. If still scoring low, judge prompt issue. |
| **PROG-003** | No answer chunks exist in Paoli 2017 | Test-bound. Separate decision needed: rewrite expected facts to match what Paoli actually claims (it measures whether strength outcomes differ at equal volume between SJ and MJ), or swap to a paper that argues the original expected claims. |

---

## Success Criteria Summary

| Retrieval improvement | Expected behavior | Quantitative criterion |
|---|---|---|
| **top_k 5 → 8 (alone)** | Marginal. Wang ch 1 may enter top-8 for STR-010. Saturation cases unchanged. | 1-2 of 6 cases improve |
| **Per-paper diversification (max 2/paper in top-5)** | Breaks single-paper saturation. At least one chunk from each missing paper enters top-5 for the 5 saturation cases. | 5 of 6 cases improve to recall=4+ |
| **Cross-encoder reranking (top-30 → top-5)** | Surfaces the specific PRIMARY chunks listed above, not just any chunk from the right paper. | 6 of 6 cases improve to recall=4-5 |
| **All three combined** | All bolded PRIMARY chunks in top-5 for their queries. | 6 of 6 cases recall=5 on the retrieval-bound facts |

**Independent of judge**: count `(primary chunks in top-5) / (total primary chunks)`. A retrieval improvement is working if this ratio rises. If the ratio rises but eval recall scores don't, the bottleneck has shifted to the judge.

**Measured baseline (2026-05-30, pre-Phase-2): core 6 = `0/15` top-5 (`3/15` top-20); all 11 retrieval-fixable cases = `0/35` top-5 (`9/35` top-20).** Every primary chunk is currently absent from top-5. The bar is on the floor — any diversification/reranking that surfaces these chunks will register clearly. Re-run `scripts/measure_target_chunks.py` after each change and diff against `results/target_chunks_baseline.json`.

**End-state target after retrieval improvements + post-2026-05-10 test edits**:
- 6 retrieval-bound cases: recall 2 → 4 or 5
- INJ-009: small improvement or hold (judge-bound)
- CVD-003: small-to-moderate improvement (judge connection + rewritten fact aligns with retrieved chunk)
- PROG-003: hold or improve only if test rewritten separately
- **Overall Contextual Recall mean: 4.1 → projected ~4.4-4.6**
