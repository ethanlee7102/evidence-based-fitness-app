# Flame Fitness App - Development Plan

## Overview

A workout logging app with AI-powered trend analysis. Users log workouts, track progress, and receive insights to optimize their training. The "Flame" visualization evolves based on consistency and progress.

---

## Core Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Workout Logging** | Log exercises, sets, reps, weight | ⏳ Next |
| **Progress Tracking** | Visualize strength improvements | ⏳ Planned |
| **AI Insights** | Trend analysis and recommendations | ⏳ Planned |
| **Consistency** | Workout frequency, streaks | ⏳ Planned |
---

## Technical Stack

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│         React + TypeScript + Tailwind CSS               │
│                  Deployed on Vercel                     │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      Backend                            │
│                  Python + FastAPI                       │
│              Deployed on Railway/Render                 │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      Supabase                           │
│         PostgreSQL + Auth + Storage                     │
└─────────────────────────────────────────────────────────┘
```

---

## Folder Structure

### Root (Monorepo)

```
flame-fitness/
├── apps/
│   ├── web/                      # React frontend
│   └── api/                      # Python backend
│
├── packages/
│   └── shared/                   # Shared TypeScript types
│       ├── types/
│       │   ├── user.ts
│       │   └── index.ts
│       └── package.json
│
├── supabase/
│   └── migrations/               # Database migrations
│
├── .gitignore
├── package.json                  # Root pnpm workspace config
├── pnpm-workspace.yaml
├── CLAUDE.md
├── PLAN.md
└── README.md
```

### Frontend (`apps/web/`)

```
apps/web/
├── src/
│   ├── features/
│   │   ├── auth/                 # Authentication
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── screens/
│   │   │   ├── services/
│   │   │   └── index.ts
│   │   │
│   │   ├── home/                 # Landing page + Dashboard home
│   │   │   ├── components/
│   │   │   │   ├── FlameVisualization.tsx
│   │   │   │   ├── QuickActions.tsx
│   │   │   │   └── index.ts
│   │   │   ├── screens/
│   │   │   │   ├── HomeScreen.tsx        # Landing page (/)
│   │   │   │   └── HomeDashboardScreen.tsx # Dashboard home (/dashboard/home)
│   │   │   └── index.ts
│   │   │
│   │   ├── dashboard/            # Layout shell for dashboard
│   │   │   ├── components/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── DashboardLayout.tsx
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts      # NAV_ITEMS definition
│   │   │   └── index.ts
│   │   │
│   │   ├── workouts/             # Workout logging + history
│   │   │   ├── components/
│   │   │   ├── screens/
│   │   │   │   └── WorkoutsScreen.tsx
│   │   │   └── index.ts
│   │   │
│   │   ├── analysis/             # AI trends, charts
│   │   │   ├── components/
│   │   │   ├── screens/
│   │   │   │   └── AnalysisScreen.tsx
│   │   │   └── index.ts
│   │   │
│   │   ├── chat/                 # AI assistant
│   │   │   ├── components/
│   │   │   ├── screens/
│   │   │   │   └── ChatScreen.tsx
│   │   │   └── index.ts
│   │   │
│   │   ├── profile/              # User settings
│   │   │   ├── components/
│   │   │   ├── screens/
│   │   │   │   └── ProfileScreen.tsx
│   │   │   └── index.ts
│   │   │
│   │   └── index.ts
│   │
│   ├── shared/
│   │   ├── components/           # Button, Card, Loading, Layout
│   │   └── hooks/
│   │
│   ├── navigation/
│   │   ├── AppRouter.tsx         # Nested routes for dashboard
│   │   ├── ProtectedRoute.tsx
│   │   ├── OnboardingRoute.tsx
│   │   └── index.ts
│   │
│   └── lib/
│       ├── supabase.ts
│       └── api.ts
│
├── public/
├── package.json
└── vite.config.ts
```

### Backend (`apps/api/`)

```
apps/api/
├── src/
│   ├── api/                       # Route handlers
│   │   ├── health.py              # Health check endpoint
│   │   └── router.py              # Combines all routers
│   │
│   ├── core/                      # Business logic (empty, ready)
│   │
│   ├── schema/                    # Pydantic models
│   │
│   ├── service/
│   │   ├── db_service.py          # Database operations
│   │   └── storage_service.py     # Supabase storage
│   │
│   └── utils/
│       ├── config.py
│       ├── auth.py
│       └── logging.py
│
├── tests/
│   └── conftest.py
│
├── app.py                         # FastAPI entry point
├── db.py                          # Database connection
└── requirements.txt
```

---

## Database Schema

### Current (Active)

```sql
-- Users (extends Supabase Auth)
create table profiles (
  id uuid references auth.users primary key,
  username text unique,
  created_at timestamp with time zone default now()
);
```

### Planned (Workout Logger)

```sql
-- Exercises library
create table exercises (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  muscle_group text,
  created_at timestamp with time zone default now()
);

-- Workout sessions
create table workouts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  date date not null default current_date,
  notes text,
  created_at timestamp with time zone default now()
);

-- Individual sets within a workout
create table workout_sets (
  id uuid primary key default gen_random_uuid(),
  workout_id uuid references workouts(id) on delete cascade,
  exercise_id uuid references exercises(id),
  set_number integer not null,
  reps integer,
  weight numeric,
  created_at timestamp with time zone default now()
);

-- Row Level Security
alter table workouts enable row level security;
alter table workout_sets enable row level security;

create policy "Users can manage own workouts" on workouts
  for all using (auth.uid() = user_id);
create policy "Users can manage own sets" on workout_sets
  for all using (workout_id in (select id from workouts where user_id = auth.uid()));
```

---

## Development Phases

### Phase 1: Project Setup ✅
- [x] Initialize monorepo with pnpm workspaces
- [x] Set up React frontend (Vite + TypeScript + Tailwind)
- [x] Set up Python backend (FastAPI)
- [x] Create Supabase project
- [x] Configure environment variables
- [x] Implement Supabase auth

### Phase 2: CV Analyzer (REMOVED) ~~✅~~
- ~~Pose estimation with MMPose/RTMPose~~
- ~~Deadlift, Squat, Bench analyzers~~
- **Removed** - Pivoted to workout logger

### Phase 3: Dashboard & Workout Logging ⏳ CURRENT
- [x] Create Dashboard with 5-tab sidebar navigation
- [x] Create feature folders (workouts, analysis, chat, profile)
- [ ] Create database schema (exercises, workouts, workout_sets)
- [ ] Build workout logging API endpoints
- [ ] Build workout logging UI in WorkoutsScreen
- [ ] Add exercise selection
- [ ] Log sets with reps/weight

### Phase 4: Progress Tracking
- [ ] Historical workout view
- [ ] Exercise-specific progress charts
- [ ] Personal records tracking
- [ ] Volume over time

### Phase 5: AI Insights
- [ ] Integrate AI for trend analysis
- [ ] Training recommendations
- [ ] Recovery insights
- [ ] Consistency scoring

### Phase 6: Polish
- [ ] Flame visualization based on consistency
- [ ] Streak tracking
- [ ] Mobile-responsive improvements
- [ ] Error handling & edge cases

---

## Deployment

| Service | Platform | Notes |
|---------|----------|-------|
| Frontend | Vercel | Auto-deploy from main branch |
| Backend | Railway or Render | Python FastAPI |
| Database | Supabase | PostgreSQL + Auth + Storage |

---

## Dashboard Navigation

```
/dashboard                → redirects to /dashboard/home
/dashboard/home           → HomeDashboardScreen (welcome, quick stats)
/dashboard/workouts       → WorkoutsScreen (logging + history)
/dashboard/analysis       → AnalysisScreen (AI trends, charts)
/dashboard/chat           → ChatScreen (AI assistant)
/dashboard/profile        → ProfileScreen (user settings)
```

**Sidebar navigation** with lucide-react icons:
- Home, Workouts, Analysis, Chat, Profile
- Sign out button at bottom

---

## Next Steps

1. **Create workout database migration**
2. **Build workout logging API endpoints**
3. **Build workout logging UI in WorkoutsScreen**
4. **Implement workout history view**

---

## v1 RAG Chatbot Implementation Plan

### Context

Building an exercise science RAG chatbot for Flame Fitness at `/dashboard/chat`. Users ask questions and get answers with cited research papers. This is a learning project (no LangChain orchestration, no LangSmith — fully custom) designed to demonstrate deep RAG understanding.

### Tech Stack Decisions
- **Vector DB**: pgvector in Supabase (already using PostgreSQL)
- **Embedding**: OpenAI `text-embedding-3-large` (3072 dims)
- **LLM**: Gemini 2.0 Flash (cheapest, swappable via env var + wrapper)
- **Chunking**: Section-aware with fixed-size fallback (standalone `langchain_text_splitters`)
- **Observability**: Custom TraceLogger (stores traces in Supabase)
- **Eval**: Manual during dev, automated eval pipeline at end of v1
- **Streaming**: SSE from FastAPI
- **Memory**: Last N messages per session
- **Citations**: Inline `[Author, Year]` with paper DOI/URL links
- **Corpus**: 50-100 papers for v1 (manual collection)

---

### Phase 1: Database Schema
**Status**: ⏳ Next

Create `supabase/migrations/005_rag_tables.sql`:
- Enable pgvector extension
- `papers` table — title, authors, year, journal, doi, url, category, study_type, content_hash (unique, for dedup), total_chunks, embedding_model, ingested_at
- `chunks` table — paper_id (FK), chunk_index, text, section, embedding VECTOR(3072), chunking_method
- HNSW index on chunks.embedding for cosine similarity
- `chat_sessions` table — user_id (FK), title, created_at, updated_at
- `chat_messages` table — session_id (FK), role, content, citations (JSONB), created_at
- `rag_traces` table — session_id, message_id, user_id, query, retrieved_chunks (JSONB), prompt_sent, llm_response, timing data, error
- RLS policies: users own their sessions/messages/traces; papers/chunks are public-read
- `match_chunks` RPC function — takes query embedding, returns top-k chunks with paper metadata

**Verify**: Run migration, confirm tables + vector extension exist.

---

### Phase 2: Backend Infrastructure
**Status**: ⏳ Planned

**2A. Config** — Add RAG env vars to `apps/api/src/utils/config.py`
- OPENAI_API_KEY, GOOGLE_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, LLM_PROVIDER, LLM_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, RAG_TOP_K, RAG_SIMILARITY_THRESHOLD

**2B. Embedding Provider** — `apps/api/src/core/embedding_provider.py`
- `embed_texts(texts)` — batch embedding via OpenAI REST API (httpx, async)
- `embed_query(query)` — single query embedding
- Direct HTTP calls, no SDK

**2C. LLM Provider** — `apps/api/src/core/llm_provider.py`
- `generate(prompt, system)` — full response (for eval)
- `generate_stream(prompt, system)` — streaming (for chat)
- Provider switch via env var (google/openai)
- Direct HTTP calls via httpx

**2D. Dependencies** — Add `pymupdf>=1.24.0`, `langchain-text-splitters>=0.2.0` to requirements.txt

**Verify**: `embed_query("test")` returns 3072-dim vector.

---

### Phase 3: Ingestion Pipeline
**Status**: ⏳ Planned

**3A. Schemas** — `apps/api/src/schema/rag.py`
- PaperMetadata, PaperResponse, ChunkResponse, ChatMessageRequest, ChatMessageResponse, ChatSessionResponse

**3B. Ingestion Core** — `apps/api/src/core/ingestion.py`
- `extract_sections(pdf_path)` — pymupdf font analysis to detect section headers
- `chunk_with_sections(sections)` — RecursiveCharacterTextSplitter within sections
- `ingest_paper(pdf_path, metadata)` — full pipeline: load → hash → dedup check → chunk → embed → store

**3C. CLI Scripts** — `apps/api/scripts/ingest_paper.py` + `ingest_batch.py`

**3D. Papers Directory** — `apps/api/papers/` + `manifest.json`

**Verify**: Ingest one test PDF. Re-run = skipped (dedup).

---

### Phase 4: Retrieval Pipeline
**Status**: ⏳ Planned

Create `apps/api/src/core/retrieval.py`:
- `retrieve_chunks(query, top_k, category, threshold)` — embed query → call `match_chunks` RPC → return chunks with paper metadata and similarity scores

**Verify**: `retrieve_chunks("What rep range is best for hypertrophy?")` returns relevant chunks.

---

### Phase 5: RAG Generation Pipeline
**Status**: ⏳ Planned

Create `apps/api/src/core/rag_pipeline.py`:
- `build_rag_prompt(query, chunks, history)` — format sources with `[Author, Year]`
- `rag_query(query, history, top_k, category)` — non-streaming (for eval)
- `rag_query_stream(query, history, top_k, category)` — streaming (for chat)
- System prompt: cite sources, "I don't know" when insufficient, explain at beginner level

**Verify**: `rag_query("What rep range is best for hypertrophy?")` returns cited answer.

---

### Phase 6: Chat API + TraceLogger
**Status**: ⏳ Planned

**6A. TraceLogger** — `apps/api/src/core/trace_logger.py`
- Records query, chunks, prompt, response, timing, errors → stores in `rag_traces`

**6B. Chat Service** — `apps/api/src/service/chat_service.py`
- Session CRUD, message history, auto-title from first message

**6C. Chat Route** — `apps/api/src/api/chat.py`
- `GET /chat/sessions`, `GET /chat/sessions/{id}/messages`
- `POST /chat/message` — SSE streaming endpoint
- `DELETE /chat/sessions/{id}`
- SSE events: `citations`, `session`, `data`, `done`, `error`

**6D. Traces Route** — `apps/api/src/api/traces.py`
- `GET /chat/traces` — debugging endpoint

**Verify**: curl POST to `/chat/message`, see SSE events streaming.

---

### Phase 7: Frontend Chat UI
**Status**: ⏳ Planned

**7A. Types** — `features/chat/types/index.ts`
**7B. Service** — `features/chat/services/chatService.ts` (SSE parsing)
**7C. Hook** — `features/chat/hooks/useChat.ts` (state management)
**7D. Components**:
- ChatInput, ChatMessageBubble, ChatMessageList, SessionSidebar, CitationCard
**7E. ChatScreen rewrite** — SessionSidebar + Chat area with streaming

**Verify**: Navigate to `/dashboard/chat`, send message, see streaming + citations.

---

### Phase 8: Automated Evaluation Pipeline
**Status**: ⏳ Planned

**8A. Test Dataset** — `apps/api/tests/eval/test_dataset.json` (30-50 Q&A pairs)
**8B. Eval Script** — `apps/api/scripts/evaluate_rag.py`
- 5 metrics via LLM-as-judge: Contextual Relevancy, Recall, Precision, Answer Relevancy, Faithfulness
**8C. Pytest Integration** — `apps/api/tests/eval/test_rag_pipeline.py`

**Verify**: Run eval script, review metrics, iterate.

---

### File Manifest

**New Files**:
```
supabase/migrations/005_rag_tables.sql
apps/api/src/core/embedding_provider.py
apps/api/src/core/llm_provider.py
apps/api/src/core/ingestion.py
apps/api/src/core/retrieval.py
apps/api/src/core/rag_pipeline.py
apps/api/src/core/trace_logger.py
apps/api/src/schema/rag.py
apps/api/src/service/chat_service.py
apps/api/src/api/chat.py
apps/api/src/api/traces.py
apps/api/scripts/ingest_paper.py
apps/api/scripts/ingest_batch.py
apps/api/papers/manifest.json
apps/api/tests/eval/test_dataset.json
apps/api/tests/eval/test_rag_pipeline.py
apps/api/scripts/evaluate_rag.py
apps/web/src/features/chat/types/index.ts
apps/web/src/features/chat/services/chatService.ts
apps/web/src/features/chat/hooks/useChat.ts
apps/web/src/features/chat/components/ChatInput.tsx
apps/web/src/features/chat/components/ChatMessageBubble.tsx
apps/web/src/features/chat/components/ChatMessageList.tsx
apps/web/src/features/chat/components/SessionSidebar.tsx
apps/web/src/features/chat/components/CitationCard.tsx
```

**Modified Files**:
```
apps/api/src/utils/config.py          — add RAG env vars
apps/api/src/api/router.py            — register chat + traces routers
apps/api/requirements.txt             — add pymupdf, langchain-text-splitters
apps/api/.env                         — add API keys + config
apps/web/src/features/chat/screens/ChatScreen.tsx    — full rewrite
apps/web/src/features/chat/components/index.ts       — export new components
apps/web/src/features/chat/index.ts                  — updated exports
```
