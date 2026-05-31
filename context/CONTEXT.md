# Flame Fitness — Implementation Context

This file is intentionally short. It holds **current-state pointers** only. Implementation walkthroughs, phase-by-phase gotchas, and the detailed eval results table have been moved to `context/archive/IMPLEMENTATION-HISTORY.md` — load that file only when needed for specific subsystem reference.

---

## Current State Snapshot

- **RAG v1**: complete. 195 papers, ~8284 chunks. **Current reference baseline: `apps/api/results/run0_baseline_clean.json` — 4.58/5** (100 cases, 0 failed, scored 2026-05-30 against the cleaned dataset with the parse-retry judge; includes a 2nd test-cleanup round — see below). This **supersedes `post_expansion.json`** (4.57/5, 2026-03-19, pre-cleanup). Per-metric: Relevancy 4.6 · Recall 4.16 (weakest) · Precision 4.3 · Answer Relevancy 5.0 · Faithfulness 4.8. All currently-ingested papers are CC-BY; license policy (updated 2026-05-12) now allows opportunistic non-CC-BY ingestion when a paper is high-value AND no CC-BY equivalent exists, with the exact CC variant recorded on the `papers.license` column. Commercial-mode queries filter via `WHERE license IN ('CC0', 'CC-BY', 'CC-BY-SA', 'CC-BY-ND')`.
- **Test dataset**: cleaned in two rounds. Round 1 (2026-05-10): 5 cases edited (`.bak.2026-05-10`). Round 2 (2026-05-30): a full recall≤3 sweep found **6 more test-bound cases** — BH-001, STR-013, NUT-004, BH-002, BH-007, PROG-006 edited to match their sources (`.bak.2026-05-30`); all 6 recall scores recovered (3→4/5) with zero retrieval changes, confirming test-authoring artifacts. PROG-003 still pending. Full classification of all 20 recall≤3 cases in `context/archive/RECALL-FAILURE-DIAGNOSTIC.md`. **Fresh baseline confirmed the cleanup worked as designed**: the 2 contradiction-fix cases improved (NUT-016, CVD-003: Recall 2→4), while the 3 genuinely retrieval-bound cases held (BC-010, STR-010 Rec=2; GEN-004 Rec 2→1) — isolating real retrieval gaps from test noise. 34 cases now have ≥1 retrieval metric ≤3 (overwhelmingly recall/precision, not relevancy) — the Phase 2 target surface.
- **Workout logging**: complete (Phase 3). 9 tables, 28 API endpoints, full frontend (active workout modal, history, routines, exercise library).
- **Exercise library**: complete. 386 EMG-backed exercises, 36 muscle groups (13 categories), 2,890 activation mappings.
- **Recall failure diagnostic**: done. 6 of 9 failures are retrieval-bound (5 single-paper saturation + 1 chunk-level miss). See `context/archive/RECALL-FAILURE-DIAGNOSTIC.md` for the detailed forensic analysis and `context/archive/RETRIEVAL-TARGET-CHUNKS.md` for verified chunk IDs to test retrieval improvements against.

---

## Where Things Live

- **What to build next + decisions**: `context/ROADMAP.md` (authoritative; build order in decision #18)
- **Narrative for interviews/README**: `context/PORTFOLIO-NARRATIVE.md`
- **Tech stack + folder structure + patterns**: `context/CLAUDE.md`
- **Eval validation experiment plan**: `context/EVAL-PLAN.md`
- **v2 agentic design + deferred ideas**: `context/FUTURE-PLANS.md`
- **Implementation walkthroughs + historical detail**: `context/archive/IMPLEMENTATION-HISTORY.md` (load when debugging or extending a specific subsystem)
- **Recall failure forensics + chunk-level test targets**: `context/archive/RECALL-FAILURE-DIAGNOSTIC.md` (authoritative classification of all 20 recall≤3 cases: ~11 retrieval-fixable, 3 judge-bound, 7 test-bound) and `context/archive/RETRIEVAL-TARGET-CHUNKS.md` (the verified primary chunks each retrieval-fixable case should surface). **Load both when starting Phase 2 retrieval work.**
  - **Phase 2 success metric (judge-independent)**: run `cd apps/api && python -m scripts.measure_target_chunks --output results/target_chunks_<label>.json` before/after each retrieval change and diff against the **baseline `results/target_chunks_baseline.json` = `0/35` primary chunks in top-5** (core 6: 0/15, extended 5: 0/20). If this ratio rises but eval recall doesn't, the bottleneck has moved to the judge.
  - Test-set hygiene: two cleanup rounds done (5 cases 2026-05-10, 6 cases 2026-05-30) removing facts that contradicted/weren't grounded in source papers; PROG-003 still pending.

---

## Key Resolved Decisions (For Quick Lookup)

- **Embeddings**: Voyage AI `voyage-4-large` (1024 dims, ~8% better than OpenAI on MTEB, same price, fits pgvector HNSW natively)
- **LLM**: Gemini 2.5 Flash (cheapest, swappable via env var). Paid Tier 1, ~$3/month actual spend.
- **License**: All papers CC-BY from PMC Open Access Subset. Commercial-safe.
- **Eval (committed Phase 1)**: custom LLM-as-judge as primary + Ragas cross-validation + Claude Haiku 4.5 as alternate judge. Full plan in `EVAL-PLAN.md`.
- **Retrieval improvements (committed Phase 2)**: per-paper diversification → top_k=20 → FlashRank reranking → noise cleanup. See `ROADMAP.md` decisions #9-11.
- **Agentic v2 (committed Phase 3)**: LangGraph router with literature/workout/exercise-info branches + judge node. Design open questions in `FUTURE-PLANS.md`.
- **Observability**: custom `rag_traces` table in Supabase + LangSmith UI on top. Both kept.

For deeper context on any of these, see `archive/IMPLEMENTATION-HISTORY.md`.
