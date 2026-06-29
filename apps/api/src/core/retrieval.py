import logging
import time

from src.core.embedding_provider import embed_query
from src.db import get_supabase
from src.schema.rag import ChunkResponse, RetrievalResult
from src.utils.config import config

logger = logging.getLogger(__name__)

# Sentinel that disables the similarity floor on the deep fetch. We can't pass 0.0:
# retrieve_chunks resolves the threshold with `x or config.RAG_SIMILARITY_THRESHOLD`,
# and 0.0 is falsy, so it would snap back to 0.3. -1.0 is truthy AND below any real
# cosine similarity, so it lets every candidate through to the reranker.
_NO_FLOOR = -1.0


async def retrieve_chunks(
    query: str,
    top_k: int | None = None,
    category: str | None = None,
    similarity_threshold: float | None = None,
    ef_search: int | None = None,
) -> RetrievalResult:
    """Embed a query and retrieve the most relevant chunks from the vector DB.

    Args:
        query: The user's question.
        top_k: Number of chunks to return (defaults to config.RAG_TOP_K).
        category: Optional category filter (e.g. "nutrition"). None = all.
        similarity_threshold: Minimum cosine similarity (defaults to config.RAG_SIMILARITY_THRESHOLD).
        ef_search: Optional HNSW search beam width. None = leave the DB default (40)
            untouched. Set >= top_k for deep candidate fetches, else recall degrades
            past rank ~40 (approximate results).

    Returns:
        RetrievalResult with matched chunks, query text, and timing.
    """
    start = time.perf_counter()

    # 1. Embed the query
    embed_start = time.perf_counter()
    embedding = await embed_query(query)
    embedding_time_ms = (time.perf_counter() - embed_start) * 1000

    # 2. Call match_chunks RPC
    rpc_params = {
        "query_embedding": embedding,
        "match_count": top_k or config.RAG_TOP_K,
        "similarity_threshold": similarity_threshold or config.RAG_SIMILARITY_THRESHOLD,
        "filter_category": category,
    }
    if ef_search is not None:
        rpc_params["ef_search"] = ef_search
    result = get_supabase().rpc("match_chunks", rpc_params).execute()

    # 3. Parse rows into ChunkResponse objects
    chunks = [ChunkResponse(**row) for row in result.data]

    # 4. Log results
    elapsed_ms = (time.perf_counter() - start) * 1000
    truncated_query = query[:80] + "..." if len(query) > 80 else query

    if chunks:
        sim_min = min(c.similarity for c in chunks)
        sim_max = max(c.similarity for c in chunks)
        logger.info(
            f"Retrieved {len(chunks)} chunks for \"{truncated_query}\" "
            f"(similarity {sim_min:.3f}-{sim_max:.3f}, {elapsed_ms:.0f}ms)"
        )
    else:
        logger.info(
            f"No chunks found for \"{truncated_query}\" ({elapsed_ms:.0f}ms)"
        )

    return RetrievalResult(
        chunks=chunks,
        query=query,
        retrieval_time_ms=elapsed_ms,
        embedding_time_ms=embedding_time_ms,
    )


async def retrieve_reranked(
    query: str,
    top_n: int | None = None,
    category: str | None = None,
    fetch_depth: int | None = None,
    ef_search: int | None = None,
    per_paper_cap: int | None = None,
    similarity_threshold: float | None = None,
) -> RetrievalResult:
    """Deep-fetch + cross-encoder rerank + per-paper cap retrieval (Phase 2 step 9').

    The two-stage funnel: a wide bi-encoder fetch (`fetch_depth` candidates, no floor)
    feeds a cross-encoder that rescores for true relevance, then a per-paper cap breaks
    single-paper saturation, then we truncate to `top_n`.

    This is the single orchestration site shared by rag_query/rag_query_stream and the
    measurement scripts — keeping retrieve_chunks a pure vector primitive.

    Args:
        query: The user's question.
        top_n: Final chunk count (defaults to config.RERANK_TOP_N).
        category: Optional category filter. None = all.
        fetch_depth: Candidate pool size for the deep fetch (defaults to RERANK_FETCH_DEPTH).
        ef_search: HNSW beam width for the deep fetch (defaults to RERANK_EF_SEARCH).
            Must be >= fetch_depth or the pool's tail is approximate.
        per_paper_cap: Max chunks per paper in the final result (defaults to
            RERANK_PER_PAPER_CAP).
        similarity_threshold: Floor for the deep fetch. None defaults to
            config.RERANK_FETCH_THRESHOLD; a configured 0.0 means "no floor" and is
            translated to -1.0 (see _NO_FLOOR). The floor must be off so the reranker
            can rescue low-vector-similarity-but-relevant chunks.

    Returns:
        RetrievalResult with the capped+reranked chunks, plus rerank timing.
    """
    # Imported here (not module-top) so importing retrieval.py never pulls flashrank —
    # keeps the lean CI path and vector-only callers free of the ONNX dependency.
    from src.core.reranker import apply_per_paper_cap, rerank

    top_n = top_n or config.RERANK_TOP_N
    fetch_depth = fetch_depth or config.RERANK_FETCH_DEPTH
    ef_search = ef_search or config.RERANK_EF_SEARCH
    per_paper_cap = per_paper_cap if per_paper_cap is not None else config.RERANK_PER_PAPER_CAP
    floor = similarity_threshold if similarity_threshold is not None else config.RERANK_FETCH_THRESHOLD
    if floor == 0.0:
        floor = _NO_FLOOR

    # Stage 1: wide, unfiltered bi-encoder fetch.
    fetch = await retrieve_chunks(
        query=query,
        top_k=fetch_depth,
        category=category,
        similarity_threshold=floor,
        ef_search=ef_search,
    )

    # Stage 2: cross-encoder rerank (whole pool), then per-paper cap, then truncate.
    rerank_start = time.perf_counter()
    reranked = await rerank(query, fetch.chunks)
    rerank_time_ms = (time.perf_counter() - rerank_start) * 1000
    capped = apply_per_paper_cap(reranked, cap=per_paper_cap, top_n=top_n)

    logger.info(
        f"Reranked {len(fetch.chunks)} candidates -> {len(capped)} chunks "
        f"(fetch_depth={fetch_depth}, ef_search={ef_search}, cap={per_paper_cap}, "
        f"rerank={rerank_time_ms:.0f}ms)"
    )

    return RetrievalResult(
        chunks=capped,
        query=query,
        retrieval_time_ms=fetch.retrieval_time_ms,
        embedding_time_ms=fetch.embedding_time_ms,
        rerank_time_ms=rerank_time_ms,
    )
