from supabase import create_client, Client

from src.utils.config import config

_supabase: Client | None = None


def get_supabase() -> Client:
    """Get Supabase client singleton."""
    global _supabase
    if _supabase is None:
        if not config.SUPABASE_URL or not config.SUPABASE_SECRET_KEY:
            raise ValueError("Supabase credentials not configured")
        _supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SECRET_KEY)
    return _supabase
