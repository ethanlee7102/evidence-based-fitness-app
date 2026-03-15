# RAG Chatbot — Implementation Context

## Embedding Decision (Resolved)

### Problem
pgvector HNSW index caps at 2,000 dimensions for `vector` type. Original plan used OpenAI `text-embedding-3-large` at 3,072 dims.

### Options Evaluated
1. **Reduce OpenAI 3-large to 1024 dims** — Matryoshka training lets you truncate with <1% quality loss
2. **Use `halfvec` casting** — pgvector 0.7.0+ supports half-precision up to 4,000 dims, but adds complexity
3. **No index (brute force)** — At 5,000-10,000 chunks, latency is ~40-80ms. Acceptable since LLM generation dominates (1-5s)
4. **Switch to Voyage AI** — Better quality, same price, 1024 dims natively

### Decision: Voyage AI `voyage-4-large` (1024 dims)
- **Quality**: ~69.9% MTEB vs OpenAI's 64.6% (~8% better retrieval)
- **Price**: $0.12/1M tokens vs OpenAI's $0.13 (basically same, pennies at our scale)
- **Dimensions**: 1024 default — fits pgvector HNSW natively, no workarounds
- **Free tier**: 200M tokens
- **Why not OpenAI?**: Voyage is better on every metric. OpenAI's only advantage is more tutorials/community docs.
- **Why not smaller Voyage models?**: voyage-4-large is the best quality, cost difference is irrelevant at our scale (50-100 papers)

### Key Insight
`text-embedding-3-large` at 1024 dims still outperforms `text-embedding-3-small` at full 1536 dims. The large model encodes richer semantics even when truncated. Same principle applies to Voyage 4 family — all models produce compatible embeddings (shared embedding space).

---

## LLM Decision (Resolved)

### Decision: Gemini 2.5 Flash
- Cheapest option, swappable via env var + `llm_provider.py` wrapper
- Migrated from gemini-2.0-flash → gemini-2.5-flash (Google deprecated 2.0-flash free tier, shutdown June 2026)
- Free tier: 10 RPM, 250 RPD, 250K TPM
- Provider designed to be swappable — can change later without re-processing anything
- ~~Verify Voyage AI REST API format~~ ✅ Verified (see below)
- ~~Verify Gemini REST API format~~ ✅ Verified (see below)

---

## Voyage AI REST API — Verified

**Endpoint**: `POST https://api.voyageai.com/v1/embeddings`
**Auth**: `Authorization: Bearer $VOYAGE_API_KEY`

### Request Body
```json
{
  "input": ["text1", "text2"],     // string | string[] — max 1,000 items
  "model": "voyage-4-large",       // required
  "input_type": "document",        // null | "query" | "document"
  "output_dimension": 1024,        // 2048, 1024 (default), 512, 256
  "truncation": true               // default true
}
```

### Response Body
```json
{
  "object": "list",
  "data": [
    { "object": "embedding", "embedding": [0.0123, ...], "index": 0 },
    { "object": "embedding", "embedding": [0.0456, ...], "index": 1 }
  ],
  "model": "voyage-4-large",
  "usage": { "total_tokens": 8 }
}
```

### Key Details
- **`input_type` matters for retrieval quality**: Voyage prepends different internal prompts depending on value
  - `"document"` — use when embedding chunks during ingestion
  - `"query"` — use when embedding user questions at query time
  - `null` — direct vectorization without prompts (still compatible)
- **Token limit**: 120K tokens per request for voyage-4-large
- **Batch limit**: max 1,000 items per request, but token limit is the real constraint
- **Safe batch size**: ~200 chunks per call (assuming ~500 tokens/chunk)
- **Format**: Nearly identical to OpenAI's embeddings API (same `input`/`model` fields, same `data[].embedding` response shape). Voyage-specific additions: `input_type`, `output_dimension`, `output_dtype`

### Impact on Our Implementation
- `embed_texts()` must send `input_type: "document"` (for ingestion)
- `embed_query()` must send `input_type: "query"` (for retrieval)
- Batch ingestion should chunk into groups of ~200 to stay under 120K token limit

---

## Gemini REST API — Verified

### Endpoints
```
# Non-streaming (for eval pipeline)
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=$GOOGLE_API_KEY

# Streaming (for chat UI)
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key=$GOOGLE_API_KEY
```

**Auth**: API key as **query parameter** (not Bearer token like Voyage).

### Request Body
```json
{
  "system_instruction": {
    "parts": [{"text": "You are a helpful exercise science assistant."}]
  },
  "contents": [
    {
      "role": "user",
      "parts": [{"text": "What rep range is best for hypertrophy?"}]
    }
  ],
  "generationConfig": {
    "maxOutputTokens": 2048,
    "temperature": 0.7
  }
}
```

### Response Body (non-streaming)
```json
{
  "candidates": [{
    "content": {
      "role": "model",
      "parts": [{"text": "The generated response..."}]
    },
    "finishReason": "STOP"
  }],
  "usageMetadata": {
    "promptTokenCount": 50,
    "candidatesTokenCount": 200,
    "totalTokenCount": 250
  }
}
```

**Extract text**: `response["candidates"][0]["content"]["parts"][0]["text"]`

### Streaming Response
SSE (Server-Sent Events) via `?alt=sse` query param. Each event is a `GenerateContentResponse` JSON — same structure as non-streaming but arriving incrementally. Concatenate `candidates[0].content.parts[0].text` from each chunk.

### Key Details
- **Auth difference**: API key in query string (server-side only, acceptable)
- **System prompt**: Separate `system_instruction` field (not inside `contents` array)
- **Streaming trigger**: `?alt=sse` query param on the `streamGenerateContent` endpoint
- **Two SSE hops in our architecture**: Gemini → our backend (Gemini SSE) → browser (our SSE endpoint from Phase 6)

### Why Two Endpoints
- `generate()` uses `generateContent` — returns full response in one shot. Used by the **eval pipeline** (Phase 8) where nobody is watching, just need the final answer to score.
- `generate_stream()` uses `streamGenerateContent` — tokens arrive as they're generated. Used by the **chat UI** (Phase 7) for real-time typing effect. Users see text appearing in ~200ms vs waiting 3-8s for a wall of text.

---

## Phase 2 Implementation — ✅ Complete

### What Was Built
- **2A. Config** (`config.py`) — Added 11 RAG env vars with sensible defaults. Only VOYAGE_API_KEY and GOOGLE_API_KEY are required.
- **2B. Embedding Provider** (`embedding_provider.py`) — `embed_texts()` with document input_type + auto-batching, `embed_query()` with query input_type
- **2C. LLM Provider** (`llm_provider.py`) — `generate()` non-streaming + `generate_stream()` SSE streaming, both with configurable `temperature` and `max_tokens` params
- **2D. Dependencies** — docling + pymupdf + langchain-text-splitters added and installed. Docling for ML-based layout analysis, pymupdf for font metadata via bounding box matching.
- **Lifespan hook** in `app.py` — cleans up shared httpx clients on shutdown

### Decisions Made
- **Lazy validation** — RAG API keys only checked when providers are called, not at app boot. App still works for non-RAG features without keys.
- **Shared httpx AsyncClient** (Option B) — Module-level client per provider, reuses TCP connections. Cleaned up via FastAPI `lifespan` hook. Chose over per-call clients for connection pooling (same pattern as DB connection pools).
- **`temperature` and `max_tokens` as function parameters** — Not hardcoded, not in config. RAG pipeline will use low temperature (0.3-0.5) for faithfulness, eval pipeline may use different caps. Defaults: 0.7 temp, 2048 max tokens.

### Code Review Findings (post-implementation)
| Finding | Decision |
|---------|----------|
| API key in Gemini URL (visible in DEBUG logs) | Accepted — Google's required auth method, server-side only. Change log level to INFO in production. |
| Hardcoded temperature | **Fixed** — added as function parameter |
| No maxOutputTokens | **Fixed** — added as function parameter |
| No retry logic | **Deferred to Phase 3** — add to `embed_texts()` during ingestion pipeline (see below) |
| Duplicate headers in embed functions | Accepted — 2 instances doesn't warrant abstraction |
| Silent SSE parse skip | **Fixed** — added debug-level logging |

### Verified
- `embed_query("test")` returns 1024-dim float vector ✅
- Dependencies install cleanly ✅
- App boots with lifespan hook ✅

---

## Retry Logic — Planned for Phase 3

When building the ingestion pipeline, add retry with exponential backoff to `embed_texts()`. This is the most likely function to hit rate limits (batch calls during ingestion of 50+ papers).

**Approach**: Manual retry (no tenacity dependency). Retry 2-3 times on 429/500/503 with exponential backoff (1s, 2s, 4s). Log each retry attempt.

**Why not now**: No callers exist yet. We don't know what error patterns we'll actually hit. Better to add when we build the ingestion pipeline and can test against real failure modes.

**Why not `embed_query`**: Single-call function used at query time. If it fails, the user gets an error and can retry manually. Automatic retry would add latency to a user-facing path.

---

## Phase 1 Additions (beyond original plan)
These columns were added during Phase 1 implementation after discussion:
- `papers.abstract` — for paper preview cards in the UI, avoids showing raw chunk text
- `chunks.page_start` / `chunks.page_end` — for page-level citations (e.g. "Schoenfeld et al., 2017, p. 12"). Most chunks will be single-page since chunk size (~500-1000 tokens) fits within one PDF page (~500-800 words).
- `chunks.token_count` — for prompt assembly budget. When stuffing top-k chunks into LLM context, sum token_count to know if you can fit 5 chunks or only 3 before hitting the limit. Stored at ingestion time to avoid re-tokenizing at query time.

## License & Copyright Strategy

### Decision
Track the Creative Commons license of every ingested paper. This enables filtering the corpus to commercially-usable papers (CC-BY, CC0) if the app is ever monetized.

### License field
Added via migration `006_add_paper_license.sql`. Column on `papers` table with CHECK constraint: CC0, CC-BY, CC-BY-SA, CC-BY-ND, CC-BY-NC, CC-BY-NC-SA, CC-BY-NC-ND, other, unknown. Defaults to `'unknown'`.

### Paper sourcing strategy
- **Primary source**: PMC Open Access Subset (pmc.ncbi.nlm.nih.gov/tools/openftlist/) — millions of papers tagged by license
- **Search filter**: Append `AND cc by license[filter]` to PMC searches for commercial-safe papers
- **For v1 learning**: Use whatever papers help build/test the pipeline; license tracking is for future-proofing
- **For commercial use**: Filter corpus to `WHERE license IN ('CC0', 'CC-BY', 'CC-BY-SA', 'CC-BY-ND')`

### Copyright-safe RAG design
- LLM synthesizes answers in its own words — verbatim chunks are **never** displayed to users
- Chunks are an internal retrieval mechanism, not a display mechanism
- Prompt instructs LLM to explain in its own words, not quote directly
- Citations give attribution ([Author, Year] with DOI/URL links)
- This is the most defensible RAG architecture: transformative output, no market substitution, factual content (thin copyright), proper attribution

### Legal context (as of Feb 2026)
- No definitive court ruling on RAG + copyrighted content yet (Perplexity cases pending)
- Google Books precedent (intermediate copying for search = fair use) most analogous to our design
- Thomson Reuters v. ROSS (2025) rejected fair use but involved a direct market competitor — not analogous
- Scientific facts get less copyright protection than creative works
- CC-BY papers = zero legal risk (explicit permission with attribution only)

---

---

## Phase 3: Ingestion Pipeline — ✅ Complete

### What Was Built
- **Schemas** (`src/schema/rag.py`) — PaperMetadata, PaperResponse, ChunkResponse with Literal types matching DB CHECK constraints
- **Ingestion core** (`src/core/ingestion.py`) — compute_content_hash, extract_sections, chunk_sections, ingest_paper
- **Retry logic** — added to embed_texts() in embedding_provider.py: 3 attempts, 1s→2s→4s backoff, on 429/500/503
- **CLI scripts** — `scripts/ingest_paper.py` (single) + `scripts/ingest_batch.py` (batch from manifest.json)
- **Papers directory** — `papers/` for PDFs (gitignored), `papers/manifest.json` checked in

### Section Detection (Docling + pymupdf hybrid)
IBM Docling (DocLayNet ML model) handles layout analysis — reading order, header detection, tables, headers/footers. pymupdf provides font metadata (size, bold) for header hierarchy classification via bounding box spatial matching.

**Docling handles**:
- **Section headers**: ML classification via `DocItemLabel.SECTION_HEADER`
- **Double-column layouts**: Automatic layout analysis, correct reading order
- **Tables**: Exported as markdown via `item.export_to_markdown(doc)`
- **Headers/footers**: Automatically excluded
- **Page numbers**: 1-based from `item.prov[0].page_no`

**pymupdf handles** (font metadata only):
- **Bounding box matching**: Docling `item.prov[0].bbox` (BOTTOMLEFT coords) → convert y-axis (`pymupdf_y = page_height - docling_y`) → find overlapping pymupdf spans → read font size and bold flag
- 246/246 headers matched across 9 papers (100% hit rate), <1pt coordinate discrepancy

**Header hierarchy** (layered classification in `_classify_major_headers`):
1. **Font size grouping** — largest font-size group with >= 2 members = major
2. **Bold tiebreaker** — if selected group has bold/non-bold mix, only bold = major (MDPI journals)
3. **ALL_CAPS tiebreaker** — if selected group has CAPS/mixed-case mix AND group is >70% of valid headers, only CAPS = major (Frontiers journals)
4. **ALL_CAPS/numbered fallback** — when no font size groups found
5. **All major fallback** — when no hierarchy signal detected

**Abstract detection** (after hierarchy classification):
- **Force-promote**: Any Docling-detected header matching `^abstract\b` (case-insensitive) is promoted to major regardless of font size
- **Body text scan**: Before the first major header, scans body text blocks for "Abstract:" prefix (regex: `^abstract\s*[:\-—.]?\s*`). If found, injects a synthetic "Abstract" section break and keeps the remaining text as body content. Handles MDPI papers where abstract is labeled as body text, not a header.
- Result: 7/9 papers have Abstract as its own section. 2 Frontiers papers have completely unlabeled abstracts (no "Abstract" text in PDF at all).

Fallback: if <= 1 major header → entire document as one section with `section=None`

Lazy converter singleton loads ML models once on first use, reuses for batch ingestion. First run downloads ~6.2 GB of models to `~/.cache/huggingface/hub/`.

### Per-Chunk Page Tracking
Each section carries a `page_map: list[tuple[int, int]]` mapping char offsets to page numbers. After chunking, `_find_page_range()` maps each chunk's text position back to specific pages for accurate citations.

### Supabase Insert Pattern
```python
result = supabase.table("papers").insert(paper_data).execute()
paper_id = result.data[0]["id"]  # auto-generated UUID returned by default
```
supabase-py sends `Prefer: return=representation` by default. Don't include `"id"` in the insert dict — let PostgreSQL generate it via `gen_random_uuid()`.

### Test Results
- **Wax et al. 2021** (creatine review) — 70 chunks, 9 sections including Abstract (body text scan)
- **Kazeminasab et al. 2025** (creatine meta-analysis) — 71 chunks, 7 sections including Abstract (Docling header + force-promote)
- **Schoenfeld et al. 2021** (rep ranges, hypertrophy) — 52 chunks, 8 sections including Abstract (body text scan)
- **Bernardez-Vazquez et al. 2022** (hypertrophy umbrella review) — 32 chunks, 9 sections (Frontiers, no abstract label)
- **Krzysztofik et al. 2019** (advanced RT techniques) — 28 chunks, 7 sections including Abstract (body text scan)
- **Travis et al. 2020** (tapering for powerlifting) — 34 chunks, 8 sections including Abstract (body text scan)
- **Androulakis-Korakakis et al. 2021** (minimum effective dose) — 64 chunks, 16 sections (Frontiers, no abstract label)
- **Latella et al. 2020** (15-year powerlifting analysis) — 20 chunks, 10 sections including Abstract (Docling header + force-promote)
- **Thompson et al. 2020** (load prescription methods) — 43 chunks, 8 sections including Abstract (Docling header + force-promote)
- **Total (original 9)**: 9 papers, 414 chunks (3 hypertrophy, 1 nutrition, 5 strength). Expanded to 24 papers, 909 chunks after Phase 8 corpus expansion.
- Dedup confirmed — re-run skips with "Paper already ingested"
- Retry logic confirmed — triggered on Voyage 429 before payment method was added
- Voyage free tier without payment: 3 RPM / 10K TPM (very restrictive). Adding payment method unlocks normal limits, free tokens still apply.
- Double-column handling verified with `sort=True` — text reads coherently
- Section detection path 4 verified on JSCR paper — detected Introduction, Methods, Discussion, References

### Async/Sync Pattern
`ingest_paper()` is async (to await embed_texts) but uses sync Supabase client for DB calls. Fine for CLI scripts — sync calls block event loop briefly but nothing else is waiting. Comment in code notes to wrap in `asyncio.to_thread()` if ever called from web handlers.

---

## Phase 5 Ideas (noted for later)
- **Abstract-augmented retrieval**: Always include abstract of cited papers in prompt context, even if abstract chunk didn't make top-k. Gives LLM full-picture grounding for better answers.
- **Two-stage retrieval (v2)**: Search abstracts first to find relevant papers, then search chunks within those papers for specific evidence.

---

## Phase 4: Retrieval Pipeline — ✅ Complete

### What Was Built
- **Migration 007** (`007_match_chunks_add_token_count.sql`) — Updates `match_chunks` RPC to return `token_count` alongside existing columns
- **Schema update** (`src/schema/rag.py`) — Added `token_count: Optional[int] = None` to `ChunkResponse`, added `RetrievalResult` dataclass
- **Retrieval module** (`src/core/retrieval.py`) — `retrieve_chunks()` async function

### `retrieve_chunks()` Flow
1. Start perf timer
2. `await embed_query(query)` — reuses Voyage AI provider with `input_type="query"`
3. `get_supabase().rpc("match_chunks", params).execute()` — vector similarity search via pgvector
4. Parse rows into `list[ChunkResponse]` via Pydantic
5. Log: query (truncated 80 chars), chunk count, similarity range (min-max), timing
6. Return `RetrievalResult(chunks, query, retrieval_time_ms)`

### `RetrievalResult` — Why Dataclass, Not Pydantic
Internal data carrier passed between `retrieval.py` → `rag_pipeline.py` → `trace_logger.py`. Never serialized to/from JSON over the wire. Dataclass is lighter — no validation overhead for trusted internal data.

### PostgreSQL Gotcha: DROP Before CREATE When Return Type Changes
`CREATE OR REPLACE FUNCTION` can only change the function **body**, not the `RETURNS TABLE` columns. Adding `token_count` to the return type is a signature change, so PostgreSQL requires `DROP FUNCTION` first, then `CREATE FUNCTION`. This is safe — no data loss, just replaces the function.

### `token_count` Purpose
Phase 5 needs token counts to budget how many chunks fit in the LLM's context window. Without it, you'd re-count tokens on every query (wasteful) or blindly stuff chunks and risk truncation.

### Decisions
- **No query reformulation here** — retrieval stays "dumb." Phase 5 handles history-aware query rewriting before calling `retrieve_chunks()`
- **No re-ranking** — deferred to v2. pgvector cosine similarity ordering is the final ranking for v1
- **Defaults from config** — `top_k` falls back to `config.RAG_TOP_K` (5), threshold to `config.RAG_SIMILARITY_THRESHOLD` (0.3)
- **Optional category filter** — `None` = search all categories. Vector search handles topic matching naturally

---

## Session Notes
- **Phase 1 migration** has been run in Supabase — tables and pgvector extension confirmed working.
- **Phase 2 implementation** complete and verified — embedding provider, LLM provider, config, dependencies all working.
- **Migration 006** — `license` column added to papers table and applied in Supabase.
- **Phase 3 implementation** complete and verified — 24 papers ingested, section detection working, dedup working.
- **Migration 007** — `match_chunks` RPC updated to return `token_count`. Requires DROP+CREATE (not CREATE OR REPLACE) due to return type change.
- **Phase 4 implementation** complete — retrieval module, schema updates, migration all in place.
- **PLAN.md** exists at project root — keep phase statuses updated there as work completes.
- **CLAUDE.md** has a reference to PLAN.md at the top.
- **Corpus**: 24 papers ingested (909 chunks total). 3 hypertrophy, 18 nutrition, 5 strength. All CC-BY licensed. PDFs in `apps/api/papers/` (gitignored).
- **Phase 5 implementation** complete — rag_pipeline.py, multi-turn LLM support, query rewriting, [Author, Year, p. X] citations, grounded/ungrounded handling.
- **Gemini model migration**: gemini-2.0-flash → gemini-2.5-flash (Google zeroed free tier for 2.0-flash, deprecated with June 2026 shutdown).
- **Phase 6 implementation** complete — Chat API (SSE streaming), TraceLogger (fire-and-forget), ChatService (session CRUD), migration 008 (trace columns).
- **Phase 7 implementation** complete — Frontend chat UI with streaming, clickable inline citations, grouped citation cards, session sidebar.
- **Phase 8 implementation** complete — Custom LLM-as-judge eval pipeline (5 metrics, 20 test cases, CLI + pytest). Awaiting baseline run.
- **Corpus expansion** — 15 new nutrition papers added (protein, supplements, timing, recovery, sleep). See "Corpus Expansion" section below.
- **Ingestion quality fixes** — Title-level font group skip heuristic (while loop) fixes JISSN and TSMED papers. See "Ingestion Quality Fixes" section below.
- Papers updated with DOI and PMC URL metadata (all 24 papers).
- **Next**: Run baseline eval, review test dataset Q&A pairs, set pytest thresholds.

---

## Phase 5: RAG Generation Pipeline — ✅ Complete

### What Was Built

Phases 1-4 are complete: DB schema, embedding/LLM providers, ingestion pipeline (9 papers / 414 chunks), and retrieval pipeline. Phase 5 bridges retrieval and generation — given a user question, retrieve relevant chunks, format them into a citation-aware prompt, and generate a cited answer via the LLM. One function call now produces a fully cited exercise science answer end-to-end.

### Design Decisions (locked in)

| # | Decision |
|---|----------|
| Q1 | Native multi-turn — modify `generate()`/`generate_stream()` to accept `messages` list |
| Q2 | Conditional query rewriting — only rewrite when history exists |
| Q3 | Composite object — `StreamingRAGResult` with `.stream` async generator |
| Q4 | Hardcode temperature 0.3 — no config |
| Q5 | No-chunks: still call LLM with disclaimer instruction + `grounded: bool` flag |
| Q6 | Abstract augmentation deferred to post-eval |

---

### Implementation Steps

#### Step 1: Modify `llm_provider.py` for multi-turn

**File**: `apps/api/src/core/llm_provider.py`

Add `messages: list[dict] | None = None` parameter to three functions:

**`_build_gemini_payload()`** — If `messages` provided, build `contents` array from history + current prompt. Map neutral `"assistant"` role to Gemini's `"model"`. Append `prompt` as the final user turn. If no messages, existing single-prompt behavior unchanged.

```python
def _build_gemini_payload(
    prompt: str,
    system: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    messages: list[dict] | None = None,   # <-- new
) -> dict:
```

Contents-building logic:
```python
if messages:
    role_map = {"assistant": "model", "user": "user"}
    contents = [
        {"role": role_map[msg["role"]], "parts": [{"text": msg["content"]}]}
        for msg in messages
    ]
    contents.append({"role": "user", "parts": [{"text": prompt}]})
else:
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
```

**`generate()` and `generate_stream()`** — Add same `messages` param, pass through to `_build_gemini_payload()`. Backward compatible (default `None`).

---

#### Step 2: Add new types to `schema/rag.py`

**File**: `apps/api/src/schema/rag.py`

**`ChatMessage`** — TypedDict for history entries (neutral format):
```python
class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str
```

**`RAGResult`** — dataclass for non-streaming response (eval pipeline):
```python
@dataclass
class RAGResult:
    answer: str
    chunks: list[ChunkResponse]
    query: str
    rewritten_query: str | None
    prompt_sent: str
    retrieval_time_ms: float
    generation_time_ms: float
    model: str
    grounded: bool
```

**`StreamingRAGResult`** — dataclass for streaming response (chat UI):
```python
@dataclass
class StreamingRAGResult:
    chunks: list[ChunkResponse]
    query: str
    rewritten_query: str | None
    prompt_sent: str
    retrieval_time_ms: float
    model: str
    grounded: bool
    stream: AsyncGenerator[str, None]
```

No `answer` or `generation_time_ms` — those aren't available until the stream finishes. Phase 6 route handler measures generation timing and accumulates the full answer.

---

#### Step 3: Create `rag_pipeline.py`

**File**: `apps/api/src/core/rag_pipeline.py` (new)

##### Constants

**`SYSTEM_PROMPT`** — Exercise science assistant persona. Cite `[Author, Year]`, beginner-level, "I don't know" when lacking sources, no fabrication, acknowledge disagreements between sources.

**`NO_CHUNKS_INSTRUCTION`** — Replaces sources block when retrieval returns empty. Instructs LLM to answer from general knowledge but disclaim it's not backed by research.

**`REWRITE_PROMPT`** — Template for query rewriting. Takes `{history}` and `{query}` placeholders.

##### Functions

**`_rewrite_query(query, history) -> str`**
- If no history: return query unchanged (first message, no rewrite needed)
- If history: format history as readable text, call `generate()` with temp=0.0, max_tokens=256
- Log original → rewritten (truncated)

**`_build_sources_block(chunks) -> str`**
- Format chunks as numbered sources: `[1] Author, Year (Journal) [Section: X]: "chunk text"`
- Used by `build_rag_prompt()`

**`build_rag_prompt(query, chunks) -> str`**
- If chunks: sources block + question
- If no chunks: no-chunks instruction + question
- System prompt is NOT included here — it goes via the `system` parameter to `generate()`

**`rag_query(query, history, top_k, category) -> RAGResult`**
- Full pipeline: rewrite → retrieve → build prompt → `generate()` → return RAGResult
- Temperature 0.3, max_tokens 2048
- Logs chunk count, grounded status, retrieval + generation timing

**`rag_query_stream(query, history, top_k, category) -> StreamingRAGResult`**
- Same pipeline but generation is lazy — creates `generate_stream()` generator without consuming it
- Returns StreamingRAGResult with metadata + `.stream`
- Phase 6 route reads metadata first, then iterates `.stream` for SSE events

---

#### Step 4: Create test script

**File**: `apps/api/scripts/test_rag_pipeline.py` (new)

CLI script following `ingest_paper.py` pattern:
```bash
cd apps/api
python -m scripts.test_rag_pipeline "How does creatine affect muscle growth?"
python -m scripts.test_rag_pipeline "Tell me more about dosing" --stream --history '[...]'
```

Prints: metadata (grounded, chunks, timing, rewritten query) + sources list + answer + prompt preview.

---

### File Summary

| File | Action |
|------|--------|
| `apps/api/src/core/llm_provider.py` | Modify — add `messages` param to 3 functions |
| `apps/api/src/schema/rag.py` | Modify — add ChatMessage, RAGResult, StreamingRAGResult |
| `apps/api/src/core/rag_pipeline.py` | **Create** — system prompt, rewrite, prompt builder, rag_query, rag_query_stream |
| `apps/api/scripts/test_rag_pipeline.py` | **Create** — CLI test script |

### Implementation Order

1. `llm_provider.py` (Step 1) — must come first, `rag_pipeline.py` depends on `messages` param
2. `schema/rag.py` (Step 2) — must come before `rag_pipeline.py` which imports new types
3. `rag_pipeline.py` (Step 3) — core deliverable
4. `test_rag_pipeline.py` (Step 4) — verification

### Verification

Test scenarios to run with the CLI script:

1. **Grounded query**: `"How does creatine affect muscle mass?"` — should return cited answer from ingested papers, `grounded=True`
2. **Streaming mode**: same query with `--stream` — tokens print incrementally
3. **Ungrounded query**: `"What's the best programming language?"` — `grounded=False`, disclaimer in answer
4. **Follow-up with history**: `"Tell me more about the dosing"` with history — `rewritten_query` should be non-None, should retrieve relevant chunks
5. **Category filter**: `--category nutrition` — only retrieves from matching papers

### Note

Gemini requires `contents` to alternate user/model roles. The pipeline trusts the caller (Phase 6) to enforce alternation. Worth adding a comment in `rag_pipeline.py` but not validating at this layer.

---

## Double-Column PDF Issue — Resolved with Docling + pymupdf hybrid

### Problem Discovered

After ingesting 9 papers, found that double-column PDFs have section content assigned to wrong headers. pymupdf's `sort=True` on `get_text("dict")` sorts blocks by position (top-to-bottom, left-to-right), but this breaks when headers and content are in different columns.

### Decision: IBM Docling + pymupdf hybrid

**Why**: Docling's ML-based layout analysis handles columns, headers, and tables automatically. pymupdf provides font size/bold metadata for header hierarchy (Docling detects headers but doesn't distinguish major vs minor).

**Bounding box matching**: Instead of matching Docling headers to pymupdf by text (fragile — pymupdf fragments text differently), match by position. Docling provides `item.prov[0].bbox` (BOTTOMLEFT coords), pymupdf provides span bboxes (TOPLEFT coords). Conversion: x identical, `pymupdf_y = page_height - docling_y`. 246/246 headers matched across 9 papers.

**What changed**:
- `extract_sections()` in `ingestion.py` uses Docling for layout + pymupdf for font info
- `docling>=2.0.0` added to requirements.txt, `pymupdf>=1.24.0` kept (font metadata only)
- Header hierarchy: font size grouping → bold tiebreaker → ALL_CAPS tiebreaker → fallbacks
- All downstream functions unchanged (`chunk_sections`, `_find_page_range`, `ingest_paper`)
- See `DOCLING-REFACTOR.md` for full implementation history

**After rewrite**: Re-ingested all 9 papers. 414 total chunks. Retrieval verified with cross-paper queries (similarity 0.65-0.75).

---

## Phase 6: Chat API + TraceLogger — ✅ Complete

### What Was Built

Bridges the RAG pipeline (Phases 1-5) to HTTP — SSE streaming chat endpoint, session management, and observability logging. The backend is now fully functional for the frontend chat UI (Phase 7).

### Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Session creation | Hybrid — auto-create on first message | Lowest friction UX |
| Auto-title | LLM-generated, fire-and-forget, 40 tokens + cleanup | Non-blocking, nice titles |
| History window | Last 10 messages | Covers 5 turns, cheap |
| TraceLogger | Fire-and-forget via `asyncio.create_task()` | Zero latency cost |
| Split embedding time | Timer in `retrieval.py`, threaded to traces | Separates embed vs search for debugging |
| Chunk text in traces | Full text | Self-contained snapshots |
| Partial answers on error | Don't save | Trace logs it for debugging |
| Title token limit | 40 tokens + strip quotes/preamble, truncate 60 chars | Keep titles concise |

### Implementation Details

**Step 0: Split embedding time** — Timer around `embed_query()` in `retrieval.py`. Added `embedding_time_ms` to `RetrievalResult`, `RAGResult`, `StreamingRAGResult`. Threaded through `rag_pipeline.py`.

**Step 1: Schema additions** — 4 Pydantic models added to `rag.py`: `ChatMessageRequest`, `CitationPayload`, `SessionResponse`, `MessageResponse`.

**Step 2: TraceLogger** (`src/core/trace_logger.py`) — `log_trace()` creates async task, `_insert_trace()` does DB insert catching all exceptions. Maps `answer` → `llm_response` (DB column name). Rounds timing to integers for INTEGER columns. Omits `message_id` key on error traces.

**Step 3: ChatService** (`src/service/chat_service.py`) — Session CRUD (create, get, list, delete), message CRUD (save, get, get_recent for RAG). Uses `datetime.now(timezone.utc).isoformat()` for `updated_at` (Supabase REST API doesn't accept `"now()"`). `get_recent_messages()` fetches desc + reverses for oldest-first within window.

**Step 4: Chat Route** (`src/api/chat.py`) — 5 endpoints. `POST /chat/message` is the main SSE streaming endpoint. SSE event flow: `session` (new only) → `citations` (always, with deduped `CitationPayload` list) → `data*` (text chunks) → `done` (with message_id). Post-stream work (save message, log trace, generate title) runs inside the generator after final yield. Auto-title uses `generate()` with temp=0.7, cleans with regex (strips preamble, quotes, truncates).

**Step 5: Router registration** — 2-line change in `router.py`.

**Step 6: Migration 008** — Adds `rewritten_query TEXT`, `chunk_count INTEGER`, `model TEXT`, `grounded BOOLEAN` to `rag_traces`.

### Verified

- SSE streaming: session → citations → data* → done ✅
- Session auto-creation and listing ✅
- Auto-title generation ("Rep Ranges") ✅
- Message persistence with citations JSONB ✅
- Follow-up: query rewriting worked ("What about for strength?" → "Optimal repetition range for strength development...") ✅
- rag_traces: both queries logged with embedding_time_ms, chunk_count, model, grounded ✅
- Timing: embedding ~200-400ms, retrieval ~400-900ms, generation ~11-15s

### Gotchas

- DB column is `llm_response`, not `answer` — TraceLogger maps accordingly
- Supabase REST API doesn't accept `"now()"` string — must pass actual ISO timestamp
- `rag_traces.embedding_time_ms` is INTEGER — must round float values
- Post-stream work must be inside the generator (after yield), not after `return StreamingResponse` — code after return never executes

---

### Original Plan Details (for reference)

#### Implementation Order

1. **Schema additions** (`src/schema/rag.py`) — needed by everything
2. **TraceLogger** (`src/core/trace_logger.py`) — independent
3. **ChatService** (`src/service/chat_service.py`) — independent
4. **Chat Route** (`src/api/chat.py`) — depends on 1-3
5. **Router registration** (`src/api/router.py`) — depends on 4

Steps 2 and 3 are independent and can be built in parallel.

---

### Step 1: Schema Additions

**File**: `apps/api/src/schema/rag.py` (modify — add at bottom)

Add 4 Pydantic models:

```python
class ChatMessageRequest(BaseModel):
    """POST /chat/message request body."""
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[str] = None      # None = create new session
    category: Optional[Category] = None   # Optional retrieval filter

class SessionResponse(BaseModel):
    """Chat session returned from API."""
    id: str
    user_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    """Chat message returned from API."""
    id: str
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    citations: Optional[list[dict]] = None
    created_at: datetime
    class Config:
        from_attributes = True

class CitationPayload(BaseModel):
    """Stripped-down citation for SSE event. No chunk_text (copyright)."""
    chunk_id: str
    title: str
    authors: str
    year: int
    journal: Optional[str] = None
    doi: Optional[str] = None
    section: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    similarity: float
    category: Category
```

---

### Step 2: TraceLogger

**File**: `apps/api/src/core/trace_logger.py` (new)

**Purpose**: Fire-and-forget observability — records every RAG interaction to `rag_traces`.

**Functions**:
- `log_trace(user_id, session_id, message_id, query, result, answer, generation_time_ms, error=None)` — regular function (not async), calls `asyncio.create_task()` internally
- `_insert_trace(...)` — async function that does the actual DB insert, catches all exceptions internally
- `_chunks_to_json(chunks)` — converts ChunkResponse list to JSON-serializable dicts (excludes `chunk_text` — too large, already in chunks table)

**Key details**:
- `embedding_time_ms` left as NULL (pipeline doesn't separate embedding from vector search time)
- `total_time_ms` = retrieval_time_ms + generation_time_ms
- Never raises — logs errors internally

---

### Step 3: ChatService

**File**: `apps/api/src/service/chat_service.py` (new)

**Pattern**: Same as `DBService` — class with `self.supabase = get_supabase()`.

**Methods**:

| Method | Returns | Notes |
|--------|---------|-------|
| `create_session(user_id, title=None)` | `dict` | Returns created row with `id` |
| `get_sessions(user_id)` | `list[dict]` | Ordered by `updated_at` desc |
| `get_session(session_id, user_id)` | `dict \| None` | Uses `.maybe_single()` (not `.single()` — avoids exception on 0 rows) |
| `delete_session(session_id, user_id)` | `bool` | FK cascades delete messages |
| `get_messages(session_id, user_id, limit=50)` | `list[dict]` | Oldest first, verifies ownership |
| `get_recent_messages(session_id, user_id, limit=10)` | `list[ChatMessage]` | Last N as TypedDicts for RAG history. Fetches desc + reverses. |
| `save_message(session_id, role, content, citations=None)` | `dict` | Returns created row with `id` |
| `update_session_title(session_id, title)` | `None` | For async title gen |
| `update_session_timestamp(session_id)` | `None` | Bumps `updated_at` |

**Key details**:
- Service_role key bypasses RLS → enforce `user_id` in every query (same pattern as `DBService`)
- `get_recent_messages` returns `list[ChatMessage]` which is exactly what `rag_query_stream(history=...)` expects
- `update_session_title` skips `user_id` check — called from background task where ownership already verified

---

### Step 4: Chat Route

**File**: `apps/api/src/api/chat.py` (new)

**Router**: `APIRouter(prefix="/chat", tags=["chat"])`

#### Endpoints

**`POST /chat/message`** — Main SSE streaming endpoint

Flow:
1. If no `session_id` → create session
2. Get recent history BEFORE saving user message (avoids dedup)
3. Save user message + bump `updated_at`
4. Call `rag_query_stream(query, history, category)`
5. Return `StreamingResponse` with SSE events:

```
event: session   → {"session_id": "uuid", "title": null}       (only if new session)
event: citations → {"chunks": [...], "grounded": true}          (always, before text)
event: data      → {"text": "chunk"}                            (repeated per LLM batch)
event: done      → {"message_id": "uuid"}                       (stream complete)
event: error     → {"detail": "..."}                            (on failure)
```

6. After stream completes: save assistant message (with citations JSONB), log trace (fire-and-forget), generate title if first message (fire-and-forget)

**`GET /chat/sessions`** — List sessions (newest first)
- Response: `list[SessionResponse]`

**`GET /chat/sessions/{session_id}`** — Single session
- Response: `SessionResponse`

**`GET /chat/sessions/{session_id}/messages`** — Messages for session
- Response: `list[MessageResponse]`

**`DELETE /chat/sessions/{session_id}`** — Delete session (204 No Content)
- FK cascade deletes messages

#### Helpers

- `_sse_event(event, data) -> str` — formats SSE event string
- `_generate_title(query, answer_preview, session_id, chat)` — async, fire-and-forget via `asyncio.create_task()`. Calls `generate()` with temp=0.7, max_tokens=20. Truncates title to 60 chars.

#### Key details

- History fetched BEFORE saving user message — no dedup needed
- Citations stored on assistant message as simplified JSONB (title, authors, year, doi, journal) for historical display
- `CitationPayload` sent over SSE — excludes `chunk_text` (copyright, payload size)
- Error mid-stream: emit `error` event, still log trace with partial answer
- StreamingResponse headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`, `Connection: keep-alive`

---

### Step 5: Router Registration

**File**: `apps/api/src/api/router.py` (modify)

Two-line change:
- Add `chat` to import: `from src.api import chat, health, profile`
- Add router: `api_router.include_router(chat.router)`

---

### Pitfalls to Watch

1. **`.maybe_single()` not `.single()`** — Supabase `.single()` throws on 0 rows. Use `.maybe_single()` for ownership checks where "not found" is normal.

2. **Sync Supabase in async route** — `supabase-py` is synchronous. DB calls in the SSE handler happen before/after streaming, not during. Acceptable for dev. Can wrap in `asyncio.to_thread()` later if needed.

3. **Gemini rate limits** — Title gen adds a 2nd LLM call per first message. 10 RPM free tier is fine for dev. Fire-and-forget means a 429 just logs an error.

4. **CORS for SSE** — Already handled. SSE uses regular HTTP, existing CORS middleware covers it.

---

### Verification

```bash
# 1. Send first message (creates session, streams response)
curl -N -X POST http://localhost:8000/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What rep range is best for hypertrophy?"}'
# Expect: session → citations → data* → done events

# 2. List sessions
curl http://localhost:8000/chat/sessions -H "Authorization: Bearer $TOKEN"

# 3. Get messages
curl http://localhost:8000/chat/sessions/$SID/messages -H "Authorization: Bearer $TOKEN"

# 4. Follow-up (tests history + query rewriting)
curl -N -X POST http://localhost:8000/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "What about for strength?", "session_id": "'$SID'"}'

# 5. Check rag_traces table in Supabase dashboard

# 6. Re-fetch session to verify LLM-generated title
curl http://localhost:8000/chat/sessions/$SID -H "Authorization: Bearer $TOKEN"

# 7. Delete session
curl -X DELETE http://localhost:8000/chat/sessions/$SID -H "Authorization: Bearer $TOKEN"
```

---

### Files Summary

| File | Action | Description |
|------|--------|-------------|
| `apps/api/src/schema/rag.py` | Modify | Add ChatMessageRequest, SessionResponse, MessageResponse, CitationPayload |
| `apps/api/src/core/trace_logger.py` | Create | Fire-and-forget RAG trace logging |
| `apps/api/src/service/chat_service.py` | Create | Session CRUD + message persistence |
| `apps/api/src/api/chat.py` | Create | SSE streaming endpoint + session REST endpoints |
| `apps/api/src/api/router.py` | Modify | Register chat.router (2-line change) |

---

## Phase 7: Frontend Chat UI — ✅ Complete

### What Was Built

Connects the React frontend to the Phase 6 RAG backend. ChatGPT-like interface at `/dashboard/chat` with SSE streaming responses, inline clickable citations, grouped citation cards, session history sidebar, suggested questions, and markdown rendering.

### Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Session sidebar | Collapsible left panel inside ChatScreen | Self-contained, doesn't touch dashboard layout |
| Citations | Grouped by paper, sections + page ranges listed inside card | Deduplicates multi-chunk papers, shows context at a glance |
| Inline citations | Clickable `[Author, Year]` in LLM response → scroll to card with highlight | Connects text claims to source cards |
| Markdown rendering | `react-markdown` + `remark-gfm` | LLM returns structured markdown |
| SSE client | Raw `fetch` + `ReadableStream` | `EventSource` is GET-only |
| State management | Local `useChat` hook (not context) | Chat state only needed within chat feature |
| Token access | `useChat` calls `useAuth()` internally | Clean encapsulation |
| Retry | Store last failed message text, re-send on click | Better UX than manual re-submit |

### Implementation Details

**Types** (`features/chat/types/index.ts`) — Citation, ChatSession, ChatMessageData, StreamingMessage, SendMessageRequest, SSECallbacks. Snake_case matching backend wire format (no mapping layer).

**Service** (`features/chat/services/chatService.ts`) — REST wrappers using `apiRequest()` for sessions/messages. `sendMessageSSE()` with custom fetch + ReadableStream + buffer accumulation pattern (split on `\n\n`, keep incomplete tail). Dispatches parsed events to typed callbacks.

**Hook** (`features/chat/hooks/useChat.ts`) — State: sessions, activeSessionId, messages, streamingMessage (separate from messages array), isLoading, isSending, error, lastFailedMessage. Functional state updates in `onData` callback (stale closure safety). AbortController cleanup on unmount/session switch. 3s delay re-fetch for auto-title.

**Components** (7 files):
- `TypingIndicator` — animated bouncing dots with staggered delay
- `CitationCard` — `groupCitations()` deduplicates by paper (title::year key). `cleanSection()` strips leading numbers ("5. Discussion" → "Discussion") and deduplicates repeated names ("5. Conclusion 5. Conclusion" → "Conclusion"). `normalizeCiteKey()` (lowercase surname + year) for matching inline citations. DOI links, category color badges, sections with page ranges.
- `SuggestedQuestions` — 4 exercise science questions, 2x2 grid on desktop
- `ChatMessage` — `processCitations()` converts `[Author, Year]` in markdown to `#cite::key` hash links (avoids react-markdown URL sanitization stripping `cite://` protocol). Custom `a` component detects hash links, renders as styled buttons, on click scrolls to matching card (`data-cite-key` attribute) with `scrollIntoView({ block: 'center' })` + 1.5s ring highlight. Handles `cited in` pattern — links to the paper we have. react-markdown + remark-gfm with Tailwind-styled component overrides.
- `ChatInput` — auto-resize textarea (reset height to 'auto' before reading scrollHeight), Enter sends, Shift+Enter newlines, disabled during streaming
- `ChatMessageList` — auto-scroll when near bottom (threshold 100px), `behavior: 'auto'` during streaming / `'smooth'` otherwise
- `SessionSidebar` — renders `null` when closed (no fixed positioning, no z-index conflicts with nav sidebar). ChevronLeft to collapse, ChevronRight in header to expand.

**ChatScreen** — Edge-to-edge layout via `-m-6` + `h-screen`. Error banner with Retry button (re-sends stored failed message). Loading spinner for session switches.

### Key Patterns

- **Streaming message separation** — `streamingMessage` lives outside `messages` array until `onDone`, then converts to `ChatMessageData` and pushes to messages. Clean separation of history vs in-flight.
- **Optimistic UI** — User message appears instantly (temp ID), session deletion removes from local state before API confirms.
- **Citation linking** — `processCitations()` regex: `\[([^\[\]]+?,\s*(\d{4})[^\[\]]*)\](?!\()` — matches `[Author, Year, p. X]` but not existing markdown links. For `cited in` patterns, extracts the target paper (after "cited in") since that's the one in our corpus.
- **URL sanitization workaround** — react-markdown strips unknown protocols like `cite://`. Using `#cite::key` hash links instead, which pass through sanitization.

### Gotchas

- `TextDecoder` `{ stream: true }` option goes on `.decode()` call, not constructor
- `react-markdown` sanitizes URLs — unknown protocols stripped, use hash links instead
- `scrollIntoView({ block: 'nearest' })` doesn't scroll enough for citation cards — use `block: 'center'`
- Sidebar must not use `fixed` positioning — conflicts with nav sidebar z-index. Render `null` when closed instead.
- `-m-6` counteracts DashboardLayout `p-6` — if parent padding changes, this breaks
- `h-screen` for full-height chat (not `h-[calc(100vh-48px)]` which left a gap)

---

## Phase 8: Automated RAG Evaluation Pipeline

### Context

Phases 1-7 of the RAG chatbot are complete (DB schema, ingestion, retrieval, generation, chat API, frontend UI). The pipeline works end-to-end, but we have no systematic way to measure quality. Without evaluation, we can't know if changing chunk size, embedding model, or prompt improves or degrades performance.

Phase 8 builds a fully custom LLM-as-judge eval pipeline (no DeepEval/RAGAS — custom for learning). It scores 5 metrics against a test dataset, producing a report with per-question and aggregate scores.

### Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Judge mode | Separate default + `--combined` flag | Default: 5 individual judge calls for learning depth. `--combined` flag: 1 call scores all 5 metrics for faster iteration (2 vs 7 Gemini calls/case) |
| Chunk text | Full (no truncation) | Faithfulness needs complete chunk text; Gemini 1M context handles it easily |
| Code location | `src/core/eval/` package | Consistent with project patterns; clean imports from scripts + tests |
| Multi-turn | Deferred | Single-turn only; query rewriting already verified in Phase 5 |
| Dataset size | ~20 initial, expand to 35 | Stay under 250 RPD during iteration (20 × 7 = 140 calls/run) |
| Scoring scale | 1-5 integer | Good LLM judge granularity; Likert-scale alignment |
| Judge temperature | 0.0 | Maximize determinism/reproducibility |
| Score extraction | JSON with regex fallback | Gemini reliably produces JSON; regex handles edge cases |
| Reference format | Expected facts list | More robust than full expected answers |
| Rate limiting (within case) | Inter-call delay (5s) between judge calls + retry wrapper on rag_query in runner | 5s between judge calls keeps rate at ~6-7 RPM (under 10 RPM limit). `_generate_with_retry()` in judge.py as safety net. Runner wraps `rag_query()` with retry since it calls `generate()` which has no built-in retry. Prevents both burst 429s and unprotected RAG failures. |
| Judge model | Configurable `--judge-model` flag, default same model (Gemini 2.5 Flash) | Same-model bias is a known LLM-as-judge concern (may inflate faithfulness scores). Default to Gemini for simplicity (no new API keys), but `--judge-model` flag + `judge_model` in report metadata lets us swap to GPT-4o/Claude later for cross-validation. Learn now, improve later. |
| Daily quota awareness | Add `--dry-run` flag | Separate mode = 140 calls/run (56% of 250 RPD). Running 2x/day blows quota. `--dry-run` prints expected call count before running so you don't burn quota accidentally. Combined mode = 40 calls/run (16%) gives much more headroom for iteration. |

### File Structure

```
apps/api/
├── src/core/eval/
│   ├── __init__.py              # Exports
│   ├── judge.py                 # 5 judge prompt templates + score extraction
│   ├── runner.py                # EvalRunner class (orchestration, rate limiting)
│   └── report.py                # Console summary + JSON report generation
│
├── scripts/
│   └── evaluate_rag.py          # CLI wrapper (argparse → EvalRunner)
│
└── tests/eval/
    ├── __init__.py
    ├── conftest.py              # pytest marker registration + fixtures
    ├── test_dataset.json        # ~20 test cases (expand to 35 later)
    └── test_rag_eval.py         # Threshold-based pytest assertions
```

### Implementation Steps

#### Step 1: Test Dataset (`tests/eval/test_dataset.json`)

Each test case:
```json
{
    "id": "HYP-001",
    "question": "What rep range is best for muscle hypertrophy?",
    "category": null,
    "expected_facts": [
        "Hypertrophy can occur across a wide range of rep ranges",
        "Training close to failure matters more than specific rep range",
        "Traditional 6-12 rep range is effective but not exclusively superior"
    ],
    "expected_papers": ["Schoenfeld 2021", "Bernardez-Vazquez 2022"],
    "difficulty": "easy",
    "tags": ["hypertrophy", "rep-ranges", "multi-paper"]
}
```

Distribution (~20 cases):
- ~6 hypertrophy (easy/medium/hard) — draws from Schoenfeld 2021, Bernardez-Vazquez 2022, Krzysztofik 2019
- ~6 strength (easy/medium/hard) — draws from Travis 2020, Androulakis-Korakakis 2021, Latella 2020, Thompson 2020
- ~4 nutrition (easy/medium) — draws from Wax 2021, Kazeminasab 2025 (both creatine-focused)
- ~2 cross-category
- ~2 out-of-scope (should return grounded=false)

Verify expected_facts and expected_papers using existing `test_retrieval.py` and `test_rag_pipeline.py` scripts before finalizing.

---

#### Step 2: Judge Module (`src/core/eval/judge.py`)

Two modes: **separate** (default) and **combined** (`--combined` flag).

##### Separate Mode (default) — 5 individual judge calls

**Metric 1 — Contextual Relevancy**: Are retrieved chunks relevant to the question?
- Input: question + chunks
- Rubric: 5=all highly relevant → 1=mostly irrelevant

**Metric 2 — Contextual Recall**: Do chunks contain the expected facts?
- Input: expected_facts + chunks
- Rubric: 5=all facts found → 1=none found
- Extra output: `fact_coverage` mapping each fact → supported/partial/not_found

**Metric 3 — Contextual Precision**: Are the most relevant chunks ranked highest?
- Input: question + chunks (with rank/similarity)
- Rubric: 5=best chunks at top → 1=inverted ranking

**Metric 4 — Answer Relevancy**: Does the answer address the question?
- Input: question + answer
- Rubric: 5=complete direct answer → 1=off-topic

**Metric 5 — Faithfulness**: Is the answer faithful to chunks (no hallucination)?
- Input: chunks (FULL text) + answer
- Rubric: 5=zero hallucination → 1=mostly hallucinated
- Extra output: `unsupported_claims` list

##### Combined Mode (`--combined`) — 1 judge call scores all 5

Single prompt containing question, expected_facts, chunks, and answer. LLM returns JSON with all 5 metric scores + reasoning in one response. Faster iteration (2 Gemini calls/case vs 7), useful once prompts are tuned.

##### Shared Infrastructure

Each prompt instructs the LLM to return JSON:
```json
{"score": 4, "reasoning": "..."}
```

Score extraction: parse JSON first, regex fallback for `Score: X` pattern.

Helper functions:
- `_format_chunks_for_judge(chunks)` — formats with metadata + full text
- `_generate_with_retry(prompt, system, judge_model)` — retry on 429 with backoff (2s, 5s, 10s). Accepts optional `judge_model` override; defaults to `config.LLM_MODEL`.
- `extract_score(response)` → `(score: int, reasoning: str, extra: dict)`

Rate limiting within test cases:
- `inter_call_delay` parameter (default 5.0s) — `asyncio.sleep()` between each separate judge call
- Keeps effective rate at ~6-7 RPM (well under 10 RPM Gemini free tier limit)
- Combined mode skips inter-call delay (only 1 judge call)

Dataclasses:
- `MetricScore(score: int, reasoning: str, extra: dict)`
- `JudgeResult` — contains all 5 `MetricScore` fields

Public API:
- `judge_contextual_relevancy(question, chunks) → MetricScore`
- `judge_contextual_recall(expected_facts, chunks) → MetricScore`
- `judge_contextual_precision(question, chunks) → MetricScore`
- `judge_answer_relevancy(question, answer) → MetricScore`
- `judge_faithfulness(chunks, answer) → MetricScore`
- `judge_combined(question, expected_facts, chunks, answer) → JudgeResult` — 1 call, all 5 metrics
- `judge_all(question, expected_facts, chunks, answer, combined=False, inter_call_delay=5.0) → JudgeResult` — dispatches to combined or separate; adds `asyncio.sleep(inter_call_delay)` between separate calls

---

#### Step 3: Eval Runner (`src/core/eval/runner.py`)

`EvalRunner` class:

```python
class EvalRunner:
    def __init__(self, min_delay: float = 7.0, verbose: bool = False, combined: bool = False, inter_call_delay: float = 5.0, judge_model: str | None = None)
    async def evaluate_single(self, test_case: dict) -> EvalTestResult
    async def run(self, dataset: list[dict]) -> dict  # full report
```

Flow per test case:
1. Call `rag_query(question, category=category)` → `RAGResult` — wrapped with retry logic (3 attempts, backoff 2s→5s→10s on RuntimeError from 429)
2. Call `judge_all(question, expected_facts, chunks, answer, combined=self.combined, inter_call_delay=self.inter_call_delay)` → `JudgeResult`
3. Compute `overall_score` = mean of 5 metric scores
4. Return `EvalTestResult` with scores, RAG metadata, timing, error

Rate limiting:
- Sequential processing (not parallel)
- `min_delay` seconds between test cases (default 7s)
- `inter_call_delay` seconds between judge calls within a test case (default 5s)
- Separate mode: ~37s per test case (1 RAG + 5 judges × 5s delay + 7s between cases), ~12 min for 20 cases
- Combined mode: ~12s per test case (1 RAG + 1 judge + 7s between cases), ~4 min for 20 cases
- Separate mode: 20 cases × 6 calls = 120 Gemini calls/run (+ 20 embed calls to Voyage)
- Combined mode: 20 cases × 2 calls = 40 Gemini calls/run (+ 20 embed calls to Voyage)

Error handling:
- Each test case is independent — one failure doesn't stop the run
- `rag_query()` wrapped with retry (3 attempts) — catches `RuntimeError` from Gemini 429s
- Failed cases marked with `error` field, excluded from aggregates
- 429 errors also retried in `_generate_with_retry()` (judge.py)

`EvalTestResult` dataclass:
```python
@dataclass
class EvalTestResult:
    id: str
    question: str
    category: str | None
    difficulty: str
    tags: list[str]
    scores: dict | None          # JudgeResult as dict
    overall_score: float | None
    rag_result: dict | None      # answer, grounded, chunks_retrieved, papers, timing
    error: str | None
```

---

#### Step 4: Report Generator (`src/core/eval/report.py`)

Two output modes:

**Console summary** (always printed):
```
================================================================
RAG Evaluation Report — 2026-03-11
Model: gemini-2.5-flash | Judge: gemini-2.5-flash | Cases: 20 run, 0 failed
Mode: separate | Duration: 12m 34s
================================================================

AGGREGATE SCORES (mean +/- std)
  Contextual Relevancy:   4.2 +/- 0.6
  Contextual Recall:      3.8 +/- 0.9
  Contextual Precision:   4.0 +/- 0.7
  Answer Relevancy:       4.5 +/- 0.5
  Faithfulness:           4.6 +/- 0.4
  Overall:                4.22

BY CATEGORY
  hypertrophy (n=6):  Rel=4.3  Rec=4.0  Pre=4.1  Ans=4.6  Fai=4.7
  strength (n=6):     Rel=4.1  Rec=3.6  Pre=3.9  Ans=4.4  Fai=4.5
  ...

WORST PERFORMERS (bottom 3)
  1. STR-005 (2.8) — Faithfulness=2, Recall=3
  ...
================================================================
```

**JSON report** (saved to file with `--output`):
- `metadata`: timestamp, model, judge_model, top_k, threshold, dataset path, duration, judge_mode ("separate"|"combined")
- `aggregate`: mean/std/min/max per metric + overall
- `by_category` and `by_difficulty` breakdowns
- `results`: full per-case detail (scores, reasoning, RAG result, error)

Functions:
- `compute_aggregates(results) → dict`
- `print_summary(report) → None`
- `save_json_report(report, path) → None`

---

#### Step 5: CLI Script (`scripts/evaluate_rag.py`)

Thin wrapper around `EvalRunner`:

```bash
# Full run (separate judges, default)
python -m scripts.evaluate_rag

# Combined judge mode (faster, 1 call per test case)
python -m scripts.evaluate_rag --combined

# Dry run (print expected call count, don't execute)
python -m scripts.evaluate_rag --dry-run
python -m scripts.evaluate_rag --combined --dry-run

# Specific test cases
python -m scripts.evaluate_rag --ids HYP-001 NUT-001

# Only retrieval metrics (skip answer_relevancy + faithfulness)
python -m scripts.evaluate_rag --metrics retrieval

# Only generation metrics (skip contextual_*)
python -m scripts.evaluate_rag --metrics generation

# Custom judge model (cross-validation)
python -m scripts.evaluate_rag --judge-model gpt-4o

# Custom dataset
python -m scripts.evaluate_rag --dataset path/to/custom.json

# Save JSON report
python -m scripts.evaluate_rag --output results/eval_001.json

# Verbose (print each question as it runs)
python -m scripts.evaluate_rag --verbose
```

`--dry-run` output example:
```
DRY RUN — Phase 8 RAG Evaluation
  Dataset: tests/eval/test_dataset.json (20 cases)
  Mode: separate
  Judge model: gemini-2.5-flash
  Expected Gemini calls: 120 (of 250 RPD limit = 48%)
  Expected Voyage calls: 20
  Estimated duration: ~12 min
```

---

#### Step 6: Pytest Integration (`tests/eval/`)

**conftest.py**: Register `eval` marker, provide `test_dataset` and `eval_results` session fixtures.

**test_rag_eval.py**: Threshold-based assertions:
```python
THRESHOLDS = {
    "contextual_relevancy": 3.5,
    "contextual_recall": 3.0,
    "contextual_precision": 3.5,
    "answer_relevancy": 3.5,
    "faithfulness": 4.0,  # Highest bar
    "overall": 3.5,
}
```

Tests:
- Each metric above its threshold
- No test case errors
- No score of 1 (catastrophic failure)
- Out-of-scope questions return grounded=false

Run with: `pytest tests/eval/ -m eval -v`

Thresholds set AFTER first baseline run (run eval → see scores → set thresholds at mean - 0.5).

**pytest.ini** (or pyproject.toml): Register the `eval` marker so `pytest` doesn't warn.

---

### Critical Files to Modify/Read

| File | Action | Why |
|------|--------|-----|
| `src/core/rag_pipeline.py` | Read only | `rag_query()` is the eval target |
| `src/core/llm_provider.py` | Read only | `generate()` reused as judge LLM |
| `src/schema/rag.py` | Read only | `RAGResult`, `ChunkResponse` types consumed by eval |
| `scripts/test_rag_pipeline.py` | Read only | Pattern reference for CLI script (argparse, asyncio.run) |
| `scripts/reingest_all.py` | Read only | Paper metadata for building test dataset |

### Verification

1. Run `python -m scripts.evaluate_rag --dry-run` — confirm call count math
2. Run `python -m scripts.evaluate_rag --verbose --output results/baseline.json` from `apps/api/`
3. Confirm all 20 test cases complete without errors
4. Review per-case reasoning in JSON report — sanity-check that judge scores match human intuition
5. Set pytest thresholds based on baseline scores
6. Run `pytest tests/eval/ -m eval -v` — confirm all threshold tests pass

### Dependencies

None new. Uses only:
- `src/core/rag_pipeline.rag_query()` (existing)
- `src/core/llm_provider.generate()` (existing)
- Standard library: `json`, `re`, `statistics`, `asyncio`, `time`, `argparse`, `pathlib`, `dataclasses`, `logging`
- `pytest` (already installed)

---

## Corpus Expansion — 15 New Nutrition Papers

### Context
Original corpus was 9 papers (3 hypertrophy, 1 nutrition, 5 strength). Expanded with 15 CC-BY nutrition papers from PMC Open Access Subset to improve coverage for evaluation and user queries.

### Papers Added
All CC-BY licensed, sourced from PMC with `cc by license[filter]`:

**Protein & MPS**:
- Cintineo et al. 2018 — Protein supplementation effects on performance & recovery (Frontiers in Nutrition)
- Zhao et al. 2024 — Protein intake & athletic performance meta-analysis (Frontiers in Nutrition)
- Davies et al. 2024 — Muscle protein synthetic response to resistance exercise (Translational Sports Medicine)
- Gwin et al. 2020 — MPS responses to EAAs, intact protein, mixed meals (Nutrients)
- Pearson et al. 2023 — Protein supplementation & recovery from exercise-induced muscle damage (European J Clinical Nutrition)
- Roth et al. 2022 — Lean mass sparing during caloric restriction (European J Applied Physiology)

**Nutrient Timing & Pre-Sleep Protein**:
- Arent et al. 2020 — Nutrient timing review (Nutrients)
- Trommelen & van Loon 2016 — Pre-sleep protein ingestion (Nutrients)
- Snijders et al. 2019 — Pre-sleep protein update (Frontiers in Nutrition)

**Supplements**:
- Antonio et al. 2024 — Top 5 sport supplements (Nutrients)
- Grgic et al. 2018 — Caffeine effects on strength & power meta-analysis (JISSN)
- Trexler et al. 2015 — ISSN position stand: beta-alanine (JISSN)
- Bird et al. 2024 — Supplementation strategies for strength/power athletes (Nutrients)

**Recovery & Sleep**:
- Mielgo-Ayuso & Fernández-Lázaro 2021 — Nutrition and muscle recovery (Nutrients)
- Doherty et al. 2019 — Sleep and nutrition interactions for athletes (Nutrients)

### Ingestion Results
- All 15 papers ingested successfully (0 failures)
- Total corpus: 24 papers, 909 chunks
- Metadata in `papers/manifest.json` and `scripts/reingest_all.py`

---

## Ingestion Quality Fixes — Title-Level Font Group Skip

### Problem
Some papers had font size hierarchy misclassification in `_classify_major_headers()`. Title-level or page-label font groups (≤2 members) at a larger font size were classified as major headers, pushing the real section headers to minor.

**Affected papers**:
- **Davies et al. 2024** (TSMED) — Paper title at 17.9pt (2 headers) classified as major. Real sections at 12.0pt (12 headers) classified as minor. Result: 1 section instead of 13.
- **Trexler et al. 2015** (JISSN) — Page labels "REVIEW", "Open Access" at 13.0pt (2 headers) classified as major. Real sections at 9.2pt (13 headers) missed. Result: 2 wrong sections instead of 16.
- **Grgic et al. 2018** (JISSN) — Same JISSN page label issue at 13.0pt. Real sections at 10.3pt (6 headers) missed. Result: 2 wrong sections instead of 8.

### Fix
Changed the title-level skip logic in `_classify_major_headers()` from a single `if` check to a `while` loop:

```python
# Before (single skip):
if (len(qualifying) >= 2
        and len(qualifying[0][1]) <= 2
        and len(qualifying[1][1]) >= 3):
    qualifying = qualifying[1:]

# After (chain skip):
while (len(qualifying) >= 2
        and len(qualifying[0][1]) <= 2
        and any(len(q[1]) >= 3 for q in qualifying[1:])):
    qualifying = qualifying[1:]
```

**Why while loop**: Trexler 2015 has TWO small font groups before the real sections:
- 23.4pt (1 member) — title, already filtered by single-member check
- 13.0pt (2 members) — "REVIEW", "Open Access" page labels
- 10.3pt (2 members) — "Abstract", "Introduction" (separate from main sections)
- 9.2pt (13 members) — real content sections

The single `if` could only skip one group. The `while` loop skips the chain of small groups until it reaches the real sections.

### Results After Fix
| Paper | Before | After |
|-------|--------|-------|
| Davies 2024 | 1 section (35 chunks) | 13 sections (42 chunks) |
| Trexler 2015 | 2 wrong sections | 16 sections (32 chunks) |
| Grgic 2018 | 2 wrong sections | 8 sections (24 chunks) |
| All other papers | unchanged | unchanged |

Regression tested across all 24 papers — no changes to any other paper's section count.

