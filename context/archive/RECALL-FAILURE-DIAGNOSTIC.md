# Recall Failure Diagnostic — Post-Expansion Eval (2026-03-19)

Classification of the 9 test cases that scored `Contextual Recall = 2` in `results/post_expansion.json`. Goal: separate retrieval problems (fixable by top_k/reranking) from corpus problems (need more papers) from judge/test-authoring problems (rewrite expected facts or judge prompts).

This diagnostic went through three rounds:
1. **First pass** (keyword scan only): overstated chunk-level miss findings.
2. **Second pass** (retrieval rerun): revealed single-paper saturation as the dominant failure mode and corrected the chunk-level miss claims.
3. **Third pass** (end-to-end chunk reading): identified test-authoring issues — expected facts that contradict or aren't claimed in source papers. **Test edits applied 2026-05-10** (backup: `apps/api/tests/eval/test_dataset.json.bak.2026-05-10`).

Post-edit state: the eval test dataset now contains expected facts that are grounded in the source papers, so future eval runs will reflect pure retrieval performance rather than test-authoring artifacts.

---

## Headline Results

**Zero pure corpus gaps.** All 19 expected papers across the 9 failures are in the corpus.

**Dominant failure mode: single-paper saturation in retrieval.** For 5 of 9 cases, the top-5 retrieved chunks are monopolized by a single paper, even when multiple on-topic expected papers exist in the corpus.

**Test-authoring issues identified and resolved** (2026-05-10): 5 test cases had expected facts that contradicted or weren't claimed by the source papers. Those facts have been rewritten or removed in `test_dataset.json`. Net change: 18 → 15 facts across the affected cases.

| Classification | Count | Cases | Status |
|---|---|---|---|
| **Single-paper saturation** — top-5 monopolized by 1 paper; other on-topic expected papers never appear | 5 | NUT-016, BC-010, GEN-004, CVD-001, BFR-004 | Pending retrieval improvements (diversification + reranking) |
| **Chunk-level retrieval miss** — relevant paper retrieved but answer-chunk outside top-5 | 1 | STR-010 | Pending retrieval improvements (reranking + top_k bump) |
| **Judge connection issue** — answer chunk is in current top-5 but judge didn't credit the fact | 2 | INJ-009, CVD-003 | Pending judge prompt improvements; CVD-003 test fact 2 also rewritten |
| **Test-authoring issues (resolved)** | — | NUT-016 fact 3, BC-010 fact 3, GEN-004 facts 2&3, CVD-003 fact 2, STR-010 fact 4 | **Resolved 2026-05-10** — facts rewritten or removed |
| **Test-bound (unresolved)** | 1 | PROG-003 | Paoli 2017 doesn't claim either expected fact. Separate decision needed: rewrite or swap source paper. |
| **Corpus gap** | 0 | — | — |

---

## Methodology

Three-stage check using existing data plus fresh retrieval runs:

1. **Paper-level**: cross-reference each case's `expected_papers` against `papers/manifest.json`. Match by first-author surname + year.
2. **Chunk-level keyword scan**: for each missing fact, query Supabase for all chunks of the source paper and find chunks containing phrase groups that match the fact semantically.
3. **Retrieval rerun**: actually re-run `retrieve_chunks()` at `top_k=5` and `top_k=20` for each of the 9 failure queries. Compare the high-match chunks identified in stage 2 against the retrieved set.

Stage 3 is the key fix from the previous draft. Without it, I was inferring "chunk wasn't retrieved" from "chunk has the answer", which is a logical gap.

---

## Per-Case Findings

### Single-paper saturation (5)

The current retrieval clusters all top-5 results from one paper, even when other clearly on-topic expected papers exist in the corpus.

| Case | Top-5 papers retrieved | Expected papers in corpus but NOT in top-5 |
|---|---|---|
| **NUT-016** | All 5 from Kazeminasab 2025 | Conde-Pipó 2024 *"Intermittent Fasting: Does It Affect Sports Performance?"*, Aragon 2022 *"Does Timing Matter?..."* |
| **BC-010** | 2 McCarthy & Berg + 3 Willoughby | Ruiz-Castellano 2021 *"Achieving an Optimal Fat Loss Phase..."* |
| **GEN-004** | All 5 from Nuckols 2026 | Refalo 2025 *"Sex differences in muscle size..."*, James 2025 *"Sex differences in skeletal muscle fiber types..."* |
| **CVD-001** | All 5 from Edwards 2024 | Correia 2023 *"Strength training for arterial hypertension..."* |
| **BFR-004** | All 5 from Nascimento 2022 | Patterson 2019 *"BFR Exercise: Considerations of Methodology, Application, and Safety"* |

**Verified answer-chunks in the missing papers** (full chunk-level scan with phrase-group matching). These are the specific chunks retrieval improvements should aim to surface:

| Case | Paper | Verified answer chunk(s) | Content |
|---|---|---|---|
| **NUT-016** | Conde-Pipó 2024 (26 chunks) | **chunk 20** (Conclusions) | *"the scientific evidence indicates that intermittent fasting does not negatively affect sports performance and does affect the improvement of body composition"* — verbatim conclusion |
|  |  | chunks 6, 7 (Results) | results tables covering strength/anaerobic effects of IF |
|  |  | chunks 18, 2 | IF vs continuous caloric restriction comparison |
|  | Aragon 2022 (25 chunks) | **chunk 4** (Intra-Week Fasting) | *"ADF... showed similar effectiveness and tolerability compared to DCR"* — direct equivalence claim |
|  |  | chunks 6, 7 | resistance training combined with fasting findings |
| **BC-010** | Ruiz-Castellano 2021 (42 chunks) | **chunk 1** (Abstract) | retention of fat-free mass during weight loss, protein context |
|  |  | **chunk 22** (Section 8. Supplementation) | creatine + strength during fat loss phase |
|  |  | chunk 7 (Macronutrients) | MPS suppression during energy deficit |
| **GEN-004** | Refalo 2025 (43 chunks) | **chunk 1** (Abstract) | *"meta-analysis investigated absolute and relative changes in muscle size following resistance training between males and females"* |
|  |  | chunk 33 (Discussion) | fatigue resistance similarity discussion |
|  | James 2025 (61 chunks) | **chunk 22, 23** (Sex differences subsections) | type II CSA sex differences across activity levels and muscle groups |
| **CVD-001** | Correia 2023 (59 chunks) | **chunk 0, 1** | abstract + intro of "Strength training for arterial hypertension treatment" |
|  |  | chunk 4 (Results) | load intensity findings (60-70% 1RM most common) |
| **BFR-004** | Patterson 2019 (43 chunks) | **chunk 1** (Abstract) | overall safety guidelines for BFR |
|  |  | **chunk 18, 21** (Safety / Venous Thromboembolism) | DVT contraindications |
|  |  | chunks 2, 22 | numbness, soreness side effects |

**Implication**: this is NOT solved by simply bumping `top_k` from 5 to 8. Slots 6-8 in the same retrieval rerun also tend to be from the same dominant paper. The actual fix is one of:
- **Per-paper diversification** at retrieval time (e.g., max 2 chunks per paper in top-k).
- **Cross-encoder reranking** of a larger candidate set (top-30 → top-5) — this breaks saturation because the reranker scores by question-chunk relevance rather than embedding similarity that clusters within-paper.
- **Two-stage retrieval** (search abstracts first to identify N relevant papers, then chunks within those papers).

### Chunk-level retrieval miss (1)

**STR-010** — *"What is complex-contrast training and how does it compare to plyometric training alone for developing explosive power?"*

Both expected papers (Thapa 2024, Wang 2023) ARE retrieved at the paper level. The retrieval rerun shows:
- Current top-5: Wang chunks {2, 0, 30}, Thapa chunks {36, 33}
- The verbatim-answer chunks are: Wang chunk 1 (Discussion/Conclusion stating *"unloaded PLT and CT have a similar effect on explosive performance...maximum strength caused by CT was greater than that induced by PLT"*), Thapa chunk 4 (Background defining CCT as alternating high/low load with PAPE).
- Wang chunk 1 appears in top-20 but NOT top-5. Thapa chunk 4 doesn't appear even in top-20.

**Implication**: bump top_k to ~20 + rerank to surface the actual answer chunks. This is the failure mode reranking is specifically designed for.

**Note on Wang attribution**: the corpus has TWO Wang 2023 papers — one on BMD (wrong) and one on plyometric vs complex training (right). My first-pass diagnostic accidentally checked the wrong one. The correct Wang 2023 IS in the corpus and on-topic.

### Not a retrieval problem (2)

These cases scored recall=2 in the eval, but the retrieval rerun shows the answer chunks ARE in the current top-5.

**INJ-009** — *"What exercise modes are recommended for rotator cuff-related shoulder pain?"*
- Wu chunk 24 (Conclusion: *"This article demonstrates that specific modes of exercise for the shoulder can enhance both pain relief and functional status in patients with Rotator Cuff-Related Shoulder Pain"*) IS in current top-5.
- The eval's recall=2 likely reflects judge fallibility — the chunk was retrieved but the judge didn't connect it to the expected fact wording.

**CVD-003** — *"Should I do cardio, resistance training, or both for reducing cardiovascular disease risk?"*
- Lee chunk 2 IS in current top-5. It contains the verbatim conclusion: *"aerobic exercise alone or combined resistance plus aerobic exercise, but not resistance exercise alone, improved composite CVD risk profile compared with the control."*
- This case has TWO sub-issues:
  - **Judge issue**: chunk 2 directly states "combined > RT alone" but the judge marked fact 1 ("combined more effective than either alone") as not_found.
  - **Test-bound contradiction**: expected fact 2 says *"Resistance training alone has independent cardiovascular benefits"* — but Lee 2024's actual finding is the **opposite**: RT alone did NOT improve composite CVD risk. The test expects a fact that contradicts the source paper.

**Implication**: these two failures will NOT be improved by any retrieval change. They need:
- Tighter judge prompt or retry-on-uncertainty (covers fact-wording mismatches).
- Rewriting the contradictory expected fact in CVD-003 to match what Lee actually claims.

### Test-bound (1)

**PROG-003** — *"Are compound exercises sufficient or do I need isolation exercises too?"*

Expected facts: "isolation needed for muscles compound underload" and "compound more time-efficient because multi-muscle recruitment". 

Keyword scan of all 19 chunks of Paoli 2017 found no strong matches. Top "matches" were in metadata/header sections (peer-review info, data tables) with single coincidental keyword hits. Paoli 2017's actual scope: comparing single-joint vs multi-joint exercises at equal total load volume — it measures whether strength outcomes differ at equal volume. It doesn't substantively argue either of the expected facts.

**Implication**: rewrite the expected facts to match Paoli's actual claims, OR swap the source paper.

---

## Implications for the Plan — Revised

The original ROADMAP entry assumed top_k bump + reranking would fix ~8 of 9 cases. The reality is more nuanced:

| Improvement | Cases it actually fixes |
|---|---|
| **Priority A (top_k 5→8-10)** — minor, single-paper saturation persists | 0-1 (helps STR-010 partially) |
| **Per-paper diversification** *(new — not in current FUTURE-PLANS)* | 5 (all single-paper saturation cases) |
| **Priority C (cross-encoder reranking)** — biggest impact, breaks saturation | 5 + STR-010 = 6 |
| **Priority B (noise cleanup)** — multiplier on the above | indirect |
| **Priority E (judge JSON retry) + judge prompt tightening** | 2 (INJ-009, CVD-003 fact 1) |
| **Test-case rewrite** | 2 (PROG-003, CVD-003 fact 2) |

**Realistic ceiling after all retrieval+rerank improvements: 6 of 9 recall failures.** Two more require judge/eval-system changes. One requires rewriting the test case (PROG-003 — still pending).

**Update 2026-05-10**: test-authoring issues now resolved for 5 cases. Future eval runs on these cases reflect pure retrieval performance, no longer confounded by test-wording mismatches. PROG-003 still has the open test-bound decision.

**Projected post-improvement state** (after retrieval changes are made):
- 6 retrieval-bound cases (NUT-016, BC-010, GEN-004, CVD-001, BFR-004, STR-010): recall 2 → 4 or 5
- INJ-009: judge-bound, modest improvement
- CVD-003: judge connection + cleaner test fact, moderate improvement
- PROG-003: hold unless test rewritten
- **Overall Contextual Recall: 4.1 → projected ~4.4-4.6** depending on which retrieval improvements land

### Priority shift suggested

Add **per-paper diversification** to the retrieval priority list. It's the single most direct fix for the dominant failure mode and isn't in the current `FUTURE-PLANS.md`. Implementation: cap chunks-per-paper at 2 in the `match_chunks` RPC, or post-filter the SQL results.

Reranking (Priority C) remains highest-ROI because it solves the same problem AND chunk-level misses AND noise displacement — three failure modes with one fix.

Priority A (top_k bump) is **less load-bearing than I claimed.** It buys candidate diversity but doesn't help with saturation if the saturated paper's chunks fill slots 6-20 too. It's a free input multiplier for the reranker, not a standalone fix.

---

## What This Diagnostic Does Not Cover

- **Why retrieval is saturating on single papers**: could be embedding similarity clustering within paper (chunks from same paper share vocabulary and structure), could be that some papers have many more chunks than others giving them more shots at top-k. Probably both.
- **Whether the eval-time retrieval was identical to today's retrieval**: I assumed it was. If the corpus changed since 2026-03-19, the comparisons for the "not a retrieval problem" cases are weaker. Corpus has not changed by paper count, but if any reingestion happened, chunk IDs/indices might differ.
- **The recall=3 cases**: this only looked at recall=2 failures. The single-paper saturation pattern likely extends to recall=3 cases too, where on-topic papers exist but ranked just outside top-5.

---

## Source Files

- Eval results: `apps/api/results/post_expansion.json`
- Test dataset: `apps/api/tests/eval/test_dataset.json`
- Corpus manifest: `apps/api/papers/manifest.json`
- Raw per-case data (paper-level + initial keyword scan): `/tmp/recall_failures.json`, `/tmp/chunk_probe.json`
- Refined phrase-group scan: `/tmp/chunk_probe_v2.json`
- Retrieval rerun (top-5 and top-20 for all 9 queries): `/tmp/retrieval_rerun.json`
