# Flame Fitness — Implementation Context

This file is intentionally short. It holds **current-state pointers** only. Implementation walkthroughs, phase-by-phase gotchas, and the detailed eval results table have been moved to `context/archive/IMPLEMENTATION-HISTORY.md` — load that file only when needed for specific subsystem reference.

---

## Current State Snapshot

- **RAG v1**: complete. 195 papers, ~8284 chunks, post-expansion eval **4.57/5** (pre-test-cleanup, scored 2026-03-19).
- **Test dataset**: cleaned 2026-05-10. 5 cases edited to remove test-authoring issues. Backup at `apps/api/tests/eval/test_dataset.json.bak.2026-05-10`. A fresh baseline rerun is in ROADMAP Phase 1.
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
- **Recall failure forensics + chunk-level test targets**: `context/archive/RECALL-FAILURE-DIAGNOSTIC.md` and `context/archive/RETRIEVAL-TARGET-CHUNKS.md` (load when starting Phase 2 retrieval work)

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
