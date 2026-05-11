# Future Plans

This file holds **forward-looking design notes** — primarily the v2 agentic architecture and small lists of deferred ideas. Anything already committed lives in `context/ROADMAP.md`. Anything already done lives in `context/MEMORY.md` (and `context/CONTEXT.md` for implementation details if needed).

---

## RAG v2: Agentic RAG with Router (LangGraph)

The headline portfolio feature for Phase 3. Status: design pending — see open questions section below. Implementation kicks off after Phase 2 retrieval improvements land.

### Architecture
```
User question
      |
      v
   Router (LLM classifies intent — possibly multi-label)
      |
      +-- "literature question"    --> v1 RAG pipeline (research papers, vector search)
      |
      +-- "workout data question"  --> SQL queries against user's logged data
      |                                (workouts, workout_exercises, workout_sets, routines)
      |                                Per-user, RLS-enforced via JWT in graph state
      |
      +-- "exercise info question" --> Structured DB lookup (exercises + exercise_muscles)
      |                                Already populated from Phase 3 — 386 exercises,
      |                                2,890 EMG-backed activation mappings, 36 muscle groups
      |
      +-- combinations             --> Run multiple branches in parallel, combine response
                                       e.g. "Research says 14 sets/week [Lit].
                                       You're doing 18 [Workout]. Consider deload."
      |
      v
   Judge node (verifies answer)
      |
      +-- pass --> return
      +-- fail --> retry (rewrite query / swap branch / broaden) up to N retries
```

### Three Retrieval Methods (Why the Router is Justified)

- **Literature** = unstructured text → vector search (v1 RAG, already built)
- **Workout data** = structured numbers → SQL queries against user's logged data
- **Exercise info** = structured knowledge → direct DB joins (no embedding)

Each is a fundamentally different data type and access pattern. A single retrieval path can't serve all three; that's the justification for the router as architecture rather than a workaround.

### Branch Details

**Branch 1 — Literature (v1 RAG, no changes needed)**
- Source: 195 papers, ~8284 chunks
- Access: vector search → top-k chunks → cited answer
- Example queries: "What rep range is best for hypertrophy?" / "Is creatine safe during a cut?" / "How does sleep affect recovery?"

**Branch 2 — Workout data (user's logged data, per-user RLS)**
- Source: `workouts`, `workout_exercises`, `workout_sets`, `routines` tables
- Access: SQL queries (template or LLM-generated — open design decision)
- Per-user, requires JWT threaded through graph state and into Supabase client with RLS
- Example queries: "What was my best bench press last month?" / "How many sets per muscle group am I doing per week?" / "Am I getting stronger on squats?"

**Branch 3 — Exercise info (static reference DB, global not per-user)**
- Source: `exercises` (386 rows), `exercise_muscles` (2,890 activation mappings), `muscle_groups` (36 rows) — already exist from Phase 3
- Access: simple joins, no embedding, no per-user filtering
- Example queries: "What muscles does the Romanian deadlift work?" / "Show me exercises that target the rotator cuff" / "What's a good substitute for incline bench?"

**Combination queries (the most interesting cases for demos):**
- "I'm doing 14 sets of chest per week — is that enough for hypertrophy?" → workout data (count user's sets) + literature (research on volume)
- "I keep doing flat bench but my upper chest isn't growing — what should I add?" → exercise info + workout data + literature
- "How does my training compare to what the research recommends?" → workout data + literature

### Open Design Questions (Most Consequential First)

When v2 work begins, discuss **#3 and #2 together first** — they interlock. Template-SQL → loose router OK; LLM-SQL → router needs high confidence.

1. **State shape** — what does the LangGraph state object hold? (query, intent classification, branch results, retrieval history, judge verdict, retry count, conversation history, user JWT for RLS, ...)
2. **Router node design** — single LLM call classifying into N intents? Multi-label (some queries fire multiple branches)? Confidence threshold for ambiguous → fire-all?
3. **Workout SQL approach** — LLM-generated SQL (flexible but a real failure surface on user data) OR fixed query templates (safe but limited)? Hybrid? Interlocks with router confidence.
4. **Judge node mechanics** — what does it grade? (answer relevance? faithfulness to retrieved data? completeness?) Single yes/no, or per-metric scoring? When does it trigger retry vs. give up?
5. **Retry strategy** — rewrite query / swap branch / broaden retrieval / all three? Max retry count? What changes between attempts?
6. **Streaming behavior** — v1 streams tokens via SSE. LangGraph streams graph state updates, not LLM tokens. Preserve typing-effect UX: hold tokens until final node, or stream from final LLM call inside the last node.
7. **Integration boundary** — v2 as a new endpoint (`/chat/agent/message`) or replacing `/chat/message`? Existing `chat_sessions` / `chat_messages` schema work as-is, or need extensions?
8. **Combination response synthesis** — when router fires multiple branches, how do you stitch? Single final LLM call with all branch outputs as context, or templated combination?
9. **Eval for agentic flow** — current eval is "question → expected facts" with 5 metrics. Agentic systems need additional dimensions: routing accuracy, branch coverage, retry effectiveness. How to measure without test-case explosion?
10. **Auth/RLS in the agent** — workout data branch is per-user. Thread JWT through graph state into Supabase queries with RLS enforced. Single point of failure if mishandled.

### Prerequisites
- ✅ Workout logging built (Phase 3 complete 2026-03-26)
- ✅ Exercise library + muscle mappings populated (386 exercises, 2,890 mappings)
- ✅ v1 RAG stable (eval 4.57/5)
- ⏳ Sufficient workout data in user accounts to test branch 2 — may need synthetic test users
- ⏳ Retrieval improvements (Phase 2 of ROADMAP) — should land before v2 so v2 builds on improved retrieval

---

## Deferred Ideas (Low Priority, Reopen Only If Specific Trigger)

These are documented future-possibility ideas. Not committed; revisit only if a specific need arises.

### Chat Answer Feedback
User-facing thumbs up/down with optional "why" (predefined tags + free text). Tags: "Incorrect info", "Missing details", "Bad sources", "Not relevant", "Too verbose", "Great answer". DB: `chat_feedback` table — message_id (FK), user_id, rating, tags (JSONB), comment, created_at. Use: identify weak corpus spots from real signal, supplement automated eval.

**Trigger to revisit**: only if the project ships to real users beyond demo/interview. Otherwise low ROI.

### Two-Stage Retrieval
Search abstracts first to identify relevant papers, then search chunks within those papers. Better for broad multi-paper questions. Bigger architectural change than reranking. **Trigger**: only if post-Phase-2 eval shows persistent multi-paper failures that reranking didn't fix.

### Async Supabase in Web Handlers
`supabase-py` is synchronous. DB calls in the SSE handler block briefly. Wrap in `asyncio.to_thread()` for production. **Trigger**: only if observed concurrency issues. Currently not a bottleneck.

### Exercise Video URLs (decision deferred)
No free, open-source, commercially-usable video library exists at scale. Options researched: YouTube links (free, no control) / YMove ($29/mo, 636 exercises, commercial HD) / wger (CC-BY-SA, only 78 videos) / exercemus (YouTube URLs, MIT) / MuscleWiki (7,300 but non-commercial). **Trigger**: only if exercise library becomes a demo focus. Currently not a portfolio-headline feature.

### Volume Tracking per Muscle (deferred — Phase 4 territory)
Aggregate sub-groups by category for display (Upper + Mid + Lower Chest → "Chest" weekly volume). Keep granular 36 groups for mapping accuracy. **Trigger**: only if Phase 4 progress tracking gets built. Phase 4 currently deferred per portfolio framing — the v2 agentic workout-data branch covers most of this functionality conversationally.

### App Features Phases 4-6 (deferred per portfolio framing)
Progress tracking visualizations, training/recovery insights via trend analysis, Flame visualization, streaks, mobile polish. All deferred — see `context/PLAN.md` for the priority rationale and `context/PORTFOLIO-NARRATIVE.md` for why product polish isn't the portfolio differentiator.
