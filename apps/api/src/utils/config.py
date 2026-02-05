import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from api directory
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)


class Config:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "")

    @classmethod
    def validate(cls) -> None:
        if not cls.SUPABASE_URL:
            raise ValueError("SUPABASE_URL not configured")
        if not cls.SUPABASE_SECRET_KEY:
            raise ValueError("SUPABASE_SECRET_KEY not configured")


config = Config()
