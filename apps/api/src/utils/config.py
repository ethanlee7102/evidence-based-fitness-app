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

    # RAG pipeline
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
    RAG_SIMILARITY_THRESHOLD: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3"))

    @classmethod
    def validate(cls) -> None:
        if not cls.SUPABASE_URL:
            raise ValueError("SUPABASE_URL not configured")
        if not cls.SUPABASE_SECRET_KEY:
            raise ValueError("SUPABASE_SECRET_KEY not configured")


config = Config()
