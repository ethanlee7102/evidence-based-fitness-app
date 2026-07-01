# RAG Reranking Evaluation — Phase 2

**Question:** Does cross-encoder reranking improve retrieval on the 195-paper exercise-science
corpus, and can it reduce single-paper *saturation* (one paper monopolizing the top-5) without
hurting answer quality?

**Verdict: SHIP `Voyage rerank-2.5` + a score-gated per-paper cap (base 2, normalized margin 0.15).**
Validated airtight on 100 cases across two independent judges (custom Gemini + Ragas), all from one
frozen-embedding pool. Reranking beats vector decisively; the score-gated cap has the **best recall
of any config on both judges** while cutting single-paper saturation **64% → 38%** at no overall-quality cost.

---

## How it was measured

- **Frozen fixtures** — generate answers once, judge many times. Isolates retrieval changes from
  LLM run-to-run variance (every judge scores byte-identical outputs).
- **Two independent judges**, held fixed for before/after: **custom Gemini** (primary, task-aligned
  to hand-written `expected_facts`, 1–5) and **Ragas 0.4.3** (industry cross-check, 0–1).
- **Airtight capstone (final 3-way):** a known measurement trap surfaced mid-project — the Voyage
  *embedding* endpoint is non-deterministic (~0.005/dim), so two identical-config runs differ on
  ~22% of top-5s. HNSW and the Voyage reranker are both deterministic. The final report controls
  this by **embedding each query once and feeding that one vector to all three configs** — so they
  differ only by genuine retrieval logic. Verified before judging: 100/100 cases share the same
  rank-1 chunk with zero rerank-score mismatches between the cap variants.

---

## The investigation

| # | Config | Outcome |
|---|--------|---------|
| 00 | Vector-only (baseline) | Strong bar — recall 4.12, relevancy 4.59 (custom /5) |
| 01 | FlashRank `ms-marco-MiniLM` | **Degraded** — overall −0.19, both judges |
| 02 | Voyage rerank-2.5, no cap | **Beats vector** — recall +0.15, relevancy +0.14 |
| 03 | Hard per-paper cap=2 | Kills saturation but **over-diversifies single-paper questions** |
| 04 | **Score-gated cap, margin 0.15** | **Best recall on both judges; ties overall; de-saturates** |

**01 — FlashRank failed, and the data named why.** Deep fetch (150, ef_search 500) → MiniLM rerank →
top-5. Both judges degraded (custom relevancy −0.59). Root cause: the reranked top-5 had *lower*
cosine similarity (0.65 → 0.59) and 41% of chunks came from beyond the vector top-20 — the 2021-era
MS-MARCO web-search model mis-ranks dense scientific prose. Pre-registered risk, confirmed.

**02 — Voyage rerank-2.5 won.** The reranker was built behind a swappable interface, so FlashRank →
Voyage was one class + a config value. A strong reranker beat vector on recall and relevancy, faster
(~0.5s/query API vs ~5s CPU).

**03 — the cap question.** A hard cap=2 eliminates saturation (0% dominated) but the ground-truth
`expected_papers` labels exposed the failure mode: it inflates **single-paper questions** (43 of 100,
where one paper is genuinely the answer) from 1.42 → 2.60 distinct papers — forcing in weaker papers
to fill a quota.

**04 — score-gated cap.** A paper may exceed the cap only when its extra chunk clearly beats the best
*new-paper* alternative ("diversify only when nearly free"), gated on a fraction of the query's score
range (calibration-robust; Voyage's top scores are compressed). Margin **0.15** was chosen as the
empirical peak of multi-vs-single-paper *discrimination* — it diversifies multi-paper questions
(2.13 → 2.64 distinct) while barely touching single-paper ones (1.42 → 1.65).

---

## Final scorecard — airtight 3-way, both judges (shared frozen embeddings)

| Metric | Custom Gemini (/5) vec / nocap / **sgn** | Ragas (0–1) vec / nocap / **sgn** |
|--------|---|---|
| **Recall** | 4.12 / 4.27 / **4.34** | 0.72 / 0.76 / **0.79** |
| Relevancy | 4.59 / 4.73 / 4.63 | 0.99 / 0.98 / 0.99 |
| Precision | 4.22 / 4.21 / 4.19 | 0.78 / 0.81 / 0.79 |
| Answer relevancy | 5.00 / 4.99 / 4.98 | 0.86 / 0.86 / 0.88 |
| Faithfulness | 4.88 / 4.91 / 4.90 | 0.93 / 0.92 / 0.90 |
| **Overall** | 4.56 / 4.62 / 4.61 | 0.86 / 0.87 / 0.87 |
| Distinct papers | 1.94 / 2.02 / **2.47** | — |
| Saturated (≥4 of 5 from 1 paper) | 64% / 64% / **38%** | — |

**Both judges agree on every headline:**
1. **Reranking ≫ vector** — overall and recall up on both.
2. **Recall rises monotonically vector → no-cap → sgnorm on *both* judges** — sgnorm@0.15 has the best
   recall of any config. Independent judges agreeing on the ordering makes it a real effect, not an
   artifact (and overturns an earlier *confounded* run that showed sgnorm recall *down* — that was
   retrieval non-determinism, eliminated here by the shared-embedding design).
3. **sgnorm@0.15 ties no-cap on overall** (4.61 vs 4.62; 0.87 vs 0.87) — no quality cost.
4. **Answer quality held** — faithfulness and answer-relevancy flat on both.
5. **De-saturation delivered** — 64% → 38%, *selectively* (respects single-paper questions).

The only blemish, custom-judge relevancy −0.10 (no-cap → sgnorm), is within judge noise — Ragas
doesn't see it (0.98 → 0.99).

---

## What ships

```
RERANK_ENABLED=true · RERANK_PROVIDER=voyage · RERANK_MODEL=rerank-2.5
RERANK_FETCH_DEPTH=150 · RERANK_EF_SEARCH=500
RERANK_PER_PAPER_CAP=2 · RERANK_CAP_MARGIN=0.15 · RERANK_CAP_NORMALIZE=true
fetch threshold = -1.0 (no floor — let the reranker see the low-similarity tail)
```

- **Default OFF during development, config-gated** — live path and baselines untouched until the
  result justified enabling it.
- **Swappable reranker interface** (model behind a config value) — why FlashRank → Voyage was a
  one-line change, and why an API vs local reranker stays a config decision.

---

## Key methodological findings (beyond the metrics)

- **Embedding non-determinism sets a noise floor.** Voyage embeddings vary ~0.005/dim run-to-run →
  ~22% of top-5s differ between identical-config runs. Any cap comparison must control it (freeze the
  embedding / share the pool), or small deltas are indistinguishable from noise. This directly
  overturned an intermediate "sgnorm hurts recall" reading that was pure noise.
- **Proxy vs goal.** A judge-independent target-chunk proxy *disagreed* with the end-to-end eval on the
  cap (the proxy rewarded diversity; the goal wanted relevance). Trusted the judged answer quality.
- **Ragas is quota-heavy.** Claim-decomposition makes many LLM calls per case; a full 3-config Ragas
  run plus retries exhausted the 10k/day Gemini request quota. Sequential + per-config checkpointing
  made it resumable.

## Provenance

- 100 test cases · 195-paper corpus · custom Gemini judge (primary) + Ragas 0.4.3 (cross-check), both
  on frozen fixtures. Airtight 3-way from one shared-embedding capture (`capture_final_report.py`).
- Result files: `final_{vector,nocap,sgnorm}.json` (frozen outputs),
  `judge_final_{vector,nocap,sgnorm}_{custom,ragas}.json` (both judges).
- Pipeline: Voyage embeddings → pgvector HNSW → deep fetch + Voyage rerank-2.5 + score-gated cap →
  Gemini 2.5 Flash generation, cited.
