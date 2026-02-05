from src.db import get_supabase


class StorageService:
    """Handles Supabase storage operations."""

    def __init__(self):
        self.supabase = get_supabase()
        self.bucket = "videos"

    def get_public_url(self, storage_path: str) -> str:
        """Get public URL for a stored video."""
        return self.supabase.storage.from_(self.bucket).get_public_url(storage_path)

    def delete_video(self, storage_path: str) -> None:
        """Delete a video from storage."""
        self.supabase.storage.from_(self.bucket).remove([storage_path])
