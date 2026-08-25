"""Fire-and-forget RAG trace logging.

Logs each RAG query to the rag_traces table for observability and debugging.
Never blocks the response — errors are caught and logged internally.
"""

import asyncio
import logging
from typing import Optional

from src.db import get_admin_supabase
from src.schema.rag import ChunkResponse

logger = logging.getLogger(__name__)


def _chunks_to_json(chunks: list[ChunkResponse]) -> list[dict]:
    """Convert ChunkResponse list to JSON-serializable dicts.

    Includes full chunk_text for self-contained trace snapshots.
    """
    return [
        {
            "chunk_id": c.chunk_id,
            "paper_id": c.paper_id,
            "chunk_text": c.chunk_text,
            "section": c.section,
            "chunk_index": c.chunk_index,
            "page_start": c.page_start,
            "page_end": c.page_end,
            "token_count": c.token_count,
            "similarity": c.similarity,
            "rerank_score": c.rerank_score,
            "title": c.title,
            "authors": c.authors,
            "year": c.year,
            "journal": c.journal,
            "doi": c.doi,
            "category": c.category,
        }
        for c in chunks
    ]


async def _insert_trace(
    user_id: str,
    session_id: str,
    message_id: str,
    query: str,
    rewritten_query: Optional[str],
    chunks: list[ChunkResponse],
    answer: str,
    model: str,
    grounded: bool,
    retrieval_time_ms: float,
    embedding_time_ms: float,
    generation_time_ms: float,
    rerank_time_ms: float = 0.0,
    error: Optional[str] = None,
) -> None:
    """Insert a trace row into rag_traces. Catches all exceptions."""
    try:
        total_time_ms = retrieval_time_ms + rerank_time_ms + generation_time_ms

        trace_data: dict = {
            "user_id": user_id,
            "session_id": session_id,
            "query": query,
            "rewritten_query": rewritten_query,
            "retrieved_chunks": _chunks_to_json(chunks),
            "chunk_count": len(chunks),
            "llm_response": answer,
            "model": model,
            "grounded": grounded,
            "retrieval_time_ms": round(retrieval_time_ms),
            "embedding_time_ms": round(embedding_time_ms),
            "rerank_time_ms": round(rerank_time_ms),
            "generation_time_ms": round(generation_time_ms),
            "total_time_ms": round(total_time_ms),
            "error": error,
        }
        # Only include message_id if we have one (not set on error)
        if message_id:
            trace_data["message_id"] = message_id

        # System logging, fire-and-forget: uses the admin client (no request token
        # in this background task; RLS insert policy would otherwise need the JWT).
        get_admin_supabase().table("rag_traces").insert(trace_data).execute()
        logger.debug(f"Trace logged for message {message_id}")

    except Exception as e:
        logger.error(f"Failed to log trace: {type(e).__name__}: {e}")


def log_trace(
    user_id: str,
    session_id: str,
    message_id: str,
    query: str,
    rewritten_query: Optional[str],
    chunks: list[ChunkResponse],
    answer: str,
    model: str,
    grounded: bool,
    retrieval_time_ms: float,
    embedding_time_ms: float,
    generation_time_ms: float,
    rerank_time_ms: float = 0.0,
    error: Optional[str] = None,
) -> None:
    """Log a RAG trace as a fire-and-forget async task.

    Never blocks. Never raises. Errors are logged internally.
    """
    asyncio.create_task(
        _insert_trace(
            user_id=user_id,
            session_id=session_id,
            message_id=message_id,
            query=query,
            rewritten_query=rewritten_query,
            chunks=chunks,
            answer=answer,
            model=model,
            grounded=grounded,
            retrieval_time_ms=retrieval_time_ms,
            embedding_time_ms=embedding_time_ms,
            generation_time_ms=generation_time_ms,
            rerank_time_ms=rerank_time_ms,
            error=error,
        )
    )
