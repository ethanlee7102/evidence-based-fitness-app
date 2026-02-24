### Implementation Plan
Refer to `PLAN.md` for the full implementation plan, phase statuses, and file manifest. Update phase statuses in PLAN.md as work is completed.

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
Flame Fitness is a workout logging app with AI-powered trend analysis. Users log workouts, track progress, and receive insights to optimize their training.

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
│   │       │   ├── chat/         # AI assistant
│   │       │   ├── profile/      # User settings
│   │       │   └── onboarding/   # Multi-step user onboarding
│   │       ├── shared/           # Shared UI (Button, Card, Loading, Layout)
│   │       ├── navigation/       # AppRouter, ProtectedRoute, OnboardingRoute
│   │       └── lib/              # supabase.ts, api.ts
│   │
│   └── api/                      # Python backend (port 8000)
│       ├── src/
│       │   ├── api/              # Route handlers (health, profile)
│       │   ├── core/             # Business logic (empty, ready for workout features)
│       │   ├── schema/           # Pydantic models (profile.py)
│       │   ├── service/          # db_service, storage_service
│       │   ├── utils/            # config, auth, logging
│       │   └── db.py             # Supabase client
│       ├── tests/
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
- **Embedding**: `src/core/embedding_provider.py` — `embed_texts()` and `embed_query()` via Voyage AI
- **LLM**: `src/core/llm_provider.py` — `generate()` and `generate_stream()` via Gemini. Both accept `temperature` and `max_tokens` params.

### Database Tables
- `profiles` - extends Supabase auth.users with onboarding fields:
  - `display_name`, `birthday`, `gender`, `height_cm`, `weight_kg`
  - `units_preference`, `experience_level`, `goal`
  - `workout_days_per_week`, `preferred_days`, `injuries_limitations`
  - `onboarding_completed`, `onboarding_completed_at`

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
- Optional with defaults: `EMBEDDING_MODEL` (voyage-4-large), `EMBEDDING_DIMENSIONS` (1024), `EMBEDDING_BATCH_SIZE` (200), `LLM_PROVIDER` (google), `LLM_MODEL` (gemini-2.0-flash), `CHUNK_SIZE` (800), `CHUNK_OVERLAP` (200), `RAG_TOP_K` (5), `RAG_SIMILARITY_THRESHOLD` (0.3)

## Current Status
- Auth flow working with Supabase
- Onboarding flow implemented (4-step profile setup)
- Dashboard with 5-tab sidebar navigation (Home, Workouts, Analysis, Chat, Profile)
- Core infrastructure in place
- RAG Phase 1 (database schema) complete — pgvector tables + RPC running in Supabase
- RAG Phase 2 (backend infrastructure) complete — embedding provider, LLM provider, config all working

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
  - `/dashboard/workouts` → WorkoutsScreen (logging + history)
  - `/dashboard/analysis` → AnalysisScreen (AI trends, charts)
  - `/dashboard/chat` → ChatScreen (AI assistant)
  - `/dashboard/profile` → ProfileScreen (user settings)
- **Icons**: Using `lucide-react` (Home, Dumbbell, BarChart3, MessageCircle, User)

## Next Steps (Workout Logger)
Features to implement:
1. **Workout logging** - Log exercises, sets, reps, weight
2. **Progress tracking** - Historical data visualization
3. **AI insights** - Trend analysis and recommendations

Database tables needed:
- `workouts` - workout sessions (user_id, date, notes)
- `exercises` - exercise definitions (name, muscle_group)
- `workout_sets` - individual sets (workout_id, exercise_id, reps, weight)


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

  ### Learning Progress
  - [x] Big picture overview of RAG
  - [x] Ingestion pipeline walkthrough (with code snippets from Kruiz)
  - [x] Weaknesses in reference codebase identified (9 major ones)
  - [x] Simple RAG vs Agentic RAG distinction
  - [x] Video: RAG end-to-end (ingestion pipeline, retrieval, agentic RAG)
  - [x] Embeddings & vector search deep dive
  - [x] Chunking strategies advanced
  - [x] Vector databases comparison
  - [x] Retrieval & re-ranking
  - [ ] Prompt engineering for citations — learn by doing
  - [x] RAG evaluation (DeepEval/RAGAS metrics)
  - [ ] Agents & routing — deferred to v2

  ### Key Kruiz Weaknesses to Avoid
  1. No chunking strategy — need section-aware chunking (RecursiveCharacterTextSplitter within sections, with overlap)
  2. Missing embedding pipeline — build end-to-end: chunk → embed → store
  3. Metadata discarded at retrieval — keep full metadata for citations
  4. No re-ranking — add cross-encoder for v2
  5. Silent error handling — raise errors, don't return empty strings
  6. Raw SQL everywhere — use pgvector in Supabase with RPC functions
  7. Synchronous embedding calls — use async
  8. No embedding versioning — track model version
  9. Delete-and-reinsert pattern — use upserts
  10. Without systematic evaluation, you have no way to know:
    - Did changing your chunk size make retrieval better or worse?
    - Is your embedding model good enough for scientific text?
    - What's your hallucination rate?

  ## RAG Chatbot Implementation Context

  ### What We're Building

  An exercise science chatbot that lives at `/features/chat` in the Flame Fitness app.                                                                                                                            
  Users ask questions like "What rep range is best for hypertrophy?" and get answers                                                                                                                               
  with cited research papers (author, year, journal).

  ### v1 Architecture (Simple RAG — build this first)

  PDF papers → Load → Chunk (with overlap) → Embed → Store in vector DB (with metadata)

  User question → Embed → Vector search → Top-k chunks returned
  → Stuff into prompt with citation instructions → LLM generates cited answer

  #### Ingestion Pipeline (offline, run once per paper)
  1. Load PDFs using pymupdf (fitz) with font analysis to detect section headers
  2. Section-aware chunking — RecursiveCharacterTextSplitter within sections (never across), with fixed-size fallback if no headers detected
  3. Attach metadata to every chunk: title, authors, year, journal, DOI, category, section, chunk_index
  4. Embed each chunk using Voyage AI `voyage-4-large` (1024-dim), `input_type: "document"`, batched in groups of ~200
  5. Store chunk text + embedding + metadata in pgvector (Supabase)
  6. SHA-256 content hash for deduplication (skip re-processing unchanged papers)

  #### Retrieval Pipeline (online, every user query)
  1. Embed the user's question with the SAME embedding model used for ingestion, `input_type: "query"`
  2. Vector similarity search (cosine distance) to find top-k most relevant chunks
  3. Return chunks WITH full metadata (needed for citations)
  4. Format into prompt: "Answer using ONLY these sources. Cite as [Author, Year]."
  5. LLM generates answer with citations
  6. Handle "I don't know" — if no relevant chunks found, say so instead of hallucinating

  #### Key Decisions
  - ONE vector database (pgvector in Supabase), not separate DBs per category
  - Categories (nutrition, hypertrophy, strength) = metadata tags, not separate collections
  - Vector search naturally handles topic matching across categories
  - Direct API calls via httpx — no LangChain orchestration (only `langchain_text_splitters` standalone for chunking)
  - Use async for embedding calls
  - Voyage AI `input_type` param: `"document"` for ingestion, `"query"` for retrieval (improves retrieval quality)
  - Batch embedding limit: ~200 chunks per call (120K token limit for voyage-4-large)
  - LLM provider swappable via env var (Gemini 2.0 Flash default, OpenAI as alternative)
  - Gemini auth: API key as query param (not Bearer header). Endpoint: `generativelanguage.googleapis.com/v1beta/models/{model}`
  - System prompt via `system_instruction` field (separate from `contents` array)
  - Two SSE hops for streaming: Gemini → backend (Gemini SSE) → browser (our SSE endpoint)
  - `generate()` for eval (non-streaming, full response), `generate_stream()` for chat UI (streaming, real-time typing)
  - Shared httpx AsyncClient per provider (module-level, cleaned up via FastAPI `lifespan` hook)

  #### Metadata Schema Per Chunk
  ```python
  {
      "text": "the actual chunk text...",
      "metadata": {
          "title": "Hypertrophic Effects of Rep Ranges",
          "authors": "Schoenfeld et al.",
          "year": 2017,
          "journal": "Journal of Strength & Conditioning",
          "doi": "10.1234/example",
          "category": "hypertrophy",  # or "nutrition", "strength", etc.
          "study_type": "meta-analysis",  # or "RCT", "review", etc.
          "section": "Results",
          "chunk_index": 3,
          "total_chunks": 12
      }
  }

  Prompt Template Pattern

  Answer the following question using ONLY the provided sources.
  For every claim, cite the source as [Author, Year].
  If the sources don't contain enough information, say
  "I don't have enough research to answer this confidently."
  Do NOT make up information.

  Sources:
  [1] Schoenfeld et al., 2017 (Journal of Strength & Conditioning):
  "8-12 reps per set at 60-80% 1RM maximizes hypertrophic response..."

  [2] Krieger, 2010 (Journal of Sports Medicine):
  "Multiple sets produced 40% greater hypertrophy than single sets..."

  Question: {user_question}

  v2 Architecture (Agentic RAG — build after v1 works)

  User question
        │
        ▼
     Router (LLM classifies intent)
        │
        ├── "literature question"  →  RAG Pipeline (from v1)
        │
        ├── "workout data question" →  SQL query against workout tables
        │                              (workouts, exercises, workout_sets)
        │
        └── "both" →  Run both, combine
                       ("Research says 10-20 sets/week. You're doing 14.")

  - Literature = unstructured text → vector search (same as v1)
  - Workout data = structured numbers → SQL queries (different retrieval method)
  - This is why a router is justified — fundamentally different data types

  RAG Evaluation (How to Know It's Working)

  5 core metrics to measure:
  - Contextual Relevancy: Are retrieved chunks relevant to the question?
  - Contextual Recall: Do retrieved chunks contain all needed info?
  - Contextual Precision: Are more relevant chunks ranked higher?
  - Answer Relevancy: Does the answer address the actual question?
  - Faithfulness: Does the answer only use info from retrieved chunks (no hallucination)?

  Custom eval pipeline with LLM-as-judge (no DeepEval/RAGAS dependency — fully custom for learning).

  Tech Stack (Finalized)

  - Backend: FastAPI (already in Flame Fitness)
  - Vector DB: pgvector in Supabase (already using PostgreSQL)
  - Embedding model: Voyage AI `voyage-4-large` (1024 dims)
  - LLM: Gemini 2.0 Flash (cheapest, swappable via env var + wrapper)
  - PDF loading: pymupdf (fitz)
  - Chunking: `langchain_text_splitters` (standalone, no LangChain orchestration)
  - Observability: Custom TraceLogger → Supabase `rag_traces` table
  - Streaming: SSE from FastAPI
  - No LangChain orchestration, no LangSmith — fully custom for learning