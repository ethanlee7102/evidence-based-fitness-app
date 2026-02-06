from typing import Any

from src.db import get_supabase


class DBService:
    """Handles database operations."""

    def __init__(self):
        self.supabase = get_supabase()

    def save_analysis(
        self,
        analysis_id: str,
        user_id: str,
        video_url: str,
        exercise_type: str,
        technique_score: int,
        issues: list[dict],
        bar_path: list[dict] | None = None,
        landmarks_data: list[dict] | None = None,
        fps: float | None = None,
        phase_boundaries: list[dict] | None = None,
    ) -> dict:
        """Save analysis result to database."""
        video_data = {
            "id": analysis_id,
            "user_id": user_id,
            "storage_path": video_url,
            "exercise_type": exercise_type,
            "fps": fps,
        }
        self.supabase.table("videos").insert(video_data).execute()

        analysis_data = {
            "id": analysis_id,
            "video_id": analysis_id,
            "technique_score": technique_score,
            "issues": issues,
            "landmarks_data": landmarks_data,
            "bar_path_data": bar_path,
            "phase_boundaries": phase_boundaries,
        }
        result = self.supabase.table("analyses").insert(analysis_data).execute()

        return result.data[0] if result.data else {}

    def get_analysis_by_id(self, analysis_id: str, user_id: str) -> dict[str, Any] | None:
        """Get analysis by ID, ensuring it belongs to the user."""
        result = (
            self.supabase.table("analyses")
            .select("*, videos!inner(user_id, exercise_type, storage_path, fps)")
            .eq("id", analysis_id)
            .eq("videos.user_id", user_id)
            .single()
            .execute()
        )

        if not result.data:
            return None

        return result.data

    def get_user_videos(self, user_id: str) -> list[dict]:
        """Get all videos for a user."""
        result = (
            self.supabase.table("videos")
            .select("*, analyses(*)")
            .eq("user_id", user_id)
            .order("uploaded_at", desc=True)
            .execute()
        )

        return result.data or []
