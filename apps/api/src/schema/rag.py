from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# Literal types matching DB CHECK constraints (migrations 005 + 006)
Category = Literal[
    "hypertrophy", "strength", "nutrition", "endurance",
    "recovery", "mobility", "programming", "general",
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
    similarity: float
    # Flattened paper metadata for citations
    title: str
    authors: str
    year: int
    journal: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    category: Category
    study_type: Optional[StudyType] = None
