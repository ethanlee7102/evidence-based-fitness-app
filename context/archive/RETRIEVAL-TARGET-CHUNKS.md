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

**End-state target after retrieval improvements + post-2026-05-10 test edits**:
- 6 retrieval-bound cases: recall 2 → 4 or 5
- INJ-009: small improvement or hold (judge-bound)
- CVD-003: small-to-moderate improvement (judge connection + rewritten fact aligns with retrieved chunk)
- PROG-003: hold or improve only if test rewritten separately
- **Overall Contextual Recall mean: 4.1 → projected ~4.4-4.6**
