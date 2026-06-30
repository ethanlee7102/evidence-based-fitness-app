import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from api directory
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)


class Config:
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "")

    # Embedding (Voyage AI)
    VOYAGE_API_KEY: str = os.getenv("VOYAGE_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "voyage-4-large")
    EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "200"))

    # LLM (Gemini default, swappable)
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")

    # Anthropic (eval cross-validation judge only — lazy, never required at startup)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # RAG pipeline
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3"))

    # Reranking (Phase 2 step 9' — cross-encoder rerank on a deep fetch).
    # Shipped config (Phase 2, 2026-06-29): deep fetch (150, ef_search 500) ->
    # Voyage rerank-2.5 -> top-5, NO per-paper cap. Validated on 100 cases / two judges:
    # recall +0.19, faithfulness +0.19, overall 4.56->4.64 vs vector-only (custom Gemini).
    # FlashRank (ms-marco-MiniLM) was measured first and DEGRADED retrieval; the cap was
    # ablated and found harmful. See results/RERANK_EVAL_REPORT.md.
    RERANK_ENABLED: bool = os.getenv("RERANK_ENABLED", "true").lower() == "true"
    RERANK_PROVIDER: str = os.getenv("RERANK_PROVIDER", "voyage")
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "rerank-2.5")
    RERANK_FETCH_DEPTH: int = int(os.getenv("RERANK_FETCH_DEPTH", "150"))
    RERANK_EF_SEARCH: int = int(os.getenv("RERANK_EF_SEARCH", "500"))
    # Per-paper cap on the reranked top-N. 0 = NO cap (shipped default — the ablation
    # showed the cap diluted relevance/recall). Kept configurable for future tuning.
    RERANK_PER_PAPER_CAP: int = int(os.getenv("RERANK_PER_PAPER_CAP", "0"))
    RERANK_TOP_N: int = int(os.getenv("RERANK_TOP_N", "5"))
    # Max tokens a LOCAL cross-encoder reads per (query, chunk) pair (FlashRank only;
    # ignored by the Voyage API, which truncates server-side). FlashRank's default 128
    # truncates our ~800-token chunks; 512 is the MiniLM trained ceiling.
    RERANK_MAX_LENGTH: int = int(os.getenv("RERANK_MAX_LENGTH", "512"))
    # Similarity floor for the deep candidate fetch. 0.0 means "no floor" — it is
    # translated to -1.0 in retrieve_reranked() to dodge match_chunks' falsy-`or`
    # fallback to RAG_SIMILARITY_THRESHOLD. The floor must be off so the reranker
    # can see (and rescue) the low-vector-similarity-but-relevant tail.
    RERANK_FETCH_THRESHOLD: float = float(os.getenv("RERANK_FETCH_THRESHOLD", "0.0"))
    # Where FlashRank caches its downloaded ONNX model (first use fetches ~tens of MB).
    RERANK_CACHE_DIR: str = os.getenv("RERANK_CACHE_DIR", "")

    @classmethod
    def validate(cls) -> None:
        if not cls.SUPABASE_URL:
            raise ValueError("SUPABASE_URL not configured")
        if not cls.SUPABASE_SECRET_KEY:
            raise ValueError("SUPABASE_SECRET_KEY not configured")


config = Config()
