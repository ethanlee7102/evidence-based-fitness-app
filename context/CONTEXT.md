# Flame Fitness — Implementation Context

## Resolved Decisions

### Embedding: Voyage AI `voyage-4-large` (1024 dims)
- ~69.9% MTEB vs OpenAI's 64.6% (~8% better retrieval), same price ($0.12/1M tokens)
- 1024 dims fits pgvector HNSW natively. Free tier: 200M tokens.
- `input_type: "document"` for ingestion, `"query"` for retrieval. Batch limit ~200 chunks/call (120K token limit).

### LLM: Gemini 2.5 Flash
- Cheapest option, swappable via env var + `llm_provider.py` wrapper.
- Migrated from 2.0-flash → 2.5-flash (Google deprecated 2.0-flash free tier, shutdown June 2026).
- Paid Tier 1: $35/month spend cap, ~$3/month actual spend.
- Auth: API key as query param (not Bearer). System prompt via `system_instruction` field. Streaming via `?alt=sse`.
- **Gemini 2.5 Flash thinking parts**: `generate()` must filter out `thought: true` parts, concatenate only non-thought text. Same in `generate_stream()`.

### License & Copyright
- All papers CC-BY from PMC Open Access Subset. License tracked per paper in DB.
- Copyright-safe RAG: LLM synthesizes in own words (never displays verbatim chunks), cites [Author, Year] with DOI/URL.
- For commercial use: filter corpus to `WHERE license IN ('CC0', 'CC-BY', 'CC-BY-SA', 'CC-BY-ND')`.

---

## Completed Phases (1-8)

### Phase 1: Database Schema ✅
- Migration `005_rag_tables.sql`: pgvector extension, `papers`, `chunks` (HNSW index), `chat_sessions`, `chat_messages`, `rag_traces` tables, `match_chunks` RPC, RLS policies.
- Migration `006`: `license` column on papers. Migration `007`: `match_chunks` updated with `token_count`. Migration `008`: trace columns (`rewritten_query`, `chunk_count`, `model`, `grounded`).
- **Gotcha**: `CREATE OR REPLACE FUNCTION` can't change `RETURNS TABLE` columns — must DROP first.

### Phase 2: Backend Infrastructure ✅
- Config (`config.py`): 11 RAG env vars, lazy validation (keys checked when providers called, not at boot).
- Embedding provider (`embedding_provider.py`): `embed_texts()` + `embed_query()`, shared httpx AsyncClient.
- LLM provider (`llm_provider.py`): `generate()` + `generate_stream()`, multi-turn `messages` param, role alternation warning. Shared httpx AsyncClient, cleaned up via FastAPI `lifespan` hook.

### Phase 3: Ingestion Pipeline ✅
- `ingestion.py`: IBM Docling + pymupdf hybrid. Docling handles layout/reading order/headers/tables. pymupdf provides font size/bold via bounding box spatial matching for header hierarchy.
- Header hierarchy (layered): 1a) font size grouping with title-level skip (while loop), 1b) bold tiebreaker, 1c) ALL_CAPS tiebreaker, 2) text pattern fallback. Abstract force-promotion + body text scan.
- Section-aware chunking (RecursiveCharacterTextSplitter within sections, 3200 chars ~800 tokens, 200 char overlap).
- SHA-256 content hash dedup. Retry on `embed_texts()`: 3 attempts, exponential backoff on 429/500/503.
- **Title-level font group skip fix**: `while` loop skips chains of ≤2-member font groups (handles JISSN page labels, paper titles at large font sizes).

### Phase 4: Retrieval Pipeline ✅
- `retrieval.py`: `retrieve_chunks(query, top_k, category, similarity_threshold)` → `RetrievalResult` dataclass.
- Embeds query via Voyage, calls `match_chunks` RPC (pgvector cosine similarity). Logs query, chunk count, similarity range, timing.
- `RetrievalResult` is a dataclass (not Pydantic) — internal data carrier, never serialized over wire.

### Phase 5: RAG Generation Pipeline ✅
- `rag_pipeline.py`: `rag_query()` (non-streaming for eval) + `rag_query_stream()` (streaming for chat UI).
- Conditional query rewriting on follow-ups (extra LLM call, temp=0.0, 256 tokens).
- Citations as `[Author, Year, p. X]` via source block labels. Temperature 0.3. Max tokens 8192.
- Ungrounded handling: `grounded=False` + disclaimer when no relevant chunks or answer contains "I don't have enough research".

### Phase 6: Chat API + TraceLogger ✅
- `chat.py`: 5 endpoints — `POST /chat/message` (SSE streaming), GET/DELETE sessions, GET messages.
- SSE event flow: `session` (new only) → `citations` (always) → `data*` (text chunks) → `done`.
- Auto-title: LLM generates 3-8 word title, fire-and-forget, strip quotes, truncate 60 chars.
- `trace_logger.py`: Fire-and-forget via `asyncio.create_task()`. Full chunk text snapshots. Never blocks, never raises.
- `chat_service.py`: Session CRUD, message persistence, `get_recent_messages()` (last 10) for RAG history.
- **Gotchas**: DB column is `llm_response` not `answer`. Supabase REST API doesn't accept `"now()"` — use ISO timestamp. Post-stream work must be inside generator (after yield), not after `return StreamingResponse`.

### Phase 7: Frontend Chat UI ✅
- 12 new files in `features/chat/`: types, service (REST + SSE), hook (`useChat`), 7 components.
- SSE client: raw `fetch` + `ReadableStream` (EventSource is GET-only). Buffer accumulation with `\n\n` split.
- Inline citation linking: `processCitations()` regex → `#cite::key` hash links (react-markdown strips unknown protocols). Scroll to card with highlight.
- **Gotchas**: `TextDecoder` `{stream:true}` on `.decode()` not constructor. Sidebar renders `null` when closed (no fixed positioning). `-m-6` counteracts DashboardLayout `p-6`.

### Phase 8: Automated Evaluation Pipeline ✅
- Custom LLM-as-judge: 5 metrics (contextual relevancy/recall/precision, answer relevancy, faithfulness).
- Two modes: separate (5 calls/case) vs combined (1 call/case, `--combined` flag).
- `src/core/eval/`: judge.py, runner.py, report.py. CLI: `scripts/evaluate_rag.py`. Pytest: `tests/eval/`.
- Rate limiting: 7s between cases, 5s between judge calls, retry on 429/503.
- **Gemini 2.5 Flash judge gotcha**: `max_tokens=1024` was shared between thinking and output — model used ~980 thinking tokens, leaving ~40 for response. Fixed to `max_tokens=8192`.

---

## Eval Results

Baseline (2026-03-15): **4.55/5**, 29 cases, 24 papers, 909 chunks.

### Post-Expansion (2026-03-19): **4.57/5**, 100 cases, 195 papers, ~8284 chunks

| Metric | Mean | vs Baseline |
|--------|------|-------------|
| Answer Relevancy | 5.0 | = |
| Faithfulness | 4.9 | +0.1 |
| Contextual Relevancy | 4.6 | +0.1 |
| Contextual Precision | 4.3 | = |
| Contextual Recall | 4.1 | = |

| Rank | Category (n) | Overall | Rel | Rec | Pre | Ans | Fai |
|------|-------------|---------|-----|-----|-----|-----|-----|
| 1 | Hypertrophy (15) | 4.76 | 4.8 | 4.4 | 4.7 | 5.0 | 4.9 |
| 2 | Cardiovascular (7) | 4.66 | 5.0 | 3.9 | 4.6 | 5.0 | 4.9 |
| 3 | Recovery (6) | 4.63 | 4.8 | 4.2 | 4.3 | 5.0 | 4.8 |
| 4 | Nutrition (17) | 4.62 | 4.5 | 4.4 | 4.2 | 5.0 | 5.0 |
| 5 | Injury (12) | 4.47 | 4.6 | 3.8 | 4.1 | 5.0 | 4.9 |
| 6 | Mobility (7) | 4.46 | 4.1 | 4.3 | 3.9 | 5.0 | 5.0 |
| 7 | General (10) | 4.44 | 4.4 | 4.0 | 4.1 | 5.0 | 4.7 |
| 8 | Strength (10) | 4.42 | 4.6 | 3.6 | 4.4 | 4.8 | 4.7 |
| 9 | Body Comp (7) | 4.37 | 4.4 | 3.9 | 3.6 | 5.0 | 5.0 |
| 10 | Programming (7) | 4.31 | 4.3 | 3.7 | 4.1 | 4.7 | 4.7 |

18 perfect scores. Worst: GEN-004 (3.6), BC-010/MOB-003/NUT-014/INJ-009 (3.8).
STR-007/PROG-008 were judge JSON parse failures (rerun: 4.8/4.2). OOS: 2/2 correctly ungrounded.
Results saved: `apps/api/results/post_expansion.json`

---

## Phase 3: Workout Logging ✅

### Database (Migrations 011, 013)
- 6 tables: `muscle_groups` (36 rows), `exercises` (386), `exercise_muscles` (2,890 mappings), `workouts`, `workout_exercises`, `workout_sets`
- Full RLS with nested EXISTS checks for child/grandchild tables. Partial unique indexes on `lower(name)`.
- Migration 013: added Hip Adductors, Neck, Rotator Cuff muscle groups.

### Seed Data
- `muscle_groups.json`, `exercises.json`, `exercise_muscles.json` — all EMG-backed, seeded via `scripts/seed_exercises.py`
- Research files: `apps/api/data/research/` (8 files by body region)
- `data/EXERCISE-LIST-400.md` — canonical exercise list (386 exercises)
- `scripts/exercise_views.sql` — 10 SQL queries for inspecting exercise data in Supabase

### Backend
- `src/service/workout_service.py` — WorkoutService, 20 endpoints on `/workouts`
- `src/schema/workout.py` — 16 Pydantic models
- `src/api/workouts.py` — `_format_exercise()` and `_format_workout_response()` helpers flatten nested Supabase joins

### Frontend (25 files in `features/workouts/`)
Key components: `ActiveWorkoutModal`, `ExerciseCard`, `SetRow`, `ExerciseSearchModal`, `WorkoutSummaryModal`, `WorkoutDetailModal`, `RestTimerBar`, `WorkoutTimer`

### Key Design Decisions
- **Units**: Store in kg, convert at display boundary only via `useProfile().unitsPreference`
- **Set persistence**: Checkmark = immediate sync. Weight/reps/RPE = 500ms debounce.
- **PREV column**: Clickable — tap to auto-populate weight+reps from last session.
- **Timer pause/resume**: Elapsed saved to localStorage keyed by workout ID. Client sends accurate `duration_seconds` on finish.
- **Rest timer**: Per-exercise (`workout_exercises.rest_timer_seconds`). Auto-starts floating `RestTimerBar` on set completion.
- **Skeleton loading**: `ADD_EXERCISE_PENDING` action shows pulsing skeleton immediately while API calls complete.
- **Modal stacking**: z-50 (workout) < z-55 (rest timer) < z-60 (exercise search) < z-65 (create exercise) < z-70 (summary)
- **Resume**: Per-card Resume button in history list. Multiple in-progress workouts supported.

### Bugs Fixed
1. **Seed upsert failure** — `ON CONFLICT "name"` doesn't work with partial unique indexes on `lower(name)`. Switched to check-then-insert.
2. **`maybe_single()` crash** — Supabase returns `None` on 0 rows, causing `AttributeError`. Replaced all with `_single()` helper using `limit(1)`.
3. **React Strict Mode double workout** — `initRef` guard on `useActiveWorkout` mount.
4. **Exercise search truncated at E** — Default `limit=50`; increased to 400.

### Workout History & Filters (2026-03-26)
- WorkoutsScreen shows top 3 recent workouts with "See All History" link
- Dedicated `/dashboard/workouts/history` route (`WorkoutHistoryScreen`) with full paginated list
- Server-side filters (AND-combined): date range (presets + custom), min star rating, exercise
- Backend: `GET /workouts` accepts `date_from`, `date_to`, `min_rating`, `exercise_id` query params
- Exercise filter uses two-step query (workout_exercises lookup → `.in_("id", ids)`)
- `WorkoutFilterBar` component: collapsible panel, reuses `ExerciseSearchModal` for exercise picker
- Filter bar stays mounted during loading (spinner only replaces list area)

### Exercise Library & Stats (2026-03-26)
- Two tile buttons on WorkoutsScreen (Exercise Library + Routines placeholder)
- `/dashboard/workouts/exercises` route — full exercise library with search, filters, recent section (top 5)
- `ExerciseDetailModal` — fullscreen modal with metadata grid, muscles by activation level (color-coded), instructions, stats
- `GET /workouts/exercises/{id}/stats` endpoint — returns recent sets + per-session volume history
- Stats: recent sets table (5 most recent) + volume progression line chart (recharts)
- `useExerciseSearch` hook extracted from `ExerciseSearchModal` — shared by library screen and workout add-exercise modal
- Search results prioritize name-starts-with matches (client-side sort)

### Remaining (Phase 3)
- Exercise video URLs (field exists, data not sourced)
- Superset grouping UI (DB field exists)
- Set type selector UI (warmup/dropset/failure exist in DB)
- Exercise notes during workout (DB field exists)
- Routines/templates (tile placeholder exists, deferred to v2)

---

## Corpus Status: 195 papers, ~8,284 chunks

| Category | Papers | Key topics |
|----------|--------|-----------|
| Nutrition | 40 | Protein/MPS, timing, pre-sleep, caffeine, beta-alanine, supplements, IF/meal frequency, micronutrients |
| Strength | 29 | Progressive overload, autoregulation/RPE, VBT, concurrent training, frequency, neural adaptations, power/plyometrics |
| General | 23 | Specific populations (older adults, sex differences, menstrual cycle, beginners vs advanced), mental health |
| Hypertrophy | 23 | Rest intervals, tempo, proximity-to-failure, ROM, stretch-mediated, eccentrics, metabolic stress, BFR |
| Injury | 22 | Tendinopathy (patellar, Achilles, rotator cuff, lateral elbow), low back pain, bone health |
| Programming | 12 | Splits, exercise selection, volume, supersets, cluster sets, advanced techniques, periodization |
| Recovery | 14 | Deloading, overtraining, CWI, sleep, HRV, sauna, alcohol |
| Body Composition | 13 | Cutting strategies, HIIT vs MICT, progressive restriction, bulking, off-season nutrition |
| Mobility | 11 | Static/dynamic stretching, foam rolling, SMR, warm-up |
| Cardiovascular | 10 | Cardiac remodeling, VO2max, HIIT, isometric/circuit training for hypertension, mortality |

All CC-BY from PMC Open Access Subset. Full paper lists in `papers/manifest.json`.

---

## Exercise Library Overhaul ✅ (2026-03-20)

Replaced MC-Oruc unsourced mappings with EMG-backed research. 33→36 muscle groups (migration 013), 137→386 exercises, 2,890 activation mappings (avg 7.5/exercise). All 36 muscle groups used. Zero unmapped exercises.

Research detail: `apps/api/data/research/` (8 files by body region).
