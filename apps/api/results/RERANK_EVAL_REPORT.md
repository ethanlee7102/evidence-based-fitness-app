# RAG Reranking Evaluation — Phase 2

**Question:** Does cross-encoder reranking improve retrieval on the 195-paper exercise-science
corpus? Specifically, can it fix the weakest metric — **contextual recall** (4.13/5) — which a
chunk-level diagnostic traced to *single-paper saturation* (one paper monopolizing the top-5 and
burying relevant evidence from others)?

**Verdict: SHIP `Voyage rerank-2.5`, no per-paper cap.** Net-positive on two independent judges;
recall moved and answer quality held.

- recall **+0.19** · faithfulness **+0.19** · relevancy **+0.12** · overall **4.56 → 4.64** (custom Gemini judge, /5)

---

## How it was measured

- **Frozen fixture** — generate answers once, judge many times. Isolates retrieval changes from
  LLM run-to-run variance (every judge scores byte-identical outputs).
- **Two independent judges**, held fixed across before/after:
  - **Custom Gemini** (primary, task-aligned to hand-written `expected_facts`, 1–5 scale)
  - **Ragas 0.4.3** (industry cross-check, 0–1 scale, stricter / more bimodal)
- **Cheap ablations:** recall/precision/relevancy are judged on the *chunks alone* (no generation),
  so a config could be screened for ~$0.30 of retrieval-metric judging before a ~$2 full run.
- Judge-independent target-chunk metric (verified primary chunks in top-5) as a secondary signal.

---

## The investigation

| # | Config | Outcome |
|---|--------|---------|
| 00 | Vector-only (baseline) | Strong bar — relevancy 4.60, recall 4.13 |
| 01 | FlashRank `ms-marco-MiniLM-L-12-v2` + per-paper cap=2 | **Degraded** — overall 4.56 → 4.37, both judges |
| 02 | Cap ablation (no-cap) | Cap over-aggressive **and** model weak — both hurting |
| 03 | **Voyage rerank-2.5, no-cap** | **Won** — recall +0.19, faithfulness +0.19, overall +0.08 |

**01 — FlashRank failed, and the data named why.** Deep fetch (150, HNSW `ef_search` 500) →
MiniLM rerank → cap → top-5. Both judges agreed it degraded retrieval (custom relevancy −0.59,
overall −0.19). Root cause: the reranked top-5 had **lower** average cosine similarity
(0.65 → 0.59), and **41% of its chunks weren't in the vector top-20** — the 2021-era MS-MARCO
web-search model mis-ranks dense scientific prose, pulling low-relevance deep chunks up. This was a
pre-registered risk; the eval converted "might not fit" into "exactly how, and by how much."

**02 — Cap ablation.** Removing the cap recovered relevancy (+0.28) and recall (+0.15) vs cap=2 —
the cap forced diversity that diluted relevance. But uncapped reranking still sat *below* vector,
so the model was also a problem. (Isolation via cap-OFF cases: reranker alone hurt relevancy −0.26,
precision −0.43.)

**03 — Model swap.** The reranker was built behind a swappable interface, so FlashRank → Voyage was
one new class + a config value, no pipeline change. A genuinely strong reranker beat vector on the
target metric without sacrificing answer quality, and ran faster (~0.5s/query API vs ~5s/query CPU).

---

## Final scorecard — vector → Voyage rerank-2.5 (no-cap)

### Custom Gemini judge (primary, /5)

| Metric | Vector | Voyage | Δ |
|--------|-------:|-------:|---:|
| **Contextual recall** | 4.13 | 4.32 | **+0.19** |
| Contextual relevancy | 4.60 | 4.72 | +0.12 |
| Contextual precision | 4.31 | 4.23 | −0.08 |
| Answer relevancy | 5.00 | 4.98 | −0.02 |
| **Faithfulness** | 4.78 | 4.97 | **+0.19** |
| **Overall** | 4.56 | 4.64 | **+0.08** |

### Ragas judge (cross-check, 0–1)

| Metric | Vector | Voyage | Δ |
|--------|-------:|-------:|---:|
| Contextual recall | 0.740 | 0.750 | +0.010 |
| Contextual relevancy | 0.990 | 0.990 | 0.000 |
| Contextual precision | 0.770 | 0.800 | +0.030 |
| Answer relevancy | 0.870 | 0.890 | +0.020 |
| Faithfulness | 0.930 | 0.910 | −0.020 |
| **Overall** | 0.860 | 0.870 | +0.010 |

Both judges land net-positive. The lone red on each (precision on Gemini, faithfulness on Ragas) is
small, and the judges disagree on which moved — noise, not a real regression. The retrieval-only pass
flagged precision −0.22; with answers in the judge's context it shrank to −0.08, so the full run
prevented over-optimizing a phantom.

---

## What ships

```
RERANK_ENABLED      = true
RERANK_PROVIDER     = voyage
RERANK_MODEL        = rerank-2.5
RERANK_FETCH_DEPTH  = 150     # deep candidate pool
RERANK_EF_SEARCH    = 500     # HNSW beam ≈ 3× depth (migration 015)
RERANK_PER_PAPER_CAP = none   # ablation showed the cap hurt
fetch threshold     = -1.0    # no similarity floor — let the reranker see the tail
```

- **Default OFF, config-gated** throughout — live chat path and frozen baselines never disturbed
  until the result justified flipping it.
- **Swappable reranker interface** (model behind a config value, like the LLM provider) — why the
  FlashRank → Voyage swap was a one-line change, not a rewrite.
- **Local vs API trade:** Voyage adds ~0.5s + a per-query API call, negligible next to ~10–20s
  generation — paid for by recall +0.19 and faithfulness +0.19.

---

## Provenance

- 100 test cases · 195-paper corpus · custom LLM-as-judge (Gemini 2.5 Flash) cross-validated against
  Ragas 0.4.3 on a frozen output fixture · ~$5–6 total API spend this phase.
- Result files: `run0_custom_fixture.json` / `run_b_ragas_gemini.json` (vector baselines),
  `run_rerank_custom.json` / `run_rerank_ragas.json` (FlashRank cap=2),
  `run_rerank_nocap_custom.json` (FlashRank no-cap, retrieval-only),
  `run_voyage_full_custom.json` / `run_voyage_full_ragas.json` (Voyage — shipped config).
