# RAG Project Roadmap — Decisions Log

**Project framing**: portfolio builder for jump #1 at 1 YOE. Realistic target list: Junior AI Engineer / AI Engineer at Series A/B AI-first startups, OR Software Engineer / Backend Engineer doing AI work at Series A/B/C AI-using companies. Comp $110-150k base. Not jump-#2 targets (frontier labs, Tier 1 stable, Senior-level destination titles). **Work quality is senior-tier** — the calibration is about realistic interview positioning, not corner-cutting. Senior-tier depth at 1 YOE is exactly the trajectory signal that lands these roles. Full narrative in `context/PORTFOLIO-NARRATIVE.md`.

A walk-through list of every project decision. For each: question, realistic options, recommendation, and a `**Decision:**` line. Some are already committed (marked `Decision: COMMITTED` or `Decision: DONE`); others are pending your call. Once all are decided, this doc is the source of truth for what to build next.

**Decisions status (as of 2026-05-10)** — all 21 decisions are now resolved:
- ✅ DONE (2): #8a (recall failure diagnostic), test dataset cleanup (5 cases edited)
- ✅ COMMITTED (16): #1 (Run A), #2 (Run B with Ragas), #4 (Haiku 4.5 judge), #5 (synthetic ground-truth), #7 (LangSmith), #8 (keep both traces), #9 (top_k bump to ~20), #10 (noise cleanup), #11 (FlashRank reranking), #13 (judge JSON retry), #15 (README "Tools Considered"), #16 (interview notes), #17 (one blog post), #18 (Phase 1/2/3 build order), #19 (Phase 5 agentic before Phase 4), #20 (cap at ~4-6 weekends)
- ❌ SKIP (2): #3 (Run C), #6 (extra baseline rerun)
- ⏸️ DEFERRED (2): #12 (abstract-augmented retrieval — revisit after #9/#10/#11), #14 (hybrid retrieval — revisit only if post-Phase-2 precision problems emerge)

This doc is now the authoritative roadmap. Build order in decision #18.

**Context (already decided):**
- Target audience for jump #1: Series B/C/D AI-using companies, not frontier labs
- v2 orchestration: LangGraph (matches day-job stack, skip the custom-state-machine build)
- Drop the dual-build (custom + LangGraph in parallel) — time better spent on networking/applications

---

## Eval validation

### 1. Run A — cross-model run with custom judge + Claude Haiku 4.5 on 100 cases
- **Options:** do it / skip it
- **Recommendation:** do it. ~1 day work, ~$1.50-3 in API cost (Haiku 4.5), high-ROI across all target audiences. This is the load-bearing experiment for the "is my judge model-stable?" question.
- **Decision: COMMITTED.** Load-bearing experiment for ROADMAP Phase 1. Run B (Ragas) and the judge model choice (Haiku 4.5) are downstream of this and already committed, so Run A is effectively required.

### 2. Run B — Ragas + Gemini comparison on same 100 cases
- **Options:** do it / skip it / hold based on Run A results
- **Framework choice (researched 2026-05-10)**: Ragas direct over DeepEval. Ragas is the canonical reference implementation (cleaner narrative + better reproducibility), no telemetry, no vendor lock-in. DeepEval's RAGAS submodule is a reimplementation, not the real thing — using it would weaken the "validated against the industry standard" claim. The LangChain dependency Ragas pulls (`langchain-google-genai`) is fine because you're already a selective LangChain user (chunking + LangSmith + LangGraph for v2). Tradeoff accepted: ~1-2 days of ad-hoc inspection work when scores diverge, since Ragas doesn't bundle per-metric reasoning output.
- **Decision: COMMITTED — Ragas direct.** Run B is in-scope regardless of Run A results. Reframed as "characterizing custom eval against the industry-standard tool" rather than "deciding whether to use Ragas." Adds defensible cross-implementation data alongside Run A's cross-model data.

### 3. Run C — Ragas + Claude (the original maximalist 2×2 fourth run)
- **Options:** do it / skip it
- **Recommendation:** skip unless A and B both surface confusing results that need disambiguation.
- **Decision: SKIP.** Two-axis validation (Run A custom+Claude, Run B Ragas+Gemini) is sufficient for a portfolio comparison. Run C only revisited if A and B disagree confusingly.

### 4. Judge model for Run A
- **Options:** Claude Haiku 4.5 / Claude Sonnet 4.6 / GPT-4o / GPT-4o-mini
- **Recommendation:** Claude Haiku 4.5. Cost: ~$1.50-3 per run vs ~$5-8 for Sonnet 4.6. Methodologically equivalent for cross-validation purposes (different model family from Gemini, capable enough for structured eval). A cheaper model agreeing with the custom judge actually shows *robustness across capability tiers*, not just across model families — methodologically stronger than the expensive option. Anthropic ecosystem alignment preserved. GPT-4o-mini is an even cheaper alternative (~$0.30-0.60/run) but Haiku has better association with structured eval tasks in 2026.
- **Decision: COMMITTED — Claude Haiku 4.5.** Sonnet 4.6 retained as documented fallback in `EVAL-PLAN.md` if Haiku produces noisy or inconsistent scoring.

### 5. Ragas ground-truth strategy (only relevant if Run B happens)
- **Options:** synthesize ground-truth strings from existing `expected_facts` field / hand-write 100 ground-truth answers (~2 hrs of manual work)
- **Recommendation:** start synthetic, upgrade to hand-written only if `context_recall` scores look noisy.
- **Decision: COMMITTED — start synthetic** (auto-generated from `expected_facts` by joining the fact list into a single reference string). Handled programmatically as part of the Ragas runner build (no manual work needed upfront). Escalate to hand-written ground truth only if Run B produces noisy `context_recall` scores.

### 6. Re-run baseline (Run 0) for freshness
- **Options:** re-run / skip
- **Recommendation:** skip. Corpus hasn't changed since 2026-03-19.
- **Decision: SKIP.** Note: post test-cleanup (2026-05-10), the original baseline scores on the 5 edited cases will shift slightly. Phase 1 still produces a fresh baseline against the cleaned dataset as part of the standard sequence — this is just deciding not to do an *extra* rerun before that.

---

## Observability

### 7. Trace UI layer
- **Options:** LangSmith / Arize Phoenix / skip entirely (keep custom `rag_traces` only)
- **Recommendation:** LangSmith. Matches the LangChain ecosystem you use at work. Phoenix is the local-first alternative if you want to avoid vendor lock-in; either is defensible. Skipping leaves a screenshot-worthy README artifact on the table for ~half a day of work.
- **Decision: COMMITTED — LangSmith.** Aligns with day-job stack, native LangGraph integration for v2, ~half a day to layer on top of existing custom `rag_traces` table.

### 8. Custom `rag_traces` table — keep, replace, or run both
- **Options:** keep alongside trace UI / replace with LangSmith only / drop the trace UI and keep only custom
- **Recommendation:** keep alongside. Durable storage in Supabase + live debugging UI in LangSmith serve different purposes.
- **Decision: COMMITTED — keep both.** Custom `rag_traces` for durable structured storage tied to schema; LangSmith for live debugging UI and screenshots.

---

## Retrieval improvements (FUTURE-PLANS Priorities A-E + roadmap addition)

### 8a. Recall failure diagnostic (prerequisite before #9-14)
Manually inspect the 9 cases that scored 2 on `Contextual Recall` in the post-expansion eval. For each, classify the cause:
- **Retrieval-bound**: the missing `expected_facts` *are* present somewhere in the corpus but weren't in the retrieved top-k. → Fixable by #9 (top_k bump), #11 (reranking).
- **Corpus-bound**: the facts aren't anywhere in the 195 papers. → Needs more papers in that category, not a better retriever.
- **Test-bound**: the facts were never grounded in the corpus to begin with (test case overreaches). → Trim or rewrite the expected facts.

Why do this first: if half the low-recall cases are corpus or test-bound, the retrieval improvements (#9/#10/#11/#13) will move the score less than expected, and you'd waste analysis time wondering why. The classification sets realistic expectations and tells you whether you need more papers in specific categories.

- **Cost:** ~1-2 hours of manual review.
- **Options:** do it / skip and just run the improvements
- **Recommendation:** do it. Cheap, removes ambiguity from later eval results, and the classification is itself a writeup-worthy artifact.
- **Decision: DONE** (two rounds — first round overstated chunk-level misses; revised version uses fresh retrieval rerun for verification). Full results in `context/RECALL-FAILURE-DIAGNOSTIC.md`. Revised headline:
  - **0 corpus gaps** — all 19 expected papers are in the corpus
  - **5 single-paper saturation** (NUT-016, BC-010, GEN-004, CVD-001, BFR-004): top-5 monopolized by 1 paper even when other on-topic expected papers exist. NOT fixable by simple top_k bump — slots 6-20 also tend to be from the saturating paper. Needs per-paper diversification or reranking. Full forensic detail (per-case analysis, verified answer chunks) in `context/archive/RECALL-FAILURE-DIAGNOSTIC.md` and `context/archive/RETRIEVAL-TARGET-CHUNKS.md`.
  - **1 chunk-level retrieval miss** (STR-010): verbatim-answer chunks exist in retrieved papers but rank outside top-5. Wang chunk 1 is in top-20; Thapa chunk 4 isn't even in top-20.
  - **2 NOT retrieval problems** (INJ-009, CVD-003): the answer chunks ARE in current top-5. Judge missed them, or expected fact contradicts source paper (CVD-003 fact 2 contradicts Lee 2024's actual finding).
  - **1 test-bound** (PROG-003): expected facts not claimed in Paoli 2017.
  - **Realistic ceiling after retrieval improvements: 6 of 9 cases.** 2 need judge fixes, 1 needs test-case rewrite. **New priority to add: per-paper diversification** — it's the single most direct fix for the dominant failure mode.

### 9. Priority A — bump `top_k` from 5 to 8-10
- **Options:** do it / skip
- **Recommendation:** do it. Trivial change; eval directly identifies recall as the weakest metric (4.1).
- **Decision: COMMITTED — bump to ~20 as candidate pool for reranker.** Part of ROADMAP Phase 2 sequence. Bigger bump than originally proposed (20 vs 8-10) because it feeds the reranker rather than being the final answer.

### 10. Priority B — delete noise chunks (references, acknowledgments, funding, supplementary, etc.)
- **Options:** do it / skip
- **Recommendation:** do it after #9. ~16% of chunks are noise. Pairs with the top_k bump — freed slots get filled by real content.
- **Decision: COMMITTED — do it late in Phase 2 after reranking is verified.** Requires inspecting chunks before deleting (Frontiers back-matter bleed risk). Acts as a multiplier on the retrieval improvements above.

### 11. Priority C — cross-encoder reranking with FlashRank
- **Options:** do it / skip / use Cohere Rerank API instead
- **Recommendation:** do it with FlashRank. Highest-ROI single feature on the entire roadmap. ~1 day. Pairs with #9 (retrieve top-20, rerank to top-5). FlashRank over Cohere because it's local, free, and good enough.
- **Decision: COMMITTED — FlashRank.** Single highest-ROI retrieval intervention per the recall failure diagnostic (addresses all three failure modes: single-paper saturation, chunk-level miss, noise crowding). Central to ROADMAP Phase 2. **When starting this work**: load `context/archive/RETRIEVAL-TARGET-CHUNKS.md` — it lists the specific verbatim-answer chunks that successful retrieval should surface into top-k, providing a judge-independent success metric.

### 12. Priority D — abstract-augmented retrieval (inject paper abstracts into context)
- **Options:** do it / defer
- **Recommendation:** defer. Lower expected impact than A/B/C. Revisit after re-evaluating with #9/#10/#11 applied.
- **Decision: DEFERRED — revisit after #9/#10/#11.** If post-improvement eval still shows specific recall weaknesses where abstracts would help, reopen this decision.

### 13. Priority E — judge JSON parse retry (fix STR-007/PROG-008 failure mode)
- **Options:** do it / skip
- **Recommendation:** do it during eval validation work. Trivial — wraps existing parse logic in retry. Removes a recurring noise source from future runs.
- **Decision: COMMITTED — do first in Phase 1.** Eval reruns depend on stable judging, so this is the first step in the sequence.

### 14. Hybrid retrieval (BM25 + vector via Reciprocal Rank Fusion)
- **Options:** do it / defer
- **Recommendation:** defer. Your corpus is research papers, not product IDs or error codes — the failure mode hybrid solves doesn't strongly match your domain. Reranking gives bigger gains for prose. Add hybrid only if post-rerank eval still shows precision problems.
- **Decision: DEFERRED.** Research-paper prose doesn't match the failure mode BM25 addresses (exact-identifier matching). Reranking is the right tool for this domain. Reopen only if post-Phase-2 eval shows specific precision problems that look like vocabulary mismatch.

---

## Documentation outputs

### 15. README "Tools Considered and Rejected" section
- **Options:** do it / skip
- **Recommendation:** do it. Single best tactical recommendation from the meta-discussion. Frame as "selective custom where it matters, frameworks where they fit." List: Ragas (validated against it), Phoenix (chose LangSmith for ecosystem fit), custom state machine (chose LangGraph).
- **Decision: COMMITTED.** Source material in `context/PORTFOLIO-NARRATIVE.md` "Build vs Buy Decision Framework" section — ready to copy/adapt into the README.

### 16. `context/EVAL-INTERVIEW-NOTES.md` — short spoken-delivery interview prep doc
- **Options:** do it / skip
- **Recommendation:** do it after eval validation finishes. 30-60 min of work, pays off every interview.
- **Decision: COMMITTED.** Source material in `PORTFOLIO-NARRATIVE.md` "Narrative Lines for Different Audiences" section already covers the 30s/60s answers — refine into interview prep doc after Phase 1 eval data is in hand.

### 17. Public blog post(s) about the eval work
- **Options:** skip / one post / two posts (custom eval design + cross-model validation)
- **Recommendation:** one post combining both topics. Public writing is one of the higher-ROI job-search activities at your stage. But cap at one — second post is diminishing returns.
- **Decision: COMMITTED — one post.** Topic: custom eval design + cross-model/cross-implementation validation (Run A vs Run B). Write after Phase 1 produces real data to anchor the post.

---

## Sequencing / scope

### 18. Build order for what's left
- **Options:**
  - (a) Eval validation (Run A) → retrieval improvements (sequence below) → re-eval → v2 agentic with LangGraph
  - (b) Skip ahead to v2 agentic, come back to retrieval improvements later
  - (c) Finish Phase 3 polish first (supersets, set type UI, exercise notes, video URLs)
- **Recommendation:** (a). Eval first so retrieval improvements are measurable. Retrieval improvements before v2 because they raise the floor v2 builds on. Phase 3 polish is lowest priority — those features don't show up in interview demos of the AI chatbot.
- **Decision: COMMITTED — option (a).** Three phases: eval baseline & cross-validation → retrieval improvements (diversification + top_k bump + reranking + re-eval + noise cleanup) → v2 agentic with LangGraph. Full ordered sequence below.

**Full ordered build sequence** (post-diagnostic; informed by `RECALL-FAILURE-DIAGNOSTIC.md`, `RETRIEVAL-TARGET-CHUNKS.md`, and the eval validation commitments in decisions #1, #2):

The cleanest experimental design holds one axis constant while measuring the other. Sequence: establish eval baseline + cross-validation FIRST (so judge stability is known), THEN apply retrieval improvements (so retrieval changes have clean measurements against that baseline).

**Phase 1 — Eval baseline & cross-validation (~3-4 days, ~$2-4):**

1. ✅ **DONE (2026-05-30) — Priority E, Judge JSON parse retry** (decision #13). `judge.py` now regenerates on a new `JudgeParseError` with escalating temperature `[0.0, 0.3, 0.6]` before falling back to score 3; robust parser strips markdown fences. Unit-verified; 0 spurious retries across the 100-case run.
2. ✅ **DONE (2026-05-30) — Fresh baseline rerun** → `results/run0_baseline_clean.json`, **4.58/5** (supersedes `post_expansion.json`). Includes a 2nd test-cleanup round: a full recall≤3 sweep found 6 more test-bound cases (BH-001, STR-013, NUT-004, BH-002, BH-007, PROG-006), edited + re-scored, recall 4.1→4.16. Full classification in `archive/RECALL-FAILURE-DIAGNOSTIC.md`; target-chunk baseline `0/35` in `results/target_chunks_baseline.json`.
3. ✅ **DONE (2026-05-31) — Anthropic provider build.** `src/core/anthropic_provider.py` (minimal Messages API `generate()`, shared httpx client, status code surfaced in `RuntimeError`); `model` param added to `llm_provider.generate()` (silent-ignore bug fixed); prefix dispatch in `judge.py` `_generate_with_retry` (`claude-*` → Anthropic, else Gemini); retry check widened to **429 + any 5xx** (catches Anthropic 529-overloaded) via new `_is_retryable_error()`; `ANTHROPIC_API_KEY` added to config (lazy); Anthropic client closed in `app.py` lifespan. Verified: classifier + dispatch routing unit-checked, clean failure without key, default Gemini path unchanged, live 1-case + 3-case smoke tests.
4. ✅ **DONE (2026-05-31) — Run A (custom + Claude Haiku 4.5).** `results/run_a_custom_claude.json`. 100/100, 0 parse failures, 0 fallbacks, ~$0.80. **Overall 4.58→4.74 (Δ+0.16); 96.3% within ±1.** Claude lenient on retrieval metrics (Rec +0.47, Rel +0.30, Pre +0.18), lockstep on answer-quality (Ans −0.08, Fai −0.11). Custom judge validated. **Caveat: keep Gemini as the fixed judge for Phase 2 retrieval before/after** (the +0.47 recall gap is judge strictness, not retrieval). Full detail in `CONTEXT.md`.
5. ⏳ **NEXT — Ragas integration** (~1-1.5 days). New module + CLI script parallel to existing eval. See `EVAL-PLAN.md` §3.
6. **Run B — Ragas + Gemini** (decision #2). Cross-implementation validation. ~1.5 hours unattended, $0.
7. **Analysis writeup** comparing fresh baseline / Run A / Run B (~0.5 day). Per-metric correlation, agreement rate, disagreement cases.

**Phase 2 — Retrieval improvements (~3-4 days):**

8. **Per-paper diversification** (new — not in original FUTURE-PLANS). Modify `match_chunks` RPC or add a post-filter capping chunks-per-paper at ~2 in the candidate pool. Cheap; quick win for the 5 saturation cases.
9. **Priority A — top_k bump 5 → ~20 candidate pool** (decision #9). Config change. Becomes the input to reranker.
10. **Priority C — Cross-encoder reranking with FlashRank** (decision #11). ~1 day. Sits on top of #8 and #9; retrieves 20 candidates, reranks to top-5. The big lever.
11. **Re-run eval** (custom judge, Gemini) on the improved RAG and verify against `archive/RETRIEVAL-TARGET-CHUNKS.md` primary targets. Independent success metric: `(primary chunks in top-5) / (total primary chunks)`, automated by `apps/api/scripts/measure_target_chunks.py` — diff each run against the pre-Phase-2 baseline `results/target_chunks_baseline.json` (**`0/35` in top-5**; core 6 = 0/15, extended 5 = 0/20). Classification of all 20 recall≤3 cases (retrieval-fixable / judge-bound / test-bound) is in `archive/RECALL-FAILURE-DIAGNOSTIC.md`.
12. **Priority B — Noise chunk cleanup** (decision #10). Done late because it requires inspecting chunks before deleting (Frontiers back-matter bleed risk).
13. **Post-improvement cross-checks**: optional Run A2 (custom + Claude) and Run B2 (Ragas + Gemini) on the improved RAG. Confirms improvements aren't a judge artifact. Skippable if Phase 1 already showed high cross-judge agreement.

**Phase 3 — v2 agentic with LangGraph (later)**: builds on the improved retrieval. Out of scope for this sub-sequence.

**Skipped/deferred items:**
- Priority D (abstract-augmented retrieval, decision #12): defer; diagnostic shows verified answer chunks are substantive content chunks, not abstract-dependent.
- PROG-003 test rewrite (open): independent of retrieval work; can be done any time.
- Run C (Ragas + Claude, decision #3): optional; skip unless Phase 1 analysis surfaces confusing Run A/B disagreement.

**Total estimated time before v2 work**: ~6-8 days active work + ~$3-6 API cost (Haiku 4.5 judge runs + optional cross-checks).

### 19. Phase 4 (progress tracking) vs Phase 5 (Agentic RAG v2) priority
- **Options:** Phase 4 first / Phase 5 first / skip Phase 4 entirely for now
- **Recommendation:** Phase 5 (v2 RAG) first. Phase 4 is product polish; v2 RAG is the actual portfolio differentiator. Phase 4 can wait or be done lightly.
- **Decision: COMMITTED — Agentic RAG v2 (Phase 5) first.** Aligns with #18 build order. Phase 4 progress tracking deferred until v2 lands; some Phase 4 functionality (workout data analysis) gets covered for free by v2's workout data branch.

### 20. Time budget before pivoting to job-search activities (networking, applications, interview reps)
- **Options:** unlimited until "done" / cap at ~4-6 more weekends / cap tighter (~2-3 weekends, ship MVP and pivot)
- **Recommendation:** cap at ~4-6 more weekends. Run A + retrieval improvements (#9/#10/#11/#13) + LangSmith + README writeup + one blog post fits in that. After that, the marginal portfolio polish is worth less than the marginal application sent.
- **Decision: COMMITTED — cap at ~4-6 more weekends.** Scope: Phase 1 (eval baseline + Run A + Ragas Run B + analysis) + Phase 2 (retrieval improvements + re-eval) + Phase 3 MVP (agentic v2 with router/judge/retry, even if not all 10 design questions are fully resolved) + public artifacts (README "Tools Considered", interview notes, one blog post). After that, marginal portfolio polish is worth less than the marginal application sent. Maintain only critical fixes during job search.

---

## How to use this doc

1. Walk through pending decisions (`**Decision:**` blank lines). Fill in each.
2. Once decided, this doc supersedes the relevant sections of `FUTURE-PLANS.md` and the recommendation parts of `EVAL-PLAN.md`.
3. Revisit decisions only when new information arrives — not when AI advice shifts.

The **full ordered build sequence is in decision #18** (Phase 1: eval baseline + cross-validation; Phase 2: retrieval improvements; Phase 3: v2 LangGraph agentic). That section is the authoritative roadmap once decisions land.
