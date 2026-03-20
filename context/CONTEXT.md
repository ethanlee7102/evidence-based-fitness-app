# Flame Fitness — Implementation Context

## Resolved Decisions

### Embedding: Voyage AI `voyage-4-large` (1024 dims)
- ~69.9% MTEB vs OpenAI's 64.6% (~8% better retrieval), same price ($0.12/1M tokens)
- 1024 dims fits pgvector HNSW natively. Free tier: 200M tokens.
- `input_type: "document"` for ingestion, `"query"` for retrieval. Batch limit ~200 chunks/call (120K token limit).

### LLM: Gemini 2.5 Flash
- Cheapest option, swappable via env var + `llm_provider.py` wrapper.
- Migrated from 2.0-flash → 2.5-flash (Google deprecated 2.0-flash free tier, shutdown June 2026).
- Paid Tier 1: $35/month spend cap, ~$3/month actual spend. No RPM/RPD rate limiting concerns.
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
- Dependencies: docling, pymupdf, langchain-text-splitters.

### Phase 3: Ingestion Pipeline ✅
- `ingestion.py`: IBM Docling + pymupdf hybrid. Docling handles layout/reading order/headers/tables. pymupdf provides font size/bold via bounding box spatial matching for header hierarchy.
- Header hierarchy (layered): 1a) font size grouping with title-level skip (while loop), 1b) bold tiebreaker, 1c) ALL_CAPS tiebreaker, 2) text pattern fallback. Abstract force-promotion + body text scan.
- Section-aware chunking (RecursiveCharacterTextSplitter within sections, 3200 chars ~800 tokens, 200 char overlap).
- SHA-256 content hash dedup. Retry on `embed_texts()`: 3 attempts, exponential backoff on 429/500/503.
- CLI: `scripts/ingest_paper.py` (single), `scripts/ingest_batch.py` (manifest), `scripts/reingest_all.py` (full re-ingest).
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
- Future improvement ideas (abstract-augmented retrieval, two-stage retrieval, re-ranking) moved to `FUTURE-PLANS.md`.

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
- `CitationCard`: grouped by paper, `cleanSection()` strips numbers/dedupes. `normalizeCiteKey()` for matching.
- **Gotchas**: `TextDecoder` `{stream:true}` on `.decode()` not constructor. Sidebar renders `null` when closed (no fixed positioning). `-m-6` counteracts DashboardLayout `p-6`.

### Phase 8: Automated Evaluation Pipeline ✅
- Custom LLM-as-judge: 5 metrics (contextual relevancy/recall/precision, answer relevancy, faithfulness).
- Two modes: separate (5 calls/case) vs combined (1 call/case, `--combined` flag).
- `src/core/eval/`: judge.py, runner.py, report.py. CLI: `scripts/evaluate_rag.py`. Pytest: `tests/eval/`.
- Rate limiting: 7s between cases, 5s between judge calls, retry on 429/503.
- **Gemini 2.5 Flash judge gotcha**: `max_tokens=1024` was shared between thinking and output — model used ~980 thinking tokens, leaving ~40 for response. Fixed to `max_tokens=8192`.

---

## Baseline Eval Results (2026-03-15)

### Scores (24 papers, 909 chunks, 29 test cases)

Overall: **4.55/5**

| Metric | Mean | Std |
|--------|------|-----|
| Answer Relevancy | 5.0 | 0.0 |
| Faithfulness | 4.8 | 0.5 |
| Contextual Relevancy | 4.5 | 0.7 |
| Contextual Precision | 4.3 | 1.0 |
| Contextual Recall | 4.1 | 0.9 |

By category: Hypertrophy weakest (Recall=2.5, only 3 papers). Nutrition strongest (18 papers).

Worst performers: HYP-003 (3.6), HYP-001 (4.0), NUT-013 (4.0).

Results saved: `apps/api/results/baseline.json`

---

## Post-Expansion Eval Results (2026-03-19)

### Scores (195 papers, ~8284 chunks, 100 test cases)

Overall: **4.57/5**

| Metric | Mean | Std | vs Baseline |
|--------|------|-----|-------------|
| Answer Relevancy | 5.0 | 0.3 | = |
| Faithfulness | 4.9 | 0.4 | +0.1 |
| Contextual Relevancy | 4.6 | 0.7 | +0.1 |
| Contextual Precision | 4.3 | 0.9 | = |
| Contextual Recall | 4.1 | 0.9 | = |

By category (top): hypertrophy (4.76, Rec=4.4 up from 2.5), cardiovascular (4.66, Rel=5.0), recovery (4.63), nutrition (4.62, Fai=5.0).
By category (weak): programming (4.31, Pre=3.6), body-composition (4.37, Pre=3.6), strength (4.42, Rec=3.6).

18 perfect scores (5.0/5). Worst performers: GEN-004 (3.6), BC-010/MOB-003/NUT-014/INJ-009 (3.8).
Note: STR-007 and PROG-008 initially scored 3.0 due to judge JSON parse failures; rerun gave 4.8 and 4.2 respectively.
OOS: 2/2 correctly ungrounded.

Results saved: `apps/api/results/post_expansion.json`

### Score Distribution (98 scored cases)
| Metric | Score=5 | Score=4 | Score=3 | Score=2 | Score=1 |
|--------|---------|---------|---------|---------|---------|
| Ctx Relevancy | 66 | 23 | 8 | 1 | 0 |
| Ctx Recall | 35 | 41 | 13 | 9 | 0 |
| Ctx Precision | 50 | 25 | 20 | 3 | 0 |
| Ans Relevancy | 96 | 0 | 2 | 0 | 0 |
| Faithfulness | 88 | 7 | 3 | 0 | 0 |

### Category Rankings
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

### Bottom 10 Cases
| Case | Category | Overall | Weak Metrics |
|------|----------|---------|-------------|
| GEN-004 | general | 3.6 | Rec=2 (sex differences — cross-topic chunks) |
| NUT-014 | nutrition | 3.8 | Pre=2 (poor chunk ranking) |
| BC-010 | body-comp | 3.8 | Rec=2 (missing expected facts) |
| MOB-003 | mobility | 3.8 | Rel=3, Rec=3, Pre=3 (weak retrieval) |
| INJ-009 | injury | 3.8 | Rec=2, Pre=2 (relevant chunks ranked low) |
| HYP-013 | hypertrophy | 4.0 | Rel=3, Pre=3 |
| NUT-024 | nutrition | 4.0 | Rec=3, Pre=3 |
| REC-006 | recovery | 4.0 | Pre=3, Fai=4 |
| BH-001 | injury | 4.0 | Rel=2, Rec=3 |
| CVD-001 | cardiovascular | 4.0 | Rec=2 |

---

## Phase 3: Workout Logging ✅ (code complete, in testing)

### Database (Migration 011)
- 6 new tables: `muscle_groups` (33 rows, 11 categories), `exercises` (137 global + user custom), `exercise_muscles` (478 activation mappings), `workouts`, `workout_exercises`, `workout_sets`
- Muscle taxonomy: MC-Oruc 23 zones → expanded to 33 with 4 activation levels (maximum/high/medium/partial)
- Partial unique indexes: global exercises unique by `lower(name)`, user exercises unique per `(created_by, lower(name))`
- Full RLS: muscle_groups/exercises/exercise_muscles public-read for authenticated; workouts/workout_exercises/workout_sets ownership-gated (nested EXISTS checks for child/grandchild tables)

### Seed Data (`apps/api/data/`)
- `muscle_groups.json` — 33 muscle groups across 11 categories (Chest, Back, Shoulders, Biceps, Triceps, Forearms, Quads, Hamstrings, Glutes, Calves, Abs)
- `exercises.json` — 137 exercises sourced from free-exercise-db (public domain), with equipment, movement_pattern, force_type, body_region, laterality, instructions
- `exercise_muscles.json` — 478 activation mappings (MC-Oruc's 82 exercises with full mappings + basic defaults for remaining ~55)
- `scripts/seed_exercises.py` — Idempotent (checks existing by name before insert, not upsert, because partial unique indexes don't support ON CONFLICT)
- `video_url` field exists but is null for all exercises (deferred)

### Backend API (20 endpoints on `/workouts`)
- `src/schema/workout.py` — 16 Pydantic models (MuscleGroupResponse, ExerciseResponse, WorkoutResponse, WorkoutSummaryResponse, SetResponse, PreviousSetData, UpdateWorkoutExerciseRequest, Create/Update requests)
- `src/service/workout_service.py` — WorkoutService class following ChatService pattern. Key: `_single()` helper replaces all `maybe_single()` calls (Supabase returns None/406 on 0 rows with `maybe_single()`, causing crashes).
- `src/api/workouts.py` — 20 FastAPI endpoints with `_format_exercise()` and `_format_workout_response()` helpers to flatten nested Supabase joins into response shape.
- Registered in `src/api/router.py`

**Endpoints:**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/workouts/muscle-groups` | All muscle groups (for filters) |
| GET | `/workouts/exercises` | Search (q, equipment, muscle_category) |
| GET | `/workouts/exercises/recent` | Recently used exercises (deduplicated) |
| GET | `/workouts/exercises/{id}` | Exercise with muscle groups |
| POST | `/workouts/exercises` | Create custom exercise |
| GET | `/workouts/exercises/{id}/previous` | PREV column data |
| POST | `/workouts` | Start new workout |
| GET | `/workouts` | List history (paginated) |
| GET | `/workouts/in-progress` | Current in-progress workout |
| GET | `/workouts/{id}` | Full workout detail |
| POST | `/workouts/{id}/exercises` | Add exercise to workout |
| DELETE | `/workouts/{id}/exercises/{we_id}` | Remove exercise |
| PATCH | `/workouts/{id}/exercises/reorder` | Reorder exercises |
| PATCH | `/workouts/{id}/exercises/{we_id}` | Update exercise (rest timer, notes) |
| POST | `/workouts/{id}/exercises/{we_id}/sets` | Add set |
| PATCH | `/workouts/{id}/sets/{set_id}` | Update set (weight, reps, RPE, checkmark) |
| DELETE | `/workouts/{id}/sets/{set_id}` | Delete set |
| PATCH | `/workouts/{id}/finish` | Finish workout (accepts client duration_seconds) |
| DELETE | `/workouts/{id}` | Delete workout |

### Frontend (25 files)
**Types & Services:**
- `types/index.ts` — 15 TypeScript interfaces (snake_case matching backend wire format). `FinishWorkoutRequest` includes optional `duration_seconds` for pause-aware timing.
- `services/workoutService.ts` — API wrappers for all 20 endpoints including `getRecentExercises()` and `updateWorkoutExercise()`
- `utils/unitConversion.ts` — Reuses `kgToLbs`/`lbsToKg` from onboarding, adds `displayWeight()`, `inputToKg()`, `weightUnit()`, `formatDuration()`, `formatVolume()`

**Hooks:**
- `useWorkoutHistory.ts` — Paginated history (PAGE_SIZE=20), optimistic delete. In-progress workouts appear in the regular list with per-card Resume buttons.
- `useActiveWorkout.ts` — `useReducer` for deeply nested workout→exercises→sets state. Optimistic local updates on every keystroke, 500ms debounced server sync for weight/reps, immediate sync on checkmark. `initRef` guard prevents React Strict Mode double-mount. `ADD_EXERCISE_PENDING` action shows skeleton card immediately while API calls complete. `UPDATE_EXERCISE` action for rest timer config.

**Components (11):**
- `WorkoutsScreen.tsx` — History list, Start Workout button, empty state. Resume is per-card (no separate banner). Renders `WorkoutDetailModal` for completed workout viewing.
- `ActiveWorkoutModal.tsx` — Full-screen `fixed inset-0 z-50` overlay with elapsed timer (pause-aware via localStorage), exercise list with skeleton loading, rest timer bar, "+ Add Exercise" button, Finish button. Saves elapsed to localStorage on close, restores on resume, sends accurate `duration_seconds` on finish.
- `ExerciseCard.tsx` — Collapsible card with set table (SET | PREV | weight | reps | RPE | checkmark), three-dot menu (Move Up/Down, Remove Exercise), clock icon with rest timer presets (30s, 1:00, 1:30, 2:00, 3:00, Off), completed set counter
- `SetRow.tsx` — Weight/reps/RPE inputs with unit conversion. Clickable PREV column (tap to auto-populate weight+reps). Checkmark button (only active when weight+reps filled, green when completed), per-set delete via dot menu.
- `ExerciseSearchModal.tsx` — `z-[60]` (above workout modal). Debounced search (300ms), filter by muscle category + equipment, "Recent" exercises section (fetched on mount, hidden when typing), "Create Custom Exercise" option
- `WorkoutSummaryModal.tsx` — `z-[70]`. Post-finish: duration/exercises/sets/volume stats, exercise-by-exercise summary with best set, star rating (1-5), body weight input, notes. Receives accurate `elapsed` prop from parent.
- `CreateExerciseForm.tsx` — `z-[65]`. Name, equipment select, body region toggle, muscle group multi-select (grouped by category, pill buttons)
- `WorkoutHistoryCard.tsx` — Date, complete/in-progress badge, exercise count, duration, volume, set count, star rating. "Resume" button on in-progress cards. Clicking in-progress card resumes; clicking completed card opens detail view.
- `WorkoutHistoryList.tsx` — Scrollable list with Load More button
- `WorkoutDetailModal.tsx` — Full-screen detail view for completed workouts. Stats grid (duration, exercises, sets, volume), rating stars, body weight, notes. Per-exercise cards with sets table showing weight, reps, RPE (conditional), set type badges.
- `RestTimerBar.tsx` — `z-[55]` fixed bottom bar. Countdown timer with MM:SS display, exercise name, skip button. Pulse animation at ≤3s. Auto-starts when set completed on an exercise with rest timer configured.
- `WorkoutTimer.tsx` — Accepts `initialElapsed` for pause/resume and `elapsedRef` to expose current value. Counts up from saved offset rather than wall-clock `started_at`.

### Key Design Decisions
- **Units**: Store everything in kg. Convert at display boundary only via `useProfile().unitsPreference`
- **Set persistence**: Checkmark = immediate server sync. Weight/reps/RPE = 500ms debounce to avoid API hammering
- **PREV column**: Per-exercise query on add (not bulk). Clickable — tap to auto-populate weight+reps from last session.
- **Workout flow**: Full-screen modal (not page navigation). Liftoff-style: timer running, expandable exercise cards, set-by-set logging
- **Resume**: Per-card Resume button on in-progress workouts in history list. Multiple in-progress workouts supported.
- **Timer pause/resume**: Elapsed seconds saved to localStorage keyed by workout ID on close. Restored on resume. Client sends accurate `duration_seconds` on finish (backend falls back to wall-clock if not provided).
- **Rest timer**: Per-exercise rest time stored in `workout_exercises.rest_timer_seconds`. Auto-starts floating countdown bar on set completion. Completing another set replaces running timer.
- **Skeleton loading**: Adding exercise shows pulsing skeleton card immediately (optimistic `ADD_EXERCISE_PENDING` action), replaced when API calls complete.
- **Modal stacking**: z-50 (active workout) < z-55 (rest timer bar) < z-60 (exercise search) < z-65 (create exercise) < z-70 (finish summary)
- **Templates**: Deferred to v2

### Bugs Fixed During Implementation
1. **Seed script upsert failure** — `ON CONFLICT "name"` doesn't work with partial unique indexes on `lower(name)`. Switched to check-then-insert pattern.
2. **`maybe_single()` crash** — Supabase Python client returns `None` (not an object with `.data`) when 0 rows match, causing `AttributeError`. Replaced all 10 occurrences with `_single()` helper that uses `limit(1)` instead.
3. **React Strict Mode double workout** — `useEffect` in `useActiveWorkout` called `startWorkout()` twice in dev. Added `initRef` guard.
4. **Exercise search truncated at letter E** — Default `limit=50` only returned first 50 of 137 alphabetically sorted exercises. Increased to 200.

### What's Left (Phase 3 Polish)
- Exercise video URLs (field exists, data not sourced yet)
- Templates/routines (deferred to v2)
- Superset grouping UI (DB field exists, no frontend yet)
- Set type selector UI (warmup/dropset/failure types exist in DB, no UI to change)
- Exercise notes during workout (DB field exists, no UI)

---

### Analysis & What to Improve

**Generation is near-ceiling.** Answer Relevancy (5.0) and Faithfulness (4.9) are essentially solved — the LLM almost never hallucinates or goes off-topic. The prompt engineering and citation format are working well. No changes needed here.

**Retrieval is the bottleneck.** Contextual Recall (4.1) is the weakest metric with 9 cases scoring 2. This means relevant chunks exist in the corpus but don't make it into the top-5. Three improvements address this directly:

1. **Increase top_k (5 → 8-10)**: Cheapest fix. With 8,284 chunks competing for 5 slots, relevant chunks get squeezed out. Especially for broad multi-paper questions. Negligible cost increase on Paid Tier 1.

2. **Re-ranking (cross-encoder)**: Retrieve top-20 with bi-encoder, re-rank with cross-encoder, keep best 5-8. Fixes the precision problems (body-comp 3.6, mobility 3.9) where "somewhat related" chunks outrank "directly answers the question" chunks. Best combined with top_k increase.

3. **Post-ingestion noise cleanup**: Reference sections, author contributions, funding, etc. waste top-k slots. ~16% of chunks are noise. Deleting them gives relevant chunks a better shot at top-k without any model changes.

**Judge reliability**: 2/100 cases had JSON parse failures (fallback to score 3). Minor but worth hardening — either retry on parse failure or improve the combined judge prompt to produce cleaner JSON.

**Category-specific weaknesses**:
- Strength (Rec=3.6): Broad questions span power, plyometrics, and traditional strength — chunks from one sub-area crowd out others
- Programming (Rec=3.7, Ans=4.7): Overlap with hypertrophy/strength categories causes cross-category chunk competition
- Body Comp (Pre=3.6): Nutrition and body-comp chunks are semantically similar, irrelevant nutrition chunks steal top-k slots

### Bugs Fixed During Baseline
1. **Gemini thinking parts** — filter `thought: true` parts in `generate()` and `generate_stream()`
2. **Judge max_tokens** — increased from 1024 to 8192 (thinking budget issue)
3. **Missing config import** in runner.py
4. **None rag_result crash** in report.py — `r.get("rag_result") or {}`
5. **Save-before-print** in evaluate_rag.py
6. **503 retry** — added to both runner.py and judge.py
7. **OOS grounded detection** — check answer for "I don't have enough research" and override `grounded=False`

---

## Corpus Status

### Current: 195 papers, ~8284 chunks

| Category | Papers | Notes |
|----------|--------|-------|
| Hypertrophy | 23 | 3 original + 10 new (rest intervals, tempo, proximity-to-failure, ROM, stretch, eccentrics, metabolic stress, periodization, time-efficiency) + 10 BFR (mechanisms, moderators, young adults, BFR vs heavy-load, methodology/safety, ACL rehab, tendon rehab, risk stratification, older adults, BFR regimens/CV safety) |
| Nutrition | 40 | 1 original + 2 creatine + 15 expanded (protein, MPS, timing, pre-sleep, caffeine, beta-alanine, supplements, recovery, sleep) + 10 IF/meal frequency (TRE+RT body comp, IF+RT lean mass, muscle-centric IF, IF+CR exercise performance, protein distribution, per-meal protein, IF sports performance, Ramadan RT, Ramadan IF body comp, IF variants) + 12 micronutrient supplementation (vitamin D strength/performance, omega-3 inflammation/MPS, magnesium muscle soreness, minerals/trace elements, iron supplementation athletes, antioxidants vit C/E, broad micronutrient reviews) |
| Strength | 29 | 5 original + 10 new (progressive overload, autoregulation/RPE, VBT, concurrent training/interference, specificity, training frequency, neural adaptations, reps at %1RM) + 14 power/plyometrics (plyometric umbrella review, plyo optimization, drop jump methodology, RFD, complex-contrast training, power vs strength in older adults, weightlifting vs RT vs plyometrics, variable resistance, plyo vs complex training, reactive strength index, upper body plyometrics, power training aging, resisted sprint training, optimal power load) |
| Recovery | 14 | 2 original (deloading) + 12 new (overtraining, CWI, sleep, recovery techniques, RT recovery, HRV, sauna/heat, alcohol) |
| Body Composition | 13 | Cutting: RT for weight loss, exercise modalities during deficit, HIIT vs MICT, progressive vs severe restriction, muscle-sparing strategies, supplements during cuts. Bulking: energy surplus requirements, small vs large surplus, off-season bodybuilder nutrition, bulk-and-cut cycles. |
| Mobility | 11 | Stretching: acute effects on strength/power, chronic effects on strength/hypertrophy, intensity effects, techniques comparison, post-exercise recovery. Foam rolling: performance/recovery meta-analysis, vs stretching, SMR for athletes, chronic effects. Warm-up: specific warm-up for compound lifts. |
| General | 23 | Specific populations (12): older adults/sarcopenia (4), sex differences (3), menstrual cycle (2), beginners vs advanced (3). Mental health (11): RT for depression/anxiety in youth (Barahona-Fuentes), depression prevention (Zhao), high-intensity exercise & depression (Zeng), RT & self-esteem (Collins), self-efficacy/motivation (Martinez Kercher), RT & cognitive function (Cheng), exercise & cognition in older adults (Xu), acute RT & executive function (Huang), neuroplasticity/BDNF (Fernandes), stress/cortisol (Athanasiou), exercise & sleep (Alnawwar). |
| Injury | 22 | Tendinopathy: dose-response (Pavlova), patellar (Challoumas), Achilles exercise types (Sivrika), Achilles tendon adaptation (Merry), rotator cuff (Wu), autoregulation/load management (Burton), lateral elbow/tennis elbow (Yoon). Tendon adaptations: mechanical loading (Lazarczuk). Low back pain: posterior chain RT (Tataryn), exercise prescription (Zhao). Training through pain (Smith). Gym injuries & exercise selection (Bonilla). Bone health (10): mechanisms (Chang), RT & BMD in older adults (Massini), exercise types for BMD (Kemmler), high-impact exercises (Manaye), exercise intensities for osteoporosis (Kitagawa), RT protocols network meta (Wang), high-intensity RT for elderly (Cheng), exercise for osteoporosis/osteopenia (Alnasser), ACSM guidelines (Cui), jumping vs RT in youth (Miao). |
| Cardiovascular | 10 | Cardiac remodeling (Van Ochten), athlete's heart (Maxwell), aerobic vs RT vs combined for CVD risk (Lee/CardioRACE), weight training & mortality (Shailendra), HIIT for CV health (Ko), exercise intensity & VO2max (Crowley), RT for hypertrophy (Correia), isometric exercise & BP (Edwards), circuit RT & CRF (Ramos-Campo), minimum exercise dose (Behm). |
| Programming | 12 | Training splits: full-body vs split (Evangelista, Hamarsland). Exercise selection: compound vs isolation (Paoli), free weights vs machines (Haugen). Volume: weekly set volume (Ralston). Supersets (Zhang). Cluster sets (Cui). Advanced techniques: drop sets/rest-pause (Fonseca). Bodybuilder programs (Alves). Block periodization (Wetmore). Powerlifting: peaking (Travis*), scoping review (Silverthorne), min effective dose (Androulakis-Korakakis*), daily max vs periodized (Androulakis-Korakakis 2018). *Also in strength/hypertrophy categories. |

### Hypertrophy Expansion (10 papers) — ✅ Ingested

Added to address weak hypertrophy recall (2.5) from baseline. All CC-BY, 398 new chunks total.

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Singer et al. | 2024 | Rest interval duration (Bayesian meta-analysis) | 30 |
| Androulakis Korakakis et al. | 2024 | RT technique (ROM, tempo, contraction type) | 18 |
| Wilk et al. | 2021 | Movement tempo | 64 |
| Refalo et al. | 2023 | Proximity-to-failure (meta-analysis) | 35 |
| Evans | 2019 | Periodization for hypertrophy | 19 |
| Grgic et al. | 2017 | Linear vs undulating periodization (meta-analysis) | 30 |
| Warneke et al. | 2023 | Stretch-mediated hypertrophy | 62 |
| Hody et al. | 2019 | Eccentric contractions | 51 |
| Lawson et al. | 2022 | Metabolic stress vs mechanical tension | 51 |
| Iversen et al. | 2021 | Time-efficient training | 38 |

Ingestion quality: 8/10 clean. Hody and Singer have reference chunks mislabeled under FUNDING/Publisher's note sections (Frontiers back-matter bleed). Content is intact — only section metadata affected. Low impact since reference chunks are noise for retrieval.

9 new eval questions added (HYP-007 through HYP-015). Test dataset now 38 cases (15 HYP, 6 STR, 13 NUT, 2 CROSS, 2 OOS).

### Strength Expansion (10 papers) — ✅ Ingested

Added to address weak strength coverage (only 5 papers). All CC-BY, 560 new chunks total.

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Plotkin et al. | 2022 | Progressive overload (load vs rep progression) | 27 |
| Hickmott et al. | 2022 | Autoregulation (RPE/VBT) meta-analysis | 83 |
| Held et al. | 2022 | VBT vs traditional (network meta-analysis) | 29 |
| Schumann et al. | 2022 | Concurrent training interference meta-analysis | 22 |
| Methenitis | 2018 | Concurrent training review | 33 |
| Stone et al. | 2022 | Training specificity for strength-power | 43 |
| Ralston et al. | 2018 | Training frequency meta-analysis | 85 |
| Cuthbert et al. | 2021 | Training frequency in well-trained populations | 49 |
| Škarabot et al. | 2021 | Neural adaptations to resistance training | 26 |
| Nuzzo et al. | 2024 | Reps at % of 1RM meta-regression | 44 |

### Recovery Expansion (14 papers total) — ✅ Ingested

2 original + 12 new. All CC-BY, 538 total chunks (79 original + 459 new).

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Bell et al. | 2023 | Deloading consensus (Delphi approach) | 50 |
| Coleman et al. | 2024 | Deload period effects on muscular adaptations | 29 |
| Armstrong et al. | 2022 | Overtraining syndrome (complex systems) | 52 |
| Cadegiani & Kater | 2017 | Hormonal aspects of overtraining (systematic review) | 44 |
| Piñero et al. | 2024 | CWI effects on RT-induced hypertrophy (meta-analysis) | 33 |
| Moore et al. | 2022 | CWI vs passive recovery (meta-analysis + meta-regression) | 57 |
| Craven et al. | 2022 | Acute sleep loss on physical performance (meta-analysis) | 46 |
| Easow et al. | 2025 | Sleep deprivation on muscle strength (systematic review) | 29 |
| Dupuy et al. | 2018 | Recovery techniques comparison (meta-analysis: massage, CWI, compression, stretching, active recovery) | 29 |
| Sousa et al. | 2024 | Recovery in RT microcycle construction | 33 |
| Driller & Leabeater | 2023 | Recovery strategies and devices overview | 30 |
| Addleman et al. | 2024 | HRV for strength and conditioning recovery monitoring | 30 |
| Ahokas et al. | 2025 | Post-exercise heat exposure / sauna (systematic review) | 42 |
| Lakićević | 2019 | Alcohol and RT recovery (systematic review) | 34 |

Ingestion quality: 11/12 clean. Lakićević had 2 garbled section names (author name as header, body text bleed into Results header) — fixed directly in Supabase. Moore and Craven have \xa0 non-breaking spaces (normal Springer PDF artifact, harmless).

### Body Composition Expansion (13 papers) — ✅ Ingested

Added as new category (migration 009). All CC-BY, 538 new chunks total.

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Lahav et al. | 2026 | RT as key strategy for quality weight loss | 26 |
| Lafontant et al. | 2025 | RT vs AT vs CT for body fat loss (meta-analysis) | 80 |
| Xie et al. | 2025 | Exercise modalities during caloric restriction (network meta-analysis) | 39 |
| Khalafi et al. | 2025 | Concurrent training vs isolated for body composition | 84 |
| Giannopoulos et al. | 2025 | Bulk and cut dietary protocol (pilot RCT) | 32 |
| Helms et al. | 2023 | Small vs large energy surpluses in trained individuals | 33 |
| Vargas-Molina et al. | 2023 | Progressive vs severe energy restriction in trained women | 21 |
| Guo et al. | 2023 | HIIT vs MICT on fat loss (meta-analysis) | 44 |
| Ruiz-Castellano et al. | 2021 | Optimal fat loss phase for resistance-trained athletes | 42 |
| McCarthy & Berg | 2021 | Weight loss strategies and skeletal muscle mass loss risk | 42 |
| Iraki et al. | 2019 | Off-season nutrition recommendations for bodybuilders | 35 |
| Slater et al. | 2019 | Is energy surplus required for hypertrophy? | 42 |
| Willoughby et al. | 2018 | Supplements for lean mass during weight loss | 18 |

Ingestion quality: 11/13 clean. Khalafi had duplicated header ("3.1. Search Results 3.1. Search Results" → fixed to "3. Results"). Willoughby had journal metadata bleed into 2 section names ("Nutrients 2018 , 10 , x FOR PEER REVIEW" appended → fixed). Vargas-Molina has \xa0 non-breaking spaces (Springer artifact, harmless).

### Mobility Expansion (11 papers) — ✅ Ingested

New category (Priority 4). All CC-BY, 506 new chunks total.

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Chaabene et al. | 2019 | Acute static stretching → strength/power (review) | 26 |
| Warneke et al. | 2024 | Chronic static stretching → strength/hypertrophy (meta-analysis) | 61 |
| Bryant et al. | 2023 | Static stretching intensity → ROM/strength (systematic review) | 44 |
| Behm et al. | 2023 | Stretching techniques → ROM (meta-analysis) | 38 |
| Afonso et al. | 2021 | Strength training vs stretching for ROM (meta-analysis) | 110 |
| Zhang et al. | 2025 | Post-exercise stretching → recovery (meta-analysis) | 39 |
| Wiewelhove et al. | 2019 | Foam rolling → performance/recovery (meta-analysis) | 31 |
| Konrad et al. | 2021 | Foam rolling vs stretching (meta-analysis) | 31 |
| Martínez-Aranda et al. | 2024 | Self-myofascial release → athletes' performance (systematic review) | 75 |
| Pagaduan et al. | 2022 | Chronic foam rolling → flexibility/performance (systematic review) | 24 |
| Ribeiro et al. | 2020 | Specific warm-up for bench press/squat (RCT) | 27 |

Ingestion quality: 10/11 clean. Martínez-Aranda had duplicated header ("3. Results 3. Results" → fixed to "3. Results"). Konrad missing RESULTS section (merged into DISCUSSION — common for short Frontiers meta-analyses). Pagaduan missing "3. Results" (same pattern). Zhang missing Abstract section (Frontiers format variation). All content intact.

### Specific Populations Expansion (12 papers) — ✅ Ingested

Priority 5: Training for specific populations. All CC-BY, 498 new chunks total.

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Delaire et al. | 2025 | RT variables for sarcopenia muscle mass (meta-regressions) | 50 |
| Govindasamy et al. | 2025 | RT effects on sarcopenia risk (scoping review of mechanisms) | 61 |
| Tøien et al. | 2025 | Heavy strength training in older adults | 27 |
| Li et al. | 2024 | Age-associated differences in exercise recovery | 33 |
| Refalo et al. | 2025 | Sex differences in muscle size after RT (Bayesian meta-analysis) | 43 |
| James et al. | 2025 | Sex differences in muscle fiber types (systematic review + meta-analysis) | 61 |
| Nuckols et al. | 2026 | Sex differences in fatigue/recovery from RT | 36 |
| Colenso-Semple et al. | 2023 | Menstrual cycle and strength performance (umbrella review) | 24 |
| Niering et al. | 2024 | Menstrual cycle phases on maximal strength (meta-analysis) | 43 |
| Aslam et al. | 2025 | Neuromuscular adaptations: elite vs recreational (review) | 49 |
| Swinton et al. | 2024 | Dose-response modelling of RT (meta-analysis, training status moderator) | 35 |
| Lacio et al. | 2021 | Load effects in untrained vs trained (systematic review) | 36 |

Ingestion quality: 10/12 clean. Niering had duplicated header ("4. Discussion 4. Discussion" → fixed to "4. Discussion"). Colenso-Semple had garbled back-matter sections ("Confl ict of interest", "Publisher ' s note" → fixed). James et al. has \xa0 non-breaking spaces (Wiley artifact, harmless).

### Injury Expansion (12 papers) — ✅ Ingested

New category (migration 010). All CC-BY, 531 new chunks total.

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Pavlova et al. | 2023 | Resistance exercise dose for tendinopathy (meta-analysis) | 40 |
| Challoumas et al. | 2021 | Patellar tendinopathy management (network meta-analysis) | 30 |
| Sivrika et al. | 2023 | Achilles tendinopathy exercise types (systematic review) | 25 |
| Merry et al. | 2022 | Achilles tendon adaptation to resistance exercise (review) | 37 |
| Wu et al. | 2025 | Rotator cuff shoulder pain exercise modes (meta-analysis) | 37 |
| Lazarczuk et al. | 2022 | Tendon mechanical adaptations to loading (meta-analysis) | 63 |
| Tataryn et al. | 2021 | Posterior chain RT for chronic low back pain (meta-analysis) | 40 |
| Zhao et al. | 2025 | Exercise prescription for chronic low back pain (network meta-analysis) | 44 |
| Smith et al. | 2017 | Should exercises be painful? (meta-analysis) | 52 |
| Bonilla et al. | 2022 | Exercise selection and gym injuries (systematic review) | 65 |
| Yoon et al. | 2021 | Eccentric exercise for lateral elbow tendinopathy (meta-analysis) | 27 |
| Burton | 2021 | Autoregulation in RT for tendinopathy (review) | 71 |

Ingestion quality: 10/12 clean. Sivrika had duplicated header ("3.1. Description of Studies 3.1. Description of Studies" → fixed to "3. Results"). Wu had garbled back-matter ("Confl ict of interest", "Publisher ' s note" → fixed). Tataryn had "Publisher ' s Note" → fixed. Lazarczuk has \xa0 non-breaking spaces (Springer artifact, harmless). Smith has mixed-case headers (BJSM drop-cap formatting, cosmetic only).

### Cardiovascular Expansion (10 papers) — ✅ Ingested

New category (migration 010 already added). All CC-BY, 421 new chunks total.

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Van Ochten et al. | 2025 | Exercise-induced cardiac remodeling & CV outcomes (review) | 31 |
| Maxwell et al. | 2024 | Athlete's heart — acute to chronic adaptation (review) | 24 |
| Lee et al. | 2024 | CardioRACE trial: aerobic vs RT vs combined for CVD risk (RCT) | 38 |
| Shailendra et al. | 2024 | Weight training and all-cause/CVD/cancer mortality (cohort) | 29 |
| Ko et al. | 2025 | HIIT positive impacts on CV health (narrative review) | 39 |
| Crowley et al. | 2022 | Exercise training intensity on VO2max (umbrella review) | 31 |
| Correia et al. | 2023 | Strength training for arterial hypertension (meta-analysis) | 59 |
| Edwards et al. | 2024 | Isometric exercise training and hypertension (systematic review) | 84 |
| Ramos-Campo et al. | 2021 | Resistance circuit-based training and CRF (meta-analysis) | 54 |
| Behm et al. | 2023 | Minimalist training — minimum dose for fitness (review) | 32 |

Ingestion quality: 8/10 clean. Crowley missing Abstract section (Hindawi format, content intact in first chunk). Correia missing Abstract/Introduction sections (Scientific Reports puts Methods at end by design, first sections not detected as headers). Edwards and Behm have \xa0 non-breaking spaces (Springer artifact, harmless). Van Ochten has double spaces in section names (cosmetic, Annals of Medicine PDF artifact).

### Programming Expansion (12 papers) — ✅ Ingested

New category (migration 010 already included `programming`). All CC-BY, 469 new chunks total. 6 additional papers already in DB under hypertrophy/strength categories also cover programming topics (Bernardez-Vazquez, Schoenfeld, Krzysztofik, Travis, Thompson, Androulakis-Korakakis 2021).

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Evangelista et al. | 2021 | Split vs full-body routine (RCT, untrained) | 24 |
| Hamarsland et al. | 2022 | Equal-volume frequency in trained (RCT) | 24 |
| Paoli et al. | 2017 | Single vs multi-joint exercises (RCT) | 19 |
| Haugen et al. | 2023 | Free weights vs machines (meta-analysis) | 46 |
| Ralston et al. | 2017 | Weekly set volume & strength (meta-analysis) | 37 |
| Zhang et al. | 2025 | Superset vs traditional (meta-analysis) | 49 |
| Cui et al. | 2025 | Long-term cluster training (meta-analysis) | 35 |
| Fonseca et al. | 2023 | Traditional vs advanced techniques (meta-analysis) | 88 |
| Alves et al. | 2020 | Bodybuilder training programs (narrative review) | 35 |
| Wetmore et al. | 2020 | Block periodization training (RCT) | 23 |
| Silverthorne et al. | 2025 | Powerlifting sport science (scoping review) | 65 |
| Androulakis-Korakakis et al. | 2018 | Daily max vs periodized comp prep (pilot RCT) | 24 |

Ingestion quality: 11/12 clean. Evangelista had ❚ Unicode characters in section names (Einstein/SciELO formatting) — fixed. Fisher & Csapo 2021 was removed (2-page editorial with no substantive content). Silverthorne has \xa0 non-breaking spaces (Springer artifact, harmless).

### Mental Health Expansion (11 papers) — ✅ Ingested

Priority 9: Mental health & exercise, category: general. All CC-BY, 432 new chunks total.

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Barahona-Fuentes et al. | 2021 | Strength training & psychosocial disorders in adolescents (meta-analysis) | 43 |
| Zhao et al. | 2025 | Exercise-based depression prevention in older adults (meta-analysis) | 38 |
| Zeng et al. | 2025 | High-intensity exercise on depression (meta-analysis) | 43 |
| Collins et al. | 2019 | RT on self-esteem/self-worth in youth (meta-analysis) | 43 |
| Martinez Kercher et al. | 2024 | Self-efficacy, motivation & RT outcomes (quasi-experimental) | 34 |
| Cheng et al. | 2022 | RT mechanisms for cognitive function in elderly (systematic review) | 39 |
| Xu et al. | 2023 | Exercise for cognitive function in older adults (meta-analysis) | 27 |
| Huang et al. | 2022 | Acute RT on executive function (systematic review) | 30 |
| Fernandes et al. | 2020 | Exercise & neuroplasticity/brain function (systematic review) | 71 |
| Athanasiou et al. | 2022 | Endocrine stress responses to exercise (review) | 37 |
| Alnawwar et al. | 2023 | Physical activity & sleep quality (systematic review) | 27 |

Ingestion quality: 9/11 clean. Barahona-Fuentes had duplicated header ("4. Discussion 4. Discussion" → fixed to "4. Discussion"). Collins had garbled back-matter ("Publisher ' s Note" → fixed). Zhao and Zeng missing Abstract section (Frontiers format, content intact in first chunk). Athanasiou has long but legitimate section names. Fernandes has 71 chunks (large systematic review, expected).

### Bone Health Expansion (10 papers) — ✅ Ingested

Priority 10: Bone health, category: injury. All CC-BY, 443 new chunks total.

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Chang et al. | 2022 | Regulation of bone health through exercise: mechanisms and types (review) | 33 |
| Massini et al. | 2022 | RT and BMD in older adults (meta-analysis) | 26 |
| Kemmler et al. | 2020 | Different exercise types for BMD in postmenopausal women (meta-analysis) | 75 |
| Manaye et al. | 2023 | High-intensity and high-impact exercises for bone health (systematic review) | 18 |
| Kitagawa et al. | 2022 | Exercise intensity comparison for BMD in osteoporosis (meta-analysis) | 37 |
| Wang et al. | 2023 | RT protocol comparison for BMD — network meta-analysis | 51 |
| Cheng et al. | 2025 | Optimizing high-intensity RT for BMD in elderly — network meta-analysis | 53 |
| Alnasser et al. | 2025 | Exercise loading for osteoporosis/osteopenia (meta-analysis) | 64 |
| Cui et al. | 2023 | ACSM-based exercise for osteoporosis BMD (meta-analysis) | 56 |
| Miao et al. | 2025 | High-impact jumping vs RT for bone in children/adolescents (meta-analysis) | 30 |

Ingestion quality: 6/10 clean. Massini had duplicated header ("3. Results 3. Results" → fixed to "3. Results"). Chang, Wang, and Cui had garbled Frontiers back-matter ("Confl ict of interest", "Publisher ' s note" → fixed). Kemmler has \xa0 non-breaking spaces (Springer artifact, harmless).

Corpus expansion targets and future RAG improvement ideas are in `FUTURE-PLANS.md`.

### BFR Expansion (10 papers) — ✅ Ingested

Priority 11: Blood Flow Restriction Training, category: hypertrophy. All CC-BY, 440 new chunks total.

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Davids et al. | 2023 | BFR mechanisms and athletic applications (narrative review) | 38 |
| Geng et al. | 2024 | Moderators of BFR vs high-load RT (meta-analysis) | 59 |
| Ma et al. | 2024 | BFR + RT strength/thickness in young adults (meta-analysis + meta-regression) | 55 |
| Wang et al. | 2025 | BFR vs heavy-load on strength/power/speed (meta-analysis) | 46 |
| Patterson et al. | 2019 | BFR methodology, application, and safety (comprehensive review) | 43 |
| Butt et al. | 2024 | BFR after ACL reconstruction (meta-analysis) | 27 |
| Burton et al. | 2022 | BFR in tendon rehabilitation (scoping review) | 35 |
| Nascimento et al. | 2022 | BFR risk stratification for exercise and rehabilitation (review) | 57 |
| Fabero-Garrido et al. | 2022 | Low-load BFR vs traditional RT in adults >60 (meta-analysis) | 39 |
| Ren et al. | 2025 | BFR regimens + CV safety in older adults (network meta-analysis) | 41 |

Ingestion quality: 8/10 clean. Ma had garbled Frontiers back-matter ("Confl ict of interest", "Publisher ' s note" → fixed). Fabero-Garrido had body text bleed into Discussion header ("ing applied with near limb occlusion pressure ( 4. Discussion" → fixed to "4. Discussion"). Davids has \xa0 non-breaking spaces (Springer artifact, harmless).

### Power & Plyometrics Expansion (14 papers) — ✅ Ingested

Priority 12: Power & Plyometrics, category: strength. All CC-BY, 715 new chunks total.

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Kons et al. | 2023 | Plyometric training effects on performance (umbrella review) | 57 |
| Dudagoitia Barrio et al. | 2023 | Plyometric jump training optimization (scoping review) | 66 |
| Montoro-Bombú et al. | 2023 | Drop jump volume and intensity methodology (systematic review) | 65 |
| Maffiuletti et al. | 2016 | Rate of force development: physiology and methodology (review) | 52 |
| Thapa et al. | 2024 | Complex-contrast training (systematic scoping review) | 39 |
| Balachandran et al. | 2022 | Power vs strength training in older adults (meta-analysis) | 24 |
| Morris et al. | 2022 | Weightlifting vs RT vs plyometrics for strength/power/speed (meta-analysis) | 76 |
| Shi et al. | 2022 | Variable resistance training on force/velocity/power (meta-analysis) | 39 |
| Wang et al. | 2023 | Plyometric vs complex training for explosive power (systematic review) | 44 |
| Ramirez-Campillo et al. | 2023 | Plyometric training on reactive strength index across lifespan (meta-analysis) | 58 |
| Garcia-Carrillo et al. | 2023 | Upper-body plyometric training (meta-analysis) | 68 |
| el Hadouchi et al. | 2022 | Power vs strength training effectiveness in older adults (meta-analysis) | 56 |
| Myrvang & van den Tillaar | 2024 | Resisted and assisted sprint training (meta-analysis) | 49 |
| Sarabia et al. | 2017 | Training at optimal power load vs traditional power training (RCT) | 22 |

Ingestion quality: 10/14 clean. Kons had concatenated header ("Results Search Results" → fixed to "Results"). Dudagoitia Barrio had duplicated header ("4. Results 4. Results" → fixed to "4. Results"). Montoro-Bombú had Frontiers ligature issues ("Scienti fi c-methodological..." → fixed, "Confl ict of interest" → fixed, "Publisher ' s note" → fixed), also missing Abstract section (Frontiers format). Wang had garbled Frontiers back-matter ("Confl ict of interest", "Publisher ' s note" → fixed). Morris and Ramirez-Campillo have \xa0 non-breaking spaces (Springer artifact, harmless).

### Intermittent Fasting & Meal Frequency Expansion (10 papers) — ✅ Ingested

Priority 13: IF/meal frequency, category: nutrition. All CC-BY, 372 new chunks total.

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Ho et al. | 2024 | TRE + RT body composition (meta-analysis) | 29 |
| Keenan et al. | 2020 | IF + RT lean body mass (systematic review) | 36 |
| Williamson et al. | 2021 | Muscle-centric perspective on IF (review) | 21 |
| Kazeminasab et al. | 2025 | IF + calorie restriction exercise performance (meta-analysis) | 94 |
| Hudson et al. | 2020 | Protein distribution & muscle outcomes (review) | 42 |
| Schoenfeld & Aragon | 2018 | Per-meal protein for muscle building (review) | 14 |
| Conde-Pipó et al. | 2024 | IF & sports performance (systematic review) | 26 |
| Triki et al. | 2024 | Ramadan RT muscle strength/hormones (RCT) | 33 |
| Correia et al. | 2021 | Ramadan & non-Ramadan IF body composition (meta-analysis) | 52 |
| Aragon et al. | 2022 | IF variants & body composition (narrative review) | 25 |

Ingestion quality: 7/10 clean. Ho had duplicated header ("3.1. Study Inclusion 3.1. Study Inclusion" → fixed to "3. Results"). Hudson had body text bleed into header ("86 -90). 2. Observational Research" → fixed to "2. Observational Research"). Schoenfeld had garbled back-matter ("Publisher ' s Note" → fixed). Williamson missing Abstract section (Frontiers format, content intact in first chunk). Triki missing Abstract section (Frontiers format). Correia missing Abstract section (Frontiers format — has "KEY POINTS" instead).

### Micronutrient Supplementation Expansion (12 papers) — ✅ Ingested

Priority 14. All CC-BY, 629 new chunks total.

| Authors | Year | Topic | Chunks |
|---------|------|-------|--------|
| Han et al. | 2024 | Vitamin D3 & athlete strength (meta-analysis) | 46 |
| Wicinski et al. | 2019 | Vitamin D & exercise performance (review) | 20 |
| Fernandez-Lazaro et al. | 2024 | Omega-3 & post-exercise inflammation/damage (systematic review) | 135 |
| Therdyothin et al. | 2024 | Omega-3 & muscle protein synthesis (meta-analysis) | 42 |
| Tarsitano et al. | 2024 | Magnesium & muscle soreness (systematic review) | 25 |
| Heffernan et al. | 2019 | Minerals & trace elements in exercise (systematic review) | 60 |
| Smid et al. | 2024 | Oral iron supplementation in athletes (meta-analysis) | 33 |
| Kardasis et al. | 2023 | Iron & athletic performance (review) | 41 |
| Dutra et al. | 2020 | Vitamin C/E & strength training (meta-analysis) | 24 |
| Higgins et al. | 2020 | Antioxidants & exercise performance (review) | 49 |
| Peeling et al. | 2023 | Vitamin/mineral supplements in athletes (review) | 24 |
| Ghazzawi et al. | 2023 | Micronutrients & athletic performance (systematic review) | 130 |

Ingestion quality: 10/12 clean. Fernandez-Lazaro had duplicated header ("3.1. Study Selection 3.1. Study Selection" → fixed to "3.1. Study Selection"). Higgins had ligature issue ("6. E ects" → fixed to "6. Effects of Vitamin E and C Supplementation..."). Han and Dutra missing Abstract section (Frontiers/Hindawi format, content in first chunk). Therdyothin missing Abstract (OUP format). Smid, Peeling, Tarsitano have \xa0 non-breaking spaces (Springer artifact, harmless).

### Test Dataset: 100 cases (15 HYP, 10 STR, 17 NUT, 6 REC, 7 BC, 7 MOB, 10 GEN, 12 INJ, 7 CVD, 7 PROG, 2 OOS)
Post-expansion eval complete (2026-03-19): 4.54/5 overall. See "Post-Expansion Eval Results" section above.
