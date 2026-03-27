# Future Plans & Improvement Ideas

---

## RAG v1 Improvements (before moving to v2)

Prioritized by expected eval impact based on post-expansion results (4.57/5, 100 cases). Generation metrics are near-ceiling (Ans=5.0, Fai=4.9). **Retrieval is the bottleneck** — Contextual Recall (4.1) is weakest, 9 cases scored 2.

### Priority A: Increase top_k (5 → 8-10)
**Expected impact: High (Recall, Precision) | Effort: Trivial**
With 8,284 chunks competing for 5 slots, relevant chunks get squeezed out. Especially hurts broad multi-paper questions (strength Rec=3.6, programming Rec=3.7). Just change the env var / config default. Negligible cost on Paid Tier 1 (~2,400 extra tokens/query at top_k=8).

### Priority B: Post-Ingestion Noise Cleanup
**Expected impact: Medium (Precision, Recall) | Effort: Low**
~16% of chunks are noise: references (163), author contributions (18), supplementary material (9), funding (5), publisher's note, data availability, acknowledgments, conflict of interest, etc. These waste top-k slots for zero retrieval value. Deleting them gives relevant chunks a better shot without any model changes. DELETE by section name after ingestion — inspect before deleting (Frontiers back-matter bleed risk).

### Priority C: Re-ranking (cross-encoder)
**Expected impact: High (Precision, Recall) | Effort: Medium**
Retrieve top-20 with bi-encoder (pgvector), re-rank with cross-encoder, keep best 5-8. Fixes precision problems where "somewhat related" chunks outrank "directly answers the question" chunks. Body-comp (Pre=3.6) and mobility (Pre=3.9) would benefit most — semantically similar chunks from neighboring categories steal top-k slots. Pairs well with top_k increase.

### Priority D: Abstract-Augmented Retrieval
**Expected impact: Medium (Recall) | Effort: Low**
After normal top-k retrieval, check which papers the returned chunks come from. For each cited paper, if its abstract chunk isn't already in the top-k, inject it into the prompt context. Gives the LLM both the forest (abstract = paper's overall conclusion) and the trees (specific chunks = evidence). Cheap — abstracts are already stored as chunks, just lookup by paper_id + section="Abstract".

### Priority E: Judge Reliability Fix
**Expected impact: Low (eval accuracy) | Effort: Low**
2/100 cases had JSON parse failures in combined judge mode (STR-007, PROG-008 — fallback to score 3, actual scores were 4.8 and 4.2). Either retry on parse failure or improve the combined judge prompt to produce cleaner JSON.

### Lower Priority (defer until above plateau)

**Two-Stage Retrieval** — Search abstracts first to identify relevant papers, then search chunks within those papers. Better for broad multi-paper questions. Bigger architectural change.

**Cross-Validate Eval with Different Judge Model** — Same-model bias (Gemini judges Gemini) may inflate faithfulness scores. Use `--judge-model` flag with GPT-4o or Claude. Already supported in CLI.

**Async Supabase in Web Handlers** — `supabase-py` is synchronous. DB calls in SSE handler block briefly. For production, wrap in `asyncio.to_thread()`. Low priority — not a bottleneck.

### Chat Answer Feedback
User-facing thumbs up/down on each assistant message, with optional "why" (predefined tags + free text).
- **Tags**: "Incorrect info", "Missing details", "Bad sources", "Not relevant", "Too verbose", "Great answer"
- **DB**: `chat_feedback` table — message_id (FK), user_id, rating (up/down), tags (JSONB array), comment (text), created_at
- **Frontend**: Thumbs up/down icons below each assistant message. On click, expand a small popover with tag chips + optional text input. Submit fires POST to backend.
- **Uses**: Identify weak spots in the corpus (which questions get downvoted?), prioritize future paper additions, supplement automated eval with real user signal, track quality over time.

---

## RAG v2: Agentic RAG with Router

### Architecture
```
User question
      |
      v
   Router (LLM classifies intent)
      |
      +-- "literature question"    --> RAG Pipeline (research papers, vector search)
      |
      +-- "workout data question"  --> SQL query against workout tables
      |                                (workouts, exercises, workout_sets)
      |
      +-- "exercise info question" --> Structured DB lookup (exercise_details table)
      |                                Form cues, muscles targeted, visuals
      |
      +-- combinations             --> Run multiple branches, combine response
                                       e.g. "The RDL targets hamstrings and glutes [DB].
                                       Research suggests 3-4s eccentric tempo maximizes
                                       hamstring hypertrophy [Wilk 2021]."
```

### Three Retrieval Methods
- **Literature** = unstructured text → vector search (v1 RAG)
- **Workout data** = structured numbers → SQL queries (user's logged data)
- **Exercise info** = structured knowledge → direct DB lookup (no embedding needed)

Each is a fundamentally different data type, which is why the router is justified.

### Exercise Info Branch
Structured `exercise_details` table (enriched version of the workout logging `exercises` table):
- `name`, `aliases` (e.g. "RDL", "Romanian deadlift")
- `primary_muscles`, `secondary_muscles` (JSON arrays)
- `form_cues` (ordered list of key technique points)
- `common_mistakes`
- `equipment`, `difficulty`
- `image_url` / `video_url`

No embedding, no vector search — just a lookup. LLM formats the structured data into a natural response, frontend renders the visuals.

### Prerequisites
- Workout logging feature must be built first (Phase 3 in PLAN.md)
- v1 RAG must be stable with good eval scores
- Exercise details table needs to be populated with form/muscle data
- Need sufficient workout data in the DB to test the workout data branch

---

## Corpus Expansion — Complete

All 14 priorities complete. 195 papers, ~8,284 chunks across 10 categories. All CC-BY from PMC Open Access Subset. Full paper lists in `CONTEXT.md` and `papers/manifest.json`.

| Priority | Category | Papers | Chunks |
|----------|----------|--------|--------|
| 1 | Strength | 5 → 15 | 560 |
| 2 | Recovery | 2 → 14 | 459 |
| 3 | Body Composition | 0 → 13 | 538 |
| 4 | Mobility | 0 → 11 | 506 |
| 5 | Specific Populations | 0 → 12 | 498 |
| 6 | Injury/Tendon | 0 → 12 | 531 |
| 7 | Cardiovascular | 0 → 10 | 421 |
| 8 | Programming | 0 → 12 | 469 |
| 9 | Mental Health | 0 → 11 | 432 |
| 10 | Bone Health | 0 → 10 | 443 |
| 11 | BFR | 0 → 10 | 440 |
| 12 | Power/Plyometrics | 0 → 14 | 715 |
| 13 | IF/Meal Frequency | 0 → 10 | 372 |
| 14 | Micronutrients | 0 → 12 | 629 |

### Post-Expansion Eval (2026-03-19)
- 100 test cases → **4.57/5 overall** (baseline was 4.55/29 cases)
- All expansions held quality. Hypertrophy recall fixed (2.5 → 4.4). 18 perfect scores.
- STR-007/PROG-008 were judge JSON parse failures (rerun: 4.8/4.2)
- See CONTEXT.md for full results breakdown, category rankings, and analysis

---

## Exercise Library & Muscle Data Overhaul

### Context
MC-Oruc/FitnessApp (source for muscle activation mappings) is an unsourced weekend project by a game developer — no EMG studies, no kinesiology references. Our 137 exercises need proper EMG-backed muscle activation research. Expanding library from 137 → ~200 exercises.

### Muscle Groups: 33 → 36
Adding 3 new muscle groups (requires DB migration):
- **Hip Adductors** — new "Adductors" category. Fixes broken Hip Adductor Machine mapping; enables sumo/lateral lunge adductor tracking.
- **Neck** — new "Neck" category. Enables neck curl/extension exercises (currently unmappable).
- **Rotator Cuff** — under "Shoulders" category. Enables external rotation, face pull prehab tracking.

### Exercise Library: 137 → ~200
Source: free-exercise-db (874 exercises, public domain). Pick ~63 additional common gym exercises. All ~200 need EMG-researched muscle activation mappings with real sources.

### Volume Tracking per Muscle
Aggregate sub-groups by category for display (e.g., Upper Chest + Mid Chest + Lower Chest → "Chest" weekly volume). Keep granular 36 groups for mapping accuracy.

### Exercise Video URLs
No free, open-source, commercially-usable video library exists at scale. Options researched:
- **YouTube links** — link to curated videos (free, don't control content)
- **YMove** — $29/mo, 636 exercises, royalty-free commercial HD video. Best paid option.
- **wger** — CC-BY-SA 3.0, only 78 videos (too sparse)
- **exercemus** — YouTube URLs available, MIT license with per-exercise attribution
- **MuscleWiki** — 7,300 videos but **non-commercial only**
- **Create own** — record/commission for top exercises

Decision deferred. Text instructions available from free-exercise-db (public domain) and wrkout (2,500+, public domain).

---

## Phase 3: Workout Logging — Polish & Remaining Work

### Bugs to Fix
- ~~**SetRow race condition** — fixed: debounce timer now cleared on completion~~
- ~~**"Minimize" is actually discard** — fixed: renamed to "Close", confirm says "You can resume it later"~~
- ~~**Cache invalidation after finish** — not a bug: both onComplete and onClose call loadWorkouts()~~

### Missing Features (already in DB, no frontend)
- ~~**Workout detail view** — `handleViewWorkout` is a stub; clicking a history card does nothing~~ ✅ Implemented
- **Superset UI** — `superset_group` column exists in DB, no frontend support
- ~~**RPE input** — field exists in workout_sets, no UI~~ ✅ Implemented
- **Set type selector** — working/warmup/dropset/failure types exist in DB, no UI to change
- ~~**Rest timer per exercise** — `rest_timer_seconds` column exists, no countdown UI~~ ✅ Implemented
- **Exercise notes** — `workout_exercises.notes` column exists, no UI during workout
- **Exercise video URLs** — field exists in DB, not populated or displayed

### UX Polish
- **No per-set sync feedback** — 500ms debounce is invisible to the user
- **PREV column shows "-" for extra sets** — could show best/last set instead
- **Inconsistent empty states** — WorkoutsScreen has emoji+CTA, modals have plain text
- **No retry on failed set syncs** — only global error banner, no per-set recovery
- **CreateExerciseForm incomplete** — doesn't expose movement_pattern, force_type, laterality, is_compound, instructions

### Brainstormed Improvements

**During-Workout Flow:**
- ~~**Auto-populate from last session** — tap PREV to fill weight/reps inputs (currently display-only), then just adjust~~ ✅ Implemented
- **Reorder sets** — drag or long-press to rearrange sets within an exercise
- **Plate calculator** — "I have 135 on the bar, what plates is that?"
- ~~**Rest timer with auto-start** — checking off a set starts a countdown (rest_timer_seconds column exists), notify when done~~ ✅ Implemented

**Post-Workout / History:**
- **Edit completed workouts** — fix typos (logged 135 instead of 185), add/remove sets after the fact, update rating/notes
- **Workout comparison** — side-by-side with last session of same exercises, shows progression at a glance *(straddles Phase 3/4)*
- **PR detection & celebration** — surface new personal records (weight, reps, estimated 1RM) immediately with visual feedback *(straddles Phase 3/4)*
- **Estimated 1RM calculation** — Epley/Brzycki formula per exercise, useful for programming and strength tracking *(straddles Phase 3/4)*

**Quality of Life:**
- ~~**Recent exercises / favorites** — "recent" or "favorites" section at top of exercise search (most people rotate 15-20 exercises)~~ ✅ Recent implemented (favorites deferred)
- **Copy previous workout** — "do what I did last Tuesday" — one tap to clone a past workout as starting point
- **Swipe to delete sets** — faster than three-dot menu → delete → confirm

**Data Integrity:**
- **Offline support / queue** — sets queue locally if signal lost (gym basements), sync when back online

### Deferred Features
- **Templates/routines** — save and reuse workout templates
- **Accessibility** — div menus need ARIA roles, color-only status badges need icon supplements

---

## App Features (PLAN.md Phases 4-6)

### Phase 4: Progress Tracking
- Historical workout view
- Exercise-specific progress charts
- Personal records (PRs) tracking
- Volume over time visualization

### Phase 5: AI Insights
- Trend analysis using workout data
- Training recommendations
- Recovery insights
- Consistency scoring

### Phase 6: Polish
- Flame visualization based on consistency
- Streak tracking
- Mobile-responsive improvements
- Error handling & edge cases

---

## Deployment
| Service | Platform |
|---------|----------|
| Frontend | Vercel (auto-deploy from main) |
| Backend | Railway or Render |
| Database | Supabase (already running) |
