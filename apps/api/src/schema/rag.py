from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel, Field

# Literal types matching DB CHECK constraints (migrations 005 + 006)
Category = Literal[
    "hypertrophy", "strength", "nutrition", "endurance",
    "recovery", "mobility", "programming", "body-composition",
    "general", "injury", "cardiovascular",
]

StudyType = Literal[
    "meta-analysis", "systematic-review", "rct", "review",
    "observational", "case-study", "other",
]

License = Literal[
    "CC0", "CC-BY", "CC-BY-SA", "CC-BY-ND",
    "CC-BY-NC", "CC-BY-NC-SA", "CC-BY-NC-ND",
    "other", "unknown",
]


class PaperMetadata(BaseModel):
    """Input metadata for ingesting a paper."""

    title: str
    authors: str
    year: int = Field(..., ge=1900, le=2100)
    journal: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    category: Category
    study_type: Optional[StudyType] = None
    abstract: Optional[str] = None
    license: License = "unknown"


class PaperResponse(BaseModel):
    """Paper record returned from the database."""

    id: str
    title: str
    authors: str
    year: int
    journal: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    category: Category
    study_type: Optional[StudyType] = None
    abstract: Optional[str] = None
    license: License
    content_hash: str
    total_chunks: int
    embedding_model: str
    ingested_at: datetime

    class Config:
        from_attributes = True


class ChunkResponse(BaseModel):
    """Chunk with paper metadata, returned by retrieval (match_chunks RPC)."""

    chunk_id: str
    paper_id: str
    chunk_text: str
    section: Optional[str] = None
    chunk_index: int
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    token_count: Optional[int] = None
    similarity: float
    # Cross-encoder relevance score, set by the reranker (None on vector-only paths).
    # The sort key after reranking; `similarity` is preserved for citations/observability.
    rerank_score: Optional[float] = None
    # Flattened paper metadata for citations
    title: str
    authors: str
    year: int
    journal: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    category: Category
    study_type: Optional[StudyType] = None


class ChatMessage(TypedDict):
    """A single message in conversation history. Provider-agnostic format."""

    role: Literal["user", "assistant"]
    content: str


@dataclass
class RetrievalResult:
    """Result from retrieve_chunks() — bundles chunks with query metadata."""

    chunks: list[ChunkResponse] = field(default_factory=list)
    query: str = ""
    retrieval_time_ms: float = 0.0
    embedding_time_ms: float = 0.0
    rerank_time_ms: float = 0.0


@dataclass
class RAGResult:
    """Non-streaming RAG response — used by eval pipeline (Phase 8).

    Contains the full answer and all metadata needed for evaluation and tracing.
    """

    answer: str
    chunks: list[ChunkResponse]
    query: str
    rewritten_query: str | None
    prompt_sent: str
    retrieval_time_ms: float
    embedding_time_ms: float
    rerank_time_ms: float
    generation_time_ms: float
    model: str
    grounded: bool


@dataclass
class StreamingRAGResult:
    """Streaming RAG response — used by chat UI (Phase 7).

    Metadata is available immediately. The .stream generator yields text chunks
    as they arrive from the LLM. answer and generation_time_ms are NOT included
    because they aren't known until the stream finishes — Phase 6 route handler
    accumulates the answer and measures timing.
    """

    chunks: list[ChunkResponse]
    query: str
    rewritten_query: str | None
    prompt_sent: str
    retrieval_time_ms: float
    embedding_time_ms: float
    rerank_time_ms: float
    model: str
    grounded: bool
    stream: AsyncGenerator[str, None]


# --- API models (Phase 6: Chat API) ---


class ChatMessageRequest(BaseModel):
    """POST body for /chat/message endpoint."""

    # Capped for the public demo: prompt cost scales with input length, so a
    # smaller ceiling bounds per-request spend (history is separately capped to
    # the last 10 messages).
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    category: Optional[Category] = None


class CitationPayload(BaseModel):
    """Citation data stored as JSONB on assistant messages."""

    chunk_id: str
    title: str
    authors: str
    year: int
    category: Category
    similarity: float
    journal: Optional[str] = None
    doi: Optional[str] = None
    section: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class SessionResponse(BaseModel):
    """Chat session returned from the API."""

    id: str
    user_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    """Chat message returned from the API."""

    id: str
    session_id: str
    role: str
    content: str
    citations: Optional[list[CitationPayload]] = None
    created_at: datetime
