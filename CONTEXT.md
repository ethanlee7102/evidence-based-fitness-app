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

## LLM Decision (Open)

### Current Plan
Gemini 2.0 Flash — chosen as cheapest option, swappable via env var.

### Still To Decide
1. Whether to do a deep dive comparison like we did for embeddings. The provider is designed to be swappable, so this is less critical — can change later without re-processing anything.
2. ~~Verify Voyage AI REST API format~~ ✅ Verified (see below)
3. ~~Verify Gemini REST API format~~ ✅ Verified (see below)

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
- **2D. Dependencies** — pymupdf + langchain-text-splitters added and installed
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

### Section Detection (3 paths + Abstract handling)
Header detection evolved through testing with real papers:

1. **Large font** (>= 1.2x median body font) + short text (<100 chars) → header
2. **Bold + known keyword** — handles papers where headers are same font size but bold. Keywords: abstract, introduction, methods, results, discussion, conclusion(s), references, etc.
3. **Bold + top-level numbered** — regex `^\d+\.\s+\S` catches "3. Exercise and Sports Performance" but not "3.1 Subtopic". Needed because many section titles aren't in the keyword list.
4. **Inline Abstract** — some journals (MDPI/Nutrients) format as `"Abstract: full text..."` in one block. Detects bold "Abstract" first span, splits into header + body.

Normalization strips leading numbers before keyword matching: `"1. Introduction"` → `"introduction"`, `"3.2 Results"` → `"results"`

Fallback: if <= 1 header detected → entire document as one section with `section=None`

### Per-Chunk Page Tracking
Each section carries a `page_map: list[tuple[int, int]]` mapping char offsets to page numbers. After chunking, `_find_page_range()` maps each chunk's text position back to specific pages for accurate citations.

### Supabase Insert Pattern
```python
result = supabase.table("papers").insert(paper_data).execute()
paper_id = result.data[0]["id"]  # auto-generated UUID returned by default
```
supabase-py sends `Prefer: return=representation` by default. Don't include `"id"` in the insert dict — let PostgreSQL generate it via `gen_random_uuid()`.

### Test Results
- **Wax et al. 2021** (creatine review) — 70 chunks, 9 sections detected including Abstract
- **Kazeminasab et al. 2025** (creatine meta-analysis) — 68 chunks, 7 sections detected including Abstract
- Dedup confirmed — re-run skips with "Paper already ingested"
- Retry logic confirmed — triggered on Voyage 429 before payment method was added
- Voyage free tier without payment: 3 RPM / 10K TPM (very restrictive). Adding payment method unlocks normal limits, free tokens still apply.

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
- **Phase 3 implementation** complete and verified — 2 papers ingested, section detection working, dedup working.
- **Migration 007** — `match_chunks` RPC updated to return `token_count`. Requires DROP+CREATE (not CREATE OR REPLACE) due to return type change.
- **Phase 4 implementation** complete — retrieval module, schema updates, migration all in place.
- **PLAN.md** exists at project root — keep phase statuses updated there as work completes.
- **CLAUDE.md** has a reference to PLAN.md at the top.
- **Corpus**: 2 papers ingested (138 chunks total). Both from Nutrients journal, CC-BY licensed. PDFs in `apps/api/papers/` (gitignored).
- **Next**: Phase 5 (RAG Generation Pipeline) — build_rag_prompt, rag_query, rag_query_stream.

