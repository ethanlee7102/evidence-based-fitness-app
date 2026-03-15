# RAG Chatbot — Implementation Context

## Resolved Decisions

### Embedding: Voyage AI `voyage-4-large` (1024 dims)
- ~69.9% MTEB vs OpenAI's 64.6% (~8% better retrieval), same price ($0.12/1M tokens)
- 1024 dims fits pgvector HNSW natively. Free tier: 200M tokens.
- `input_type: "document"` for ingestion, `"query"` for retrieval. Batch limit ~200 chunks/call (120K token limit).

### LLM: Gemini 2.5 Flash
- Cheapest option, swappable via env var + `llm_provider.py` wrapper.
- Migrated from 2.0-flash → 2.5-flash (Google deprecated 2.0-flash free tier, shutdown June 2026).
- Free tier: 10 RPM, 250 RPD, 250K TPM.
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

### Current: 34 papers, ~1307 chunks

| Category | Papers | Notes |
|----------|--------|-------|
| Hypertrophy | 13 | 3 original + 10 new (rest intervals, tempo, proximity-to-failure, ROM, stretch, eccentrics, metabolic stress, periodization, time-efficiency) |
| Nutrition | 18 | 1 original + 2 creatine + 15 expanded (protein, MPS, timing, pre-sleep, caffeine, beta-alanine, supplements, recovery, sleep) |
| Strength | 5 | Tapering, min effective dose, long-term adaptation, load prescription, powerlifting |

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

### Next: Re-run eval with expanded corpus, compare to baseline, set thresholds.

Corpus expansion targets and future RAG improvement ideas are in `FUTURE-PLANS.md`.

### Test Dataset: 38 cases (15 HYP, 6 STR, 13 NUT, 2 CROSS, 2 OOS)
Next: Add strength eval questions when strength corpus is expanded.
