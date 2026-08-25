"""Chat API — SSE streaming, session management, and observability.

Main endpoint: POST /chat/message — streams RAG responses via SSE.
Also provides session CRUD for history management.
"""

import asyncio
import json
import logging
import re
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.core.llm_provider import generate
from src.core.rag_pipeline import rag_query_stream
from src.core.trace_logger import log_trace
from src.db import get_admin_supabase
from src.schema.rag import (
    ChatMessageRequest,
    CitationPayload,
    MessageResponse,
    SessionResponse,
)
from src.service.chat_service import ChatService
from src.utils.auth import get_current_token, get_current_user
from src.utils.config import config
from src.utils.ratelimit import chat_rate_ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# --- SSE helpers ---


def _sse_event(event: str, data: dict) -> str:
    """Format a single SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _chunks_to_citations(chunks) -> list[dict]:
    """Convert ChunkResponse list to CitationPayload dicts for SSE + JSONB storage."""
    seen = set()
    citations = []
    for c in chunks:
        if c.chunk_id in seen:
            continue
        seen.add(c.chunk_id)
        citations.append(
            CitationPayload(
                chunk_id=c.chunk_id,
                title=c.title,
                authors=c.authors,
                year=c.year,
                category=c.category,
                similarity=c.similarity,
                journal=c.journal,
                doi=c.doi,
                section=c.section,
                page_start=c.page_start,
                page_end=c.page_end,
            ).model_dump()
        )
    return citations


def _clean_title(raw: str) -> str:
    """Clean LLM-generated title: strip quotes, preamble, truncate to 60 chars."""
    # Remove common LLM preamble patterns
    cleaned = re.sub(r'^(title:\s*|here\'s a title:\s*)', '', raw, flags=re.IGNORECASE)
    # Strip surrounding quotes
    cleaned = cleaned.strip().strip('"').strip("'").strip()
    # Truncate
    if len(cleaned) > 60:
        cleaned = cleaned[:57] + "..."
    return cleaned


async def _generate_title(
    query: str,
    answer_preview: str,
    session_id: str,
    chat: ChatService,
) -> None:
    """Generate a session title from the first Q&A. Fire-and-forget."""
    try:
        prompt = (
            f"Generate a short, descriptive title (3-8 words) for a conversation "
            f"that starts with this question and answer.\n\n"
            f"Question: {query}\n"
            f"Answer preview: {answer_preview[:300]}\n\n"
            f"Return ONLY the title, nothing else."
        )
        # Titling is a mechanical call. Disable Gemini 2.5 thinking — otherwise
        # thinking tokens consume the tiny max_tokens budget before any title text
        # is produced, yielding a mid-word fragment or an empty string (which leaves
        # the session stuck on its "New Chat" default).
        raw_title = await generate(
            prompt=prompt, temperature=0.7, max_tokens=64, thinking_budget=0
        )
        title = _clean_title(raw_title)
        if title:
            chat.update_session_title(session_id, title)
            logger.info(f"Auto-titled session {session_id}: \"{title}\"")
    except Exception as e:
        logger.error(f"Failed to generate title for session {session_id}: {e}")


# --- Endpoints ---


@router.post("/message")
async def send_message(
    request: Request,
    body: ChatMessageRequest,
    user_id: str = Depends(get_current_user),
    token: str = Depends(get_current_token),
):
    """Main SSE streaming endpoint.

    Creates session if needed, retrieves relevant chunks, streams LLM response,
    saves messages, logs trace, and generates title — all in one request.
    """
    chat = ChatService(token)
    session_id = body.session_id
    is_new_session = False

    # 1. Create session if needed
    if not session_id:
        session = chat.create_session(user_id)
        session_id = session["id"]
        is_new_session = True
    else:
        # Verify session belongs to user
        session = chat.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    # Abuse controls, applied after the session is resolved (a bad session
    # shouldn't consume a unit) and before any paid retrieval/generation. The
    # OWNER account skips BOTH so personal testing doesn't eat the demo budget.
    #   1. Per-IP throttle (best-effort; X-Forwarded-For, in-memory).
    #   2. Global daily ceiling - the hard, un-bypassable cost cap. One unit
    #      covers this request's embed + rerank + generation (+ optional rewrite/
    #      title). Uses the admin client: the counter table is service-role-only.
    if user_id != config.OWNER_USER_ID:
        if not chat_rate_ok(request):
            raise HTTPException(
                status_code=429,
                detail="You've reached the demo message limit for your connection. Please try again later.",
            )
        allowed = (
            get_admin_supabase()
            .rpc("bump_daily_chat_usage", {"p_limit": config.DEMO_DAILY_CHAT_CEILING})
            .execute()
        )
        if not allowed.data:
            raise HTTPException(
                status_code=429,
                detail="The demo has reached today's usage limit. Please try again tomorrow.",
            )

    # 2. Get history BEFORE saving user message (so current message isn't in history)
    history = None
    if not is_new_session:
        history = chat.get_recent_messages(session_id, user_id, limit=10)
        if not history:
            history = None

    # 3. Save user message + bump timestamp
    chat.save_message(session_id, "user", body.message)
    chat.update_session_timestamp(session_id)

    # 4. Run RAG pipeline (retrieval happens here, stream is lazy)
    rag_result = await rag_query_stream(
        query=body.message,
        history=history,
        category=body.category,
    )

    citations = _chunks_to_citations(rag_result.chunks)

    # 5. Stream SSE response
    async def event_stream():
        gen_start = time.perf_counter()
        answer_parts = []
        error_detail: Optional[str] = None

        try:
            # Session event (only for new sessions)
            if is_new_session:
                yield _sse_event("session", {"session_id": session_id, "title": None})

            # Citations event (always, before text)
            yield _sse_event("citations", {
                "chunks": citations,
                "grounded": rag_result.grounded,
            })

            # Stream text chunks
            async for text_chunk in rag_result.stream:
                answer_parts.append(text_chunk)
                yield _sse_event("data", {"text": text_chunk})

        except Exception as e:
            error_detail = f"{type(e).__name__}: {e}"
            logger.error(f"Stream error for session {session_id}: {error_detail}")
            yield _sse_event("error", {"detail": "An error occurred while generating the response."})

        gen_time_ms = (time.perf_counter() - gen_start) * 1000
        full_answer = "".join(answer_parts)

        if error_detail:
            # Don't save partial answer — log trace with error
            log_trace(
                user_id=user_id,
                session_id=session_id,
                message_id="",
                query=body.message,
                rewritten_query=rag_result.rewritten_query,
                chunks=rag_result.chunks,
                answer=full_answer,
                model=rag_result.model,
                grounded=rag_result.grounded,
                retrieval_time_ms=rag_result.retrieval_time_ms,
                embedding_time_ms=rag_result.embedding_time_ms,
                rerank_time_ms=rag_result.rerank_time_ms,
                generation_time_ms=gen_time_ms,
                error=error_detail,
            )
            return

        # Save assistant message
        assistant_msg = chat.save_message(
            session_id, "assistant", full_answer, citations=citations
        )
        message_id = assistant_msg["id"]

        # Done event
        yield _sse_event("done", {"message_id": message_id})

        # Fire-and-forget: log trace
        log_trace(
            user_id=user_id,
            session_id=session_id,
            message_id=message_id,
            query=body.message,
            rewritten_query=rag_result.rewritten_query,
            chunks=rag_result.chunks,
            answer=full_answer,
            model=rag_result.model,
            grounded=rag_result.grounded,
            retrieval_time_ms=rag_result.retrieval_time_ms,
            embedding_time_ms=rag_result.embedding_time_ms,
            rerank_time_ms=rag_result.rerank_time_ms,
            generation_time_ms=gen_time_ms,
        )

        # Fire-and-forget: generate title for first message
        if is_new_session and full_answer:
            asyncio.create_task(
                _generate_title(body.message, full_answer, session_id, chat)
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(user_id: str = Depends(get_current_user),
    token: str = Depends(get_current_token)):
    """List all chat sessions for the current user, newest first."""
    chat = ChatService(token)
    return chat.get_sessions(user_id)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, user_id: str = Depends(get_current_user),
    token: str = Depends(get_current_token)):
    """Get a single chat session."""
    chat = ChatService(token)
    session = chat.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(session_id: str, user_id: str = Depends(get_current_user),
    token: str = Depends(get_current_token)):
    """Get all messages for a session, oldest first."""
    chat = ChatService(token)
    # Verify session exists and belongs to user
    session = chat.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return chat.get_messages(session_id, user_id, limit=50)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user_id: str = Depends(get_current_user),
    token: str = Depends(get_current_token)):
    """Delete a chat session and all its messages (FK cascade)."""
    chat = ChatService(token)
    deleted = chat.delete_session(session_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"detail": "Session deleted"}
