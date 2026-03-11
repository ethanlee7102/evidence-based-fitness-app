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
- **Embedding**: Voyage AI `voyage-4-large` (1024 dims)
- **LLM**: Gemini 2.0 Flash (cheapest, swappable via env var + wrapper)
- **Chunking**: Section-aware with fixed-size fallback (standalone `langchain_text_splitters`)
- **Observability**: Custom TraceLogger (stores traces in Supabase)
- **Eval**: Manual during dev, automated eval pipeline at end of v1
- **Streaming**: SSE from FastAPI
- **Memory**: Last N messages per session
- **Citations**: Inline `[Author, Year]` with paper DOI/URL links
- **Corpus**: 50-100 papers for v1 (manual collection). Prefer CC-BY/CC0 from PMC Open Access Subset for commercial viability. Track license per paper.
- **Copyright strategy**: LLM synthesizes answers in own words, never displays verbatim chunks. Papers sourced from PMC Open Access (CC-BY preferred). License field enables filtering to commercially-safe corpus if needed.

---

### Phase 1: Database Schema
**Status**: ✅ Complete

Created `supabase/migrations/005_rag_tables.sql`:
- Enable pgvector extension
- `papers` table — title, authors, year, journal, doi, url, category, study_type, abstract, content_hash (unique, for dedup), total_chunks, embedding_model, license (CC license tracking for commercial filtering), ingested_at
- `chunks` table — paper_id (FK), chunk_index, text, section, page_start, page_end, token_count, embedding VECTOR(1024), chunking_method
- HNSW index on chunks.embedding for cosine similarity
- `chat_sessions` table — user_id (FK), title, created_at, updated_at
- `chat_messages` table — session_id (FK), role, content, citations (JSONB), created_at
- `rag_traces` table — session_id, message_id, user_id, query, retrieved_chunks (JSONB), prompt_sent, llm_response, timing data, error
- RLS policies: users own their sessions/messages/traces; papers/chunks are public-read
- `match_chunks` RPC function — takes query embedding VECTOR(1024), returns top-k chunks with paper metadata

Migration `006_add_paper_license.sql` adds `license` column (CC0, CC-BY, CC-BY-SA, CC-BY-ND, CC-BY-NC, CC-BY-NC-SA, CC-BY-NC-ND, other, unknown) with default `'unknown'`. Enables filtering corpus to commercially-usable papers only.

**Verify**: Run migration, confirm tables + vector extension exist.

---

### Phase 2: Backend Infrastructure
**Status**: ✅ Complete

**2A. Config** — `apps/api/src/utils/config.py`
- Added: VOYAGE_API_KEY, GOOGLE_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, EMBEDDING_BATCH_SIZE, LLM_PROVIDER, LLM_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, RAG_TOP_K, RAG_SIMILARITY_THRESHOLD
- Lazy validation — RAG keys only checked when providers are called

**2B. Embedding Provider** — `apps/api/src/core/embedding_provider.py`
- `embed_texts(texts)` — batch embedding, `input_type: "document"`, auto-batches ~200/call
- `embed_query(query)` — single query embedding, `input_type: "query"`
- Shared httpx AsyncClient with connection pooling

**2C. LLM Provider** — `apps/api/src/core/llm_provider.py`
- `generate(prompt, system, temperature=0.7, max_tokens=2048)` — non-streaming via `generateContent`
- `generate_stream(prompt, system, temperature=0.7, max_tokens=2048)` — SSE streaming via `streamGenerateContent`
- SSE parsing with debug logging on malformed lines
- Shared httpx AsyncClient with connection pooling

**2D. Dependencies** — Added `docling>=2.0.0`, `pymupdf>=1.24.0`, `langchain-text-splitters>=0.2.0`

**2E. Lifespan** — `app.py` updated with `lifespan` hook to clean up shared httpx clients on shutdown

**Verified**: `embed_query("test")` returns 1024-dim float vector ✅

---

### Phase 3: Ingestion Pipeline
**Status**: ✅ Complete

**3A. Schemas** — `apps/api/src/schema/rag.py`
- PaperMetadata (includes `license` field), PaperResponse, ChunkResponse
- Literal types for Category, License, StudyType matching DB CHECK constraints

**3B. Ingestion Core** — `apps/api/src/core/ingestion.py`
- `extract_sections(pdf_path)` — IBM Docling + pymupdf hybrid:
  - Docling (DocLayNet ML model) handles layout analysis, reading order, header detection, tables
  - pymupdf provides font size/bold via bounding box spatial matching for header hierarchy
  - Layered hierarchy: 1a) font size grouping, 1b) bold tiebreaker, 1c) ALL_CAPS tiebreaker, 2) text pattern fallback
  - Abstract detection: force-promotes "Abstract" headers to major regardless of font size; scans pre-header body text for "Abstract:" labels (MDPI papers where abstract is body text)
- Per-chunk page tracking via char-offset-to-page mapping
- Fallback: if <= 1 major header detected → single section with `section=None`
- `chunk_sections(sections)` — RecursiveCharacterTextSplitter within sections, chunk_size=3200 chars (~800 tokens), overlap=200 chars
- `compute_content_hash(pdf_path)` — SHA-256 of PDF bytes for dedup
- `ingest_paper(pdf_path, metadata)` — full pipeline: hash → dedup check → extract → chunk → embed → store. Delete paper row on error (try/except cleanup).
- Token counting: `len(text) / 4` stored in `chunks.token_count`

**3C. Retry Logic** — `apps/api/src/core/embedding_provider.py`
- Added retry to `embed_texts()`: 3 attempts on 429/500/503, exponential backoff 1s→2s→4s
- `embed_query()` unchanged (user-facing, fail fast)

**3D. CLI Scripts** — `apps/api/scripts/ingest_paper.py` + `ingest_batch.py`
- Run as modules: `cd apps/api && python -m scripts.ingest_paper`
- argparse for metadata, `asyncio.run()` for async ingestion

**3E. Papers Directory** — `apps/api/papers/` (PDFs gitignored) + `manifest.json` (checked in)

**3F. Test Script** — `apps/api/scripts/test_retrieval.py`
- CLI tool for testing retrieval: `python -m scripts.test_retrieval "query" --top-k 5 --category strength`
- Shows chunk metadata, similarity scores, and text previews

**Verified**:
- Ingested 9 papers (414 chunks): 3 hypertrophy, 1 nutrition, 5 strength
- Dedup working — re-run skips with "Paper already ingested"
- Abstract detected as own section in 7/9 papers (2 Frontiers papers have unlabeled abstracts)
- Retry logic triggered and worked on Voyage 429 (before adding payment method)
- Double-column handling verified — Docling ML model handles reading order correctly
- Header hierarchy verified across all 9 papers — proper font size, bold, and ALL_CAPS tiebreakers

---

### Phase 4: Retrieval Pipeline
**Status**: ✅ Complete

**4A. Migration** — `supabase/migrations/007_match_chunks_add_token_count.sql`
- `DROP FUNCTION` + `CREATE FUNCTION match_chunks(...)` — adds `token_count INTEGER` to RETURNS TABLE
- DROP required because PostgreSQL can't `CREATE OR REPLACE` when RETURNS TABLE columns change
- No table changes, no data loss — just replaces the function signature

**4B. Schema** — `apps/api/src/schema/rag.py`
- Added `token_count: Optional[int] = None` to `ChunkResponse`
- Added `RetrievalResult` dataclass (internal data carrier: chunks + query + timing)

**4C. Retrieval** — `apps/api/src/core/retrieval.py`
- `retrieve_chunks(query, top_k, category, similarity_threshold)` — async function
- Embeds query via `embed_query()`, calls `match_chunks` RPC, parses into `list[ChunkResponse]`
- Logs: query (truncated 80 chars), chunk count, similarity range, timing
- Returns `RetrievalResult` with chunks, query text, and elapsed time in ms

**Verified**: Run migration in Supabase SQL Editor, then test with Python REPL.

---

### Phase 5: RAG Generation Pipeline
**Status**: ✅ Complete

**5A. Multi-turn LLM support** — `apps/api/src/core/llm_provider.py`
- Added `messages: list[dict] | None` param to `_build_gemini_payload()`, `generate()`, `generate_stream()`
- Maps `"assistant"` → `"model"` for Gemini's role format
- Role alternation warning log (Gemini requires strict user/model alternation)

**5B. Schema types** — `apps/api/src/schema/rag.py`
- `ChatMessage` (TypedDict) — provider-agnostic history format
- `RAGResult` (dataclass) — non-streaming response for eval pipeline
- `StreamingRAGResult` (dataclass) — streaming response with lazy `.stream` async generator

**5C. RAG Pipeline** — `apps/api/src/core/rag_pipeline.py` (new)
- `SYSTEM_PROMPT` — exercise science assistant persona, citation rules, beginner-level
- `NO_CHUNKS_INSTRUCTION` — ungrounded answer disclaimer
- `REWRITE_PROMPT` — query rewriting template for follow-ups
- `_rewrite_query(query, history)` — conditional rewrite (skips if no history)
- `_build_sources_block(chunks)` — formats as `[Author, Year]` with page numbers
- `build_rag_prompt(query, chunks)` — sources + question (or no-chunks instruction)
- `rag_query()` — non-streaming, returns `RAGResult` (for eval)
- `rag_query_stream()` — streaming, returns `StreamingRAGResult` (for chat UI)
- Temperature hardcoded at 0.3, max_tokens 8192

**5D. Test Script** — `apps/api/scripts/test_rag_pipeline.py` (new)
- CLI: `python -m scripts.test_rag_pipeline "query" --stream --history '[...]' --category X --show-prompt`

**5E. Model Migration** — gemini-2.0-flash → gemini-2.5-flash
- Google zeroed free tier quotas for gemini-2.0-flash (deprecated, shutdown June 1, 2026)
- Updated default in `config.py` and `apps/api/.env`

**Verified**:
- Grounded query: cited answer with [Author, Year, p. X] format ✅
- Cross-paper citations: Schoenfeld 2021 + Bernardez-Vazquez 2022 + Androulakis-Korakakis 2021 ✅
- Streaming mode: tokens arrive incrementally ✅
- Follow-up with history: "Tell me more about the dosing" → rewritten to standalone query ✅
- Ungrounded query: grounded=False, disclaimer prefix, brief general answer ✅

---

### Phase 6: Chat API + TraceLogger
**Status**: ✅ Complete

**6A. Retrieval update** — `apps/api/src/core/retrieval.py`
- Split `embedding_time_ms` from total `retrieval_time_ms` with separate timer around `embed_query()`
- Added `embedding_time_ms` field to `RetrievalResult`, `RAGResult`, `StreamingRAGResult` dataclasses
- Threaded through `rag_pipeline.py` to both `rag_query()` and `rag_query_stream()`

**6B. Schema additions** — `apps/api/src/schema/rag.py`
- `ChatMessageRequest` — POST body: message (1-10000), session_id (optional), category (optional)
- `CitationPayload` — chunk_id, title, authors, year, category, similarity, journal, doi, section, pages
- `SessionResponse` — id, user_id, title, created_at, updated_at
- `MessageResponse` — id, session_id, role, content, citations (optional), created_at

**6C. TraceLogger** — `apps/api/src/core/trace_logger.py`
- `log_trace()` — fire-and-forget via `asyncio.create_task()`, never blocks response
- `_insert_trace()` — async DB insert, catches all exceptions internally
- `_chunks_to_json()` — full chunk text included for self-contained trace snapshots
- Maps to DB columns: `llm_response` (not `answer`), rounds timing to integers

**6D. Chat Service** — `apps/api/src/service/chat_service.py`
- Session CRUD: create, get, list (newest first), delete (FK cascade)
- Message CRUD: save (with optional citations JSONB), get (oldest first, limit 50)
- `get_recent_messages()` → `list[ChatMessage]` for RAG history (last 10, oldest first)
- `update_session_title()` and `update_session_timestamp()` (uses `datetime.now(timezone.utc)`)

**6E. Chat Route** — `apps/api/src/api/chat.py`
- `POST /chat/message` — main SSE streaming endpoint
  - Auto-creates session if no session_id provided
  - Fetches history BEFORE saving user message (avoids dedup)
  - SSE event flow: `session` (new only) → `citations` (always) → `data*` (text chunks) → `done`
  - On error: emits `error` event, logs trace, does NOT save partial answer
  - After stream: saves assistant message, logs trace (fire-and-forget), generates title if first message (fire-and-forget)
- `GET /chat/sessions` — list sessions (newest first)
- `GET /chat/sessions/{id}` — single session
- `GET /chat/sessions/{id}/messages` — message history (oldest first, limit 50)
- `DELETE /chat/sessions/{id}` — delete session (FK cascade)
- Auto-title: LLM generates 3-8 word title, strips quotes/preamble, truncates 60 chars

**6F. Migration** — `supabase/migrations/008_rag_traces_add_columns.sql`
- Adds `rewritten_query`, `chunk_count`, `model`, `grounded` columns to `rag_traces`

**6G. Router registration** — `apps/api/src/api/router.py`
- Added `chat.router` to api_router

**Verified**:
- SSE streaming: session → citations → data* → done events ✅
- Session auto-creation and listing ✅
- Auto-title generation ("Rep Ranges") ✅
- Message persistence with citations JSONB ✅
- Follow-up with history: query rewriting worked ("What about for strength?" → "Optimal repetition range for strength development...") ✅
- rag_traces populated: both queries logged with timing, chunks, model, grounded flag ✅
- Typical timing: embedding ~200-400ms, retrieval ~400-900ms, generation ~11-15s

---

### Phase 7: Frontend Chat UI
**Status**: ✅ Complete

**7A. Types** — `features/chat/types/index.ts` — Citation, ChatSession, ChatMessageData, StreamingMessage, SendMessageRequest, SSECallbacks, SUGGESTED_QUESTIONS
**7B. Service** — `features/chat/services/chatService.ts` — REST wrappers (getSessions, getMessages, deleteSession) + `sendMessageSSE()` with fetch + ReadableStream + buffer accumulation for SSE parsing
**7C. Hook** — `features/chat/hooks/useChat.ts` — sessions, messages, streamingMessage, isSending, error state. Functional state updates for stale closure safety. AbortController cleanup. Retry with stored failed message.
**7D. Components** (7 files):
- TypingIndicator — animated bouncing dots
- CitationCard — grouped by paper (1 card per paper), sections + page ranges, DOI links, category badges. `normalizeCiteKey()` for matching inline citations.
- SuggestedQuestions — 4 clickable exercise science questions (empty state)
- ChatMessage — user/assistant bubbles, react-markdown + remark-gfm rendering, inline clickable citations (`[Author, Year]` → scroll to card with highlight), streaming cursor, ungrounded disclaimer
- ChatInput — auto-resize textarea, Enter to send, Shift+Enter newline
- ChatMessageList — scrollable container, auto-scroll near bottom, typing indicator
- SessionSidebar — collapsible panel with session list, new chat, delete
**7E. ChatScreen rewrite** — edge-to-edge layout (`-m-6` + `h-screen`), collapsible sidebar (ChevronLeft/Right toggle), error banner with Retry, loading spinner for session switches
**7F. Dependencies** — `react-markdown`, `remark-gfm`

**Verified**:
- Suggested questions empty state ✅
- Streaming responses with markdown rendering ✅
- Clickable inline citations scroll to citation cards with highlight ✅
- Citation cards grouped by paper with section + page subsections ✅
- DOI links open in new tab ✅
- Session sidebar: create, select, delete ✅
- Multi-turn with query rewriting ✅
- Error banner with retry ✅
- Auto-title appears after ~3s delay ✅

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

**New Files (created so far)**:
```
supabase/migrations/005_rag_tables.sql
supabase/migrations/006_add_paper_license.sql
supabase/migrations/007_match_chunks_add_token_count.sql
supabase/migrations/008_rag_traces_add_columns.sql
apps/api/src/core/embedding_provider.py
apps/api/src/core/llm_provider.py
apps/api/src/core/ingestion.py
apps/api/src/core/retrieval.py
apps/api/src/core/rag_pipeline.py
apps/api/src/core/trace_logger.py
apps/api/src/schema/rag.py
apps/api/src/service/chat_service.py
apps/api/src/api/chat.py
apps/api/scripts/ingest_paper.py
apps/api/scripts/ingest_batch.py
apps/api/scripts/reingest_all.py
apps/api/scripts/test_retrieval.py
apps/api/scripts/test_rag_pipeline.py
apps/api/papers/manifest.json
```

**New Files (Phase 7 — created)**:
```
apps/web/src/features/chat/types/index.ts
apps/web/src/features/chat/services/chatService.ts
apps/web/src/features/chat/services/index.ts
apps/web/src/features/chat/hooks/useChat.ts
apps/web/src/features/chat/hooks/index.ts
apps/web/src/features/chat/components/TypingIndicator.tsx
apps/web/src/features/chat/components/CitationCard.tsx
apps/web/src/features/chat/components/SuggestedQuestions.tsx
apps/web/src/features/chat/components/ChatMessage.tsx
apps/web/src/features/chat/components/ChatInput.tsx
apps/web/src/features/chat/components/ChatMessageList.tsx
apps/web/src/features/chat/components/SessionSidebar.tsx
```

**Modified Files (Phase 7)**:
```
apps/web/src/features/chat/components/index.ts   — 7 component exports
apps/web/src/features/chat/screens/ChatScreen.tsx — full rewrite
apps/web/src/features/chat/index.ts               — add hooks/services/types exports
apps/web/package.json                              — react-markdown, remark-gfm
```

**New Files (planned — Phase 8+)**:
```
apps/api/tests/eval/test_dataset.json
apps/api/tests/eval/test_rag_pipeline.py
apps/api/scripts/evaluate_rag.py
```

**Modified Files**:
```
apps/api/src/utils/config.py          — add RAG env vars
apps/api/src/api/router.py            — register chat router
apps/api/requirements.txt             — add docling, pymupdf, langchain-text-splitters
apps/api/.env                         — add API keys + config
apps/api/src/core/rag_pipeline.py     — thread embedding_time_ms through results
```
