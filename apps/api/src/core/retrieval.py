import logging
import time

from src.core.embedding_provider import embed_query
from src.db import get_supabase
from src.schema.rag import ChunkResponse, RetrievalResult
from src.utils.config import config

logger = logging.getLogger(__name__)


async def retrieve_chunks(
    query: str,
    top_k: int | None = None,
    category: str | None = None,
    similarity_threshold: float | None = None,
) -> RetrievalResult:
    """Embed a query and retrieve the most relevant chunks from the vector DB.

    Args:
        query: The user's question.
        top_k: Number of chunks to return (defaults to config.RAG_TOP_K).
        category: Optional category filter (e.g. "nutrition"). None = all.
        similarity_threshold: Minimum cosine similarity (defaults to config.RAG_SIMILARITY_THRESHOLD).

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
