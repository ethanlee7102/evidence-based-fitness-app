### Context Folder Conventions

When catching up at session start, read the active files in `context/` (this file, `ROADMAP.md`, `PORTFOLIO-NARRATIVE.md`, `CONTEXT.md`, `PLAN.md`, `EVAL-PLAN.md`, `FUTURE-PLANS.md`). **Skip `context/archive/` unless explicitly directed to specific files there, or unless working on a task whose active doc points at an archived file.** Archive contents are deep-reference material (implementation walkthroughs, recall-failure forensics, retrieval target chunks) — useful when you need them, wasteful to load every session.

Active files point at archive files where relevant — e.g., ROADMAP decision #11 (reranking) points at `archive/RETRIEVAL-TARGET-CHUNKS.md` as the success metric for Phase 2 retrieval work.

### Implementation Plan
Refer to `PLAN.md` for the priority summary and `ROADMAP.md` for the authoritative build order and decision log. Update `ROADMAP.md` as decisions are made.

### Teaching Mode
After completing each implementation task, pause and explain:

First give a summary of what was built (the what).

1. **The "why"** — What problem does this design decision solve? What alternatives were rejected and why?
2. **The bigger picture** — How does this piece connect to the overall architecture?
3. **The trap** — What's the most common mistake developers make here, and how does this implementation avoid it?
4. **The pattern** — What named design principle or industry pattern does this reflect (e.g. dependency injection, idempotency, single responsibility)?

Give thorough explanations by default. If an explanation will be very long, 
summarize it first, then ask if I want to go deeper on any part. If I ask "just do it," skip teaching mode for that task.

# Flame Fitness - Project Context

## Overview

**This is a portfolio builder for jump #1 in a job search at 1 YOE.** Realistic target list (apply broadly): **Junior AI Engineer / AI Engineer roles** at Series A/B AI-first startups, **Software Engineer / Backend Engineer doing AI work** at Series A/B/C AI-using companies, or mid-sized tech companies with AI work. Comp range $110-150k base in major markets. Not targeting frontier labs, Tier 1 stable companies, or Senior-level destination titles — those are jump #2 territory. Full calibration in `context/PORTFOLIO-NARRATIVE.md`.

**Important: realistic hiring level ≠ reduced work quality.** This portfolio is built to senior-quality depth — that's *exactly* what differentiates a 1-YOE applicant from the typical Junior/Mid pool. The calibration is about realistic interview positioning, not about cutting corners.

The technical focus is a RAG / LLM / agentic AI system; the workout logging app is the substrate that makes the AI features non-toy (real user training data, rich domain literature). The headline portfolio story is the AI system; the working full-stack app is the proof of general engineering competence.

## Tech Stack
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Backend**: Python + FastAPI
- **Database/Auth/Storage**: Supabase (PostgreSQL)
- **Monorepo**: pnpm workspaces

## Project Structure

```
flame-fitness/
├── apps/
│   ├── web/                      # React frontend (port 3000)
│   │   └── src/
│   │       ├── features/         # Feature-based modules
│   │       │   ├── auth/         # {components, hooks, screens, services, types}
│   │       │   ├── dashboard/    # Layout shell (Sidebar, DashboardLayout)
│   │       │   ├── home/         # Landing page + HomeDashboardScreen
│   │       │   ├── workouts/     # Workout logging + history
│   │       │   ├── analysis/     # AI trends, charts
│   │       │   ├── chat/         # AI assistant (RAG chatbot)
│   │       │   │   ├── components/  # TypingIndicator, CitationCard, SuggestedQuestions,
│   │       │   │   │                # ChatMessage, ChatInput, ChatMessageList, SessionSidebar
│   │       │   │   ├── hooks/       # useChat (state management, SSE callbacks)
│   │       │   │   ├── screens/     # ChatScreen (full chat UI)
│   │       │   │   ├── services/    # chatService (REST + SSE streaming)
│   │       │   │   └── types/       # Citation, ChatSession, ChatMessageData, etc.
│   │       │   ├── profile/      # User settings
│   │       │   └── onboarding/   # Multi-step user onboarding
│   │       ├── shared/           # Shared UI (Button, Card, Loading, Layout)
│   │       ├── navigation/       # AppRouter, ProtectedRoute, OnboardingRoute
│   │       └── lib/              # supabase.ts, api.ts
│   │
│   └── api/                      # Python backend (port 8000)
│       ├── src/
│       │   ├── api/              # Route handlers (health, profile, chat)
│       │   │   └── chat.py               # SSE streaming + session CRUD (5 endpoints)
│       │   ├── core/             # Business logic
│       │   │   ├── embedding_provider.py  # Voyage AI embed_texts/embed_query
│       │   │   ├── llm_provider.py        # Gemini generate/generate_stream
│       │   │   ├── ingestion.py           # PDF extraction, chunking, ingestion pipeline
│       │   │   ├── retrieval.py           # retrieve_chunks() → vector search → RetrievalResult
│       │   │   ├── rag_pipeline.py        # rag_query/rag_query_stream → cited answers
│       │   │   └── trace_logger.py        # Fire-and-forget RAG trace logging
│       │   ├── schema/           # Pydantic models (profile.py, rag.py)
│       │   ├── service/          # db_service, storage_service, chat_service
│       │   ├── utils/            # config, auth, logging
│       │   └── db.py             # Supabase client
│       ├── scripts/
│       │   ├── ingest_paper.py   # Single paper CLI ingestion
│       │   ├── ingest_batch.py   # Batch ingestion from manifest.json
│       │   ├── reingest_all.py   # Delete all + re-ingest all papers from manifest
│       │   ├── evaluate_rag.py   # RAG evaluation CLI (--combined, --dry-run, --verbose)
│       │   ├── test_retrieval.py # CLI retrieval testing
│       │   └── test_rag_pipeline.py # CLI end-to-end RAG testing
│       ├── papers/               # PDF storage (gitignored) + manifest.json
│       ├── tests/
│       │   └── eval/             # RAG evaluation test suite
│       └── app.py                # FastAPI entry point
│
├── packages/shared/types/        # Shared TypeScript types (profile.ts, user.ts)
└── supabase/migrations/          # Database schema
```

## Key Patterns

### Frontend
- **Feature-based architecture**: Each feature has components/, hooks/, screens/, services/, types/
- **Auth via Supabase**: useAuth hook provides user, session, signIn, signOut
- **API calls**: Use `apiRequest()` from lib/api.ts with JWT token
- **Protected routes**: Wrap with `<ProtectedRoute>` component
- **Onboarding required routes**: Wrap with `<OnboardingRoute>` for routes that require completed profile

### Backend
- **Entry point**: `app.py` (run with `uvicorn app:app`)
- **Auth**: JWT verification via `get_current_user` dependency
- **HTTP clients**: Shared module-level `httpx.AsyncClient` per provider (connection pooling). Cleaned up via FastAPI `lifespan` hook in `app.py`.
- **Embedding**: `src/core/embedding_provider.py` — `embed_texts()` and `embed_query()` via Voyage AI. `embed_texts()` has retry logic (3 attempts, exponential backoff on 429/500/503).
- **LLM**: `src/core/llm_provider.py` — `generate()` and `generate_stream()` via Gemini (2.5 Flash). Both accept `temperature`, `max_tokens`, and `messages` (multi-turn history) params. Role alternation warning log for Gemini's strict user/model requirement.
- **RAG Pipeline**: `src/core/rag_pipeline.py` — `rag_query()` (non-streaming for eval) and `rag_query_stream()` (streaming for chat UI). Conditional query rewriting on follow-ups. Citations as `[Author, Year, p. X]`. Temperature 0.3 for faithfulness. `grounded: bool` flag for UI display.
- **Ingestion**: `src/core/ingestion.py` — `extract_sections()`, `chunk_sections()`, `compute_content_hash()`, `ingest_paper()`. Uses IBM Docling + pymupdf hybrid: Docling (DocLayNet ML model) handles layout analysis, reading order, header detection, tables; pymupdf provides font size/bold via bounding box spatial matching for header hierarchy classification. Layered hierarchy: 1a) font size grouping with title-level skip (while loop skips chains of ≤2-member font groups when a ≥3-member group exists downstream), 1b) bold tiebreaker, 1c) ALL_CAPS tiebreaker, 2) text pattern fallback. Abstract detection: force-promotes "Abstract" headers to major regardless of font size, and scans pre-header body text for "Abstract:" labels (handles MDPI papers where abstract is body text, not a header).
- **Retrieval**: `src/core/retrieval.py` — `retrieve_chunks(query, top_k, category, similarity_threshold)`. Embeds query via Voyage AI, calls `match_chunks` RPC (pgvector cosine similarity), returns `RetrievalResult` dataclass (chunks + query + timing + embedding_time_ms). Logs query, chunk count, similarity range, timing at INFO level.
- **TraceLogger**: `src/core/trace_logger.py` — `log_trace()` fires async task via `asyncio.create_task()`. Never blocks, never raises. Logs to `rag_traces` table with full chunk text snapshots.
- **ChatService**: `src/service/chat_service.py` — Session CRUD, message persistence, `get_recent_messages()` returns `list[ChatMessage]` for RAG history (last 10). Uses service_role client, enforces user_id in every query.
- **Chat API**: `src/api/chat.py` — 5 endpoints: `POST /chat/message` (SSE streaming), `GET /chat/sessions`, `GET /chat/sessions/{id}`, `GET /chat/sessions/{id}/messages`, `DELETE /chat/sessions/{id}`. SSE event flow: session → citations → data* → done. Auto-title via fire-and-forget LLM call.

### Database Tables
- `profiles` - extends Supabase auth.users with onboarding fields:
  - `display_name`, `birthday`, `gender`, `height_cm`, `weight_kg`
  - `units_preference`, `experience_level`, `goal`
  - `workout_days_per_week`, `preferred_days`, `injuries_limitations`
  - `onboarding_completed`, `onboarding_completed_at`
- `muscle_groups` - 36 reference rows (name, category, display_order). 13 categories: Chest, Back, Shoulders, Biceps, Triceps, Forearms, Quads, Hamstrings, Glutes, Calves, Abs, Adductors, Neck (Rotator Cuff is under Shoulders)
- `exercises` - global library (386 seeded) + user custom. Fields: name, aliases, equipment, movement_pattern, force_type, body_region, laterality, is_compound, instructions, video_url, is_global, created_by
- `exercise_muscles` - junction table (exercise_id, muscle_group_id, activation_level: maximum/high/medium/partial)
- `workouts` - workout sessions (user_id, started_at, completed_at, duration_seconds, body_weight_kg, rating 1-5, notes)
- `workout_exercises` - exercises within a workout (workout_id, exercise_id, sort_order, superset_group, rest_timer_seconds, notes)
- `workout_sets` - individual sets (workout_exercise_id, set_number, weight_kg, reps, rpe, set_type, duration_seconds, rest_seconds, is_to_failure, completed, completed_at)
- `routines` - reusable workout templates (user_id, name, last_used_at, use_count, created_at, updated_at)
- `routine_exercises` - exercises within a routine (routine_id, exercise_id, sort_order, rest_timer_seconds, notes)
- `routine_sets` - target sets within a routine exercise (routine_exercise_id, set_number, target_reps, set_type)
- RAG tables: `papers`, `chunks` (pgvector HNSW), `chat_sessions`, `chat_messages`, `rag_traces`

## Commands

```bash
# Install dependencies
pnpm install

# Run both frontend and backend
pnpm dev

# Run individually
pnpm dev:web    # Frontend
pnpm dev:api    # Backend (needs venv activated)

# Backend setup
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
cd apps/api && pytest tests/ -v

# Ingest a single paper
cd apps/api && python -m scripts.ingest_paper --pdf papers/example.pdf --title "..." --authors "..." --year 2021 --category nutrition --license CC-BY

# Batch ingest from manifest
cd apps/api && python -m scripts.ingest_batch

# RAG evaluation
cd apps/api && python -m scripts.evaluate_rag --dry-run          # Preview call count
cd apps/api && python -m scripts.evaluate_rag --combined --verbose  # Run eval (combined mode)
cd apps/api && python -m scripts.evaluate_rag --output results/baseline.json  # Save report

# RAG evaluation tests
cd apps/api && pytest tests/eval/ -m eval -v
```

## Environment Variables

**Frontend (`apps/web/.env`):**
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`
- `VITE_API_URL` (default: http://localhost:8000)

**Backend (`apps/api/.env`):**
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `VOYAGE_API_KEY` — required for RAG embedding (Voyage AI)
- `GOOGLE_API_KEY` — required for RAG generation (Gemini)
- Optional with defaults: `EMBEDDING_MODEL` (voyage-4-large), `EMBEDDING_DIMENSIONS` (1024), `EMBEDDING_BATCH_SIZE` (200), `LLM_PROVIDER` (google), `LLM_MODEL` (gemini-2.5-flash), `CHUNK_SIZE` (800 tokens — passed as ~3200 chars to splitter), `CHUNK_OVERLAP` (200 chars), `RAG_TOP_K` (5), `RAG_SIMILARITY_THRESHOLD` (0.3)

## Current Status
- Auth flow working with Supabase
- Onboarding flow implemented (4-step profile setup)
- Dashboard with 5-tab sidebar navigation (Home, Workouts, Analysis, Chat, Profile)
- RAG Phases 1-8 complete — full pipeline from PDF ingestion to frontend chat UI + automated evaluation
- Corpus: 195 papers (~8284 chunks), all CC-BY. Post-expansion eval: 4.57/5
- Skill: `/ingest-papers` for corpus expansion workflow
- **Phase 3 (Workout Logging) — complete**
  - Migrations 011-014: 9 workout/routine tables with RLS (011 base tables, 012 fixes, 013 added muscle groups, 014 routines)
  - Backend: 20 endpoints on `/workouts` + 8 endpoints on `/routines`
  - Seed data: 386 exercises, 36 muscle groups, 2,890 muscle activation mappings
  - Frontend: Full Liftoff-style workout modal (useReducer state, optimistic updates, debounced sync)
  - History screen with filters, exercise library, routines/templates

## Onboarding Flow
- **Route**: `/onboarding` (after login, before dashboard access)
- **Steps**: Basic Info → Physical Stats → Fitness Profile → Schedule
- **Route Guard**: `<OnboardingRoute>` redirects incomplete profiles to onboarding
- **API**: `GET /profile/me`, `POST /profile/onboarding`

## Dashboard Navigation
- **Layout**: `DashboardLayout` with sidebar (desktop) containing 5 tabs
- **Routes**: Nested under `/dashboard` with `<Outlet />`
  - `/dashboard` → redirects to `/dashboard/home`
  - `/dashboard/home` → HomeDashboardScreen (welcome, quick stats)
  - `/dashboard/workouts` → WorkoutsScreen (logging + history + library/routines tiles)
  - `/dashboard/workouts/exercises` → ExerciseLibraryScreen (browse + detail modal)
  - `/dashboard/workouts/routines` → RoutinesScreen (create/edit/manage routine templates)
  - `/dashboard/workouts/history` → WorkoutHistoryScreen (paginated + filtered)
  - `/dashboard/analysis` → AnalysisScreen (AI trends, charts)
  - `/dashboard/chat` → ChatScreen (AI assistant)
  - `/dashboard/profile` → ProfileScreen (user settings)
- **Icons**: Using `lucide-react` (Home, Dumbbell, BarChart3, MessageCircle, User)

## Next Steps

The authoritative build order is in `context/ROADMAP.md` decision #18. Summary:

1. **Phase 1 — Eval baseline & cross-validation** (~3-4 days): judge JSON retry + fresh baseline rerun + Anthropic provider + Run A (custom + Haiku 4.5) + Ragas integration + Run B + analysis writeup
2. **Phase 2 — Retrieval improvements** (~3-4 days): per-paper diversification → top_k bump → cross-encoder reranking (FlashRank) → re-eval against target chunks → noise cleanup
3. **Phase 3 — v2 agentic RAG with LangGraph**: router (literature / workout data / exercise info branches) + judge node + retry — see `context/FUTURE-PLANS.md` for 10 open design questions

Lower priority / deferred: Phase 3 remaining items (exercise video URLs, superset UI, set type selector), Phase 4 progress tracking visualizations, Phase 6 flame visualization. These don't show up in interview demos of the RAG chatbot.


## AI Chatbot (Exercise Science RAG)   
                                                                                                                                                                                                                   
  ### Claude Instructions for AI Features
  - Act as a teacher, explain concepts at beginner level
  - Point out weaknesses and anti-patterns
  - Prefers to learn properly as a skill, not just follow recipes

  ### Goal
  The `features/chat` route will be an AI chatbot that:
  - v1: Answers exercise science questions with cited research literature (Simple RAG)
  - v2: Also analyzes user workout data from this app (volume, PRs, trends) using Agentic RAG with a router

  ### Architecture Decisions
  - v1: Simple RAG — papers only, no agents needed
  - v2: Agentic RAG with router (literature path + workout data path)
  - Categories (nutrition, hypertrophy, strength) handled via metadata tags, not separate agents
  - Vector search naturally handles topic matching; metadata enables filtering + citations

  ### Implementation Details

  Detailed RAG implementation walkthroughs (ingestion pipeline, retrieval pipeline, metadata schema, prompt templates, Phase-by-phase gotchas) moved to `context/archive/IMPLEMENTATION-HISTORY.md`. Load that file only when working on a specific subsystem or debugging something. The summary below is sufficient for catching up.

  **RAG v1 implementation summary**: PDF papers → IBM Docling extraction (with pymupdf bbox header detection) → section-aware chunking (RecursiveCharacterTextSplitter, 3200 chars ~800 tokens, 200 char overlap) → Voyage embeddings (`voyage-4-large`, 1024 dims, `document` for ingestion / `query` for retrieval) → pgvector storage (HNSW index). At query time: embed query → match_chunks RPC (cosine similarity, top-k) → format with `[Author, Year, p. X]` citation prompt → Gemini 2.5 Flash generates (temperature 0.3, max_tokens 8192). License-aware (all CC-BY). Streaming via SSE.

  **Eval metrics (5 core)**: contextual relevancy, contextual recall, contextual precision, answer relevancy, faithfulness. Custom LLM-as-judge (primary, hand-written prompts). Cross-validated against Ragas (committed in ROADMAP Phase 1).

  **v2 architecture summary**: LangGraph router classifies intent → routes to one or more of three branches (literature/workout-data/exercise-info) → judge node verifies → retry or return. Full architecture + 10 open design questions in `context/FUTURE-PLANS.md`.

  ## Build vs Buy Philosophy
  ------------------------

  This project is a *selective* build-from-primitives approach, not "reject all frameworks." The decision framework:

  **Built custom where the value is in understanding or in tight fit:**
  - v1 RAG orchestration (retrieve + generate as ~50 lines of direct httpx; no LangChain abstractions to hide what's happening)
  - LLM-as-judge eval (5 metrics, hand-written prompts; the only way to understand RAG quality measurement is to write the judge yourself)
  - Trace storage schema (rag_traces table tied to specific latency split + grounded flag + rewritten query — built to my system's failure modes, not generic)
  - Ingestion pipeline (Docling + pymupdf hybrid header detection — domain-specific, not standard)

  **Used frameworks where they solve real problems:**
  - LangChain text splitters (chunking is solved; reinventing it would teach nothing new)
  - LangGraph for v2 agentic flow (4-5 node state machine; matches day-job stack; abstractions earn their keep at this complexity)
  - LangSmith for trace UI (building one would be wasted effort; native LangGraph integration is free; screenshot-worthy)
  - Ragas for eval cross-validation (canonical reference implementation; the right tool for "validate my custom judge against the industry standard")

  **The narrative this supports:** every component choice has a defensible reason. Custom where understanding matters or where the system needs a tight fit. Frameworks where they're battle-tested and reinventing would just be reinventing. This is the kind of decision-making that lands a 1-YOE engineer at mid-level (Junior AI Engineer at Series A/B AI-first startups, or Software Engineer doing AI work at larger companies) — it signals trajectory, not "senior already."