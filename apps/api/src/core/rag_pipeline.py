"""RAG generation pipeline — bridges retrieval and LLM generation.

Given a user question (and optional conversation history):
1. Rewrite the query if history exists (so follow-ups retrieve well)
2. Retrieve relevant chunks via vector search
3. Format chunks into a citation-aware prompt
4. Generate a cited answer via the LLM

Two entry points:
- rag_query()        → non-streaming, returns full RAGResult (for eval pipeline)
- rag_query_stream() → streaming, returns StreamingRAGResult with .stream generator (for chat UI)
"""

import logging
import time

from src.core.llm_provider import generate, generate_stream
from src.core.retrieval import retrieve_chunks
from src.schema.rag import (
    ChatMessage,
    ChunkResponse,
    RAGResult,
    StreamingRAGResult,
)
from src.utils.config import config

logger = logging.getLogger(__name__)

# --- Constants ---

SYSTEM_PROMPT = """\
You are an exercise science assistant for Flame Fitness. Your job is to answer \
questions about training, nutrition, and recovery using the provided research sources.

Rules:
1. Base your answer ONLY on the provided sources. For every claim, cite the source \
as [Author, Year, p. X] (e.g. [Schoenfeld, 2021, p. 5]). If the source spans multiple \
pages, use [Author, Year, pp. X-Y].
2. Explain concepts at a beginner-friendly level. Avoid jargon unless you define it.
3. If the sources contain conflicting findings, acknowledge the disagreement and \
explain both sides.
4. If the sources don't contain enough information to answer confidently, say \
"I don't have enough research to answer this confidently" rather than guessing.
5. Do NOT fabricate citations or information not present in the sources.
6. Keep answers focused and well-structured. Use short paragraphs or bullet points \
for readability.\
"""

NO_CHUNKS_INSTRUCTION = """\
No relevant research papers were found in the database for this question. \
You may answer from your general knowledge, but you MUST:
1. Clearly state that this answer is NOT backed by sources from the research database.
2. Preface your answer with: "I don't have specific research papers on this topic, \
but based on general exercise science knowledge:"
3. Keep the answer brief since it cannot be verified against the literature.\
"""

REWRITE_PROMPT = """\
Given the conversation history and a follow-up question, rewrite the follow-up \
as a standalone question that captures the full intent. The rewritten question \
should make sense without any conversation context and be optimized for searching \
a research paper database.

Return ONLY the rewritten question, nothing else.

Conversation history:
{history}

Follow-up question: {query}

Rewritten question:\
"""

# Hardcoded — low temperature for faithfulness to sources
_RAG_TEMPERATURE = 0.3
_RAG_MAX_TOKENS = 8192


# --- Internal helpers ---


async def _rewrite_query(
    query: str,
    history: list[ChatMessage] | None,
) -> str:
    """Rewrite a follow-up query as standalone using conversation history.

    First message (no history) returns the query unchanged — no LLM call.
    Follow-ups get rewritten so vector search retrieves relevant chunks
    even for queries like "tell me more about that."
    """
    if not history:
        return query

    # Format history as readable text for the rewrite prompt
    history_text = "\n".join(
        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
        for msg in history
    )

    rewritten = await generate(
        prompt=REWRITE_PROMPT.format(history=history_text, query=query),
        temperature=0.0,  # Deterministic rewrite
        max_tokens=256,
    )
    rewritten = rewritten.strip()

    logger.info(
        f"Query rewritten: \"{query[:60]}\" → \"{rewritten[:60]}\""
    )
    return rewritten


def _build_sources_block(chunks: list[ChunkResponse]) -> str:
    """Format retrieved chunks as labeled sources for the LLM prompt.

    Labels use [Author, Year] format so the LLM cites in the same style.
    Includes page numbers when available for precise citations.
    """
    sources = []
    for chunk in chunks:
        # Build label: [Wax et al., 2021]
        label = f"[{chunk.authors}, {chunk.year}]"

        # Build metadata line: (Journal) [Section: X] [Pages: 5-6]
        meta_parts = []
        if chunk.journal:
            meta_parts.append(f"({chunk.journal})")
        if chunk.section:
            meta_parts.append(f"[Section: {chunk.section}]")
        if chunk.page_start:
            if chunk.page_end and chunk.page_end != chunk.page_start:
                meta_parts.append(f"[Pages: {chunk.page_start}-{chunk.page_end}]")
            else:
                meta_parts.append(f"[Page: {chunk.page_start}]")

        meta = " ".join(meta_parts)
        header = f"{label} {meta}".strip()

        sources.append(f"{header}:\n\"{chunk.chunk_text}\"")

    return "\n\n".join(sources)


def build_rag_prompt(query: str, chunks: list[ChunkResponse]) -> str:
    """Build the user-turn prompt with sources and question.

    The system prompt is NOT included here — it goes via the `system`
    parameter to generate()/generate_stream() separately.
    """
    if chunks:
        sources_block = _build_sources_block(chunks)
        return (
            f"Sources:\n{sources_block}\n\n"
            f"Question: {query}"
        )
    else:
        return (
            f"{NO_CHUNKS_INSTRUCTION}\n\n"
            f"Question: {query}"
        )


# --- Public API ---


async def rag_query(
    query: str,
    history: list[ChatMessage] | None = None,
    top_k: int | None = None,
    category: str | None = None,
) -> RAGResult:
    """Full RAG pipeline — non-streaming. Returns complete RAGResult.

    Used by the eval pipeline (Phase 8) where we need the full answer
    to score against ground truth.
    """
    # 1. Rewrite query if history exists
    rewritten = await _rewrite_query(query, history)
    search_query = rewritten if rewritten != query else query

    # 2. Retrieve relevant chunks
    retrieval_result = await retrieve_chunks(
        query=search_query,
        top_k=top_k,
        category=category,
    )
    chunks = retrieval_result.chunks
    grounded = len(chunks) > 0

    # 3. Build prompt
    prompt = build_rag_prompt(search_query, chunks)

    # 4. Generate answer
    gen_start = time.perf_counter()
    answer = await generate(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        temperature=_RAG_TEMPERATURE,
        max_tokens=_RAG_MAX_TOKENS,
        messages=history,
    )
    gen_time_ms = (time.perf_counter() - gen_start) * 1000

    logger.info(
        f"RAG query complete: {len(chunks)} chunks, grounded={grounded}, "
        f"retrieval={retrieval_result.retrieval_time_ms:.0f}ms, "
        f"generation={gen_time_ms:.0f}ms"
    )

    return RAGResult(
        answer=answer,
        chunks=chunks,
        query=query,
        rewritten_query=rewritten if rewritten != query else None,
        prompt_sent=prompt,
        retrieval_time_ms=retrieval_result.retrieval_time_ms,
        generation_time_ms=gen_time_ms,
        model=config.LLM_MODEL,
        grounded=grounded,
    )


async def rag_query_stream(
    query: str,
    history: list[ChatMessage] | None = None,
    top_k: int | None = None,
    category: str | None = None,
) -> StreamingRAGResult:
    """Full RAG pipeline — streaming. Returns StreamingRAGResult with lazy .stream.

    Used by the chat UI (Phase 7). Metadata (chunks, grounded, timing) is available
    immediately. The .stream async generator yields text chunks as they arrive
    from the LLM — it is NOT consumed until the caller iterates it.

    Phase 6 route handler reads metadata first (for SSE citation events),
    then iterates .stream for SSE data events.
    """
    # 1. Rewrite query if history exists
    rewritten = await _rewrite_query(query, history)
    search_query = rewritten if rewritten != query else query

    # 2. Retrieve relevant chunks
    retrieval_result = await retrieve_chunks(
        query=search_query,
        top_k=top_k,
        category=category,
    )
    chunks = retrieval_result.chunks
    grounded = len(chunks) > 0

    # 3. Build prompt
    prompt = build_rag_prompt(search_query, chunks)

    # 4. Create stream generator (lazy — not consumed yet)
    stream = generate_stream(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        temperature=_RAG_TEMPERATURE,
        max_tokens=_RAG_MAX_TOKENS,
        messages=history,
    )

    logger.info(
        f"RAG stream ready: {len(chunks)} chunks, grounded={grounded}, "
        f"retrieval={retrieval_result.retrieval_time_ms:.0f}ms"
    )

    return StreamingRAGResult(
        chunks=chunks,
        query=query,
        rewritten_query=rewritten if rewritten != query else None,
        prompt_sent=prompt,
        retrieval_time_ms=retrieval_result.retrieval_time_ms,
        model=config.LLM_MODEL,
        grounded=grounded,
        stream=stream,
    )
