"""Chat session and message persistence.

Handles CRUD for chat_sessions and chat_messages tables.
Uses service_role Supabase client (bypasses RLS) — enforces user_id in every query.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from src.db import get_user_supabase
from src.schema.rag import ChatMessage

logger = logging.getLogger(__name__)


class ChatService:
    """Manages chat sessions and messages in Supabase."""

    def __init__(self, token: str):
        # RLS-scoped to the caller's JWT (see src/db.get_user_supabase).
        self.supabase = get_user_supabase(token)

    # --- Sessions ---

    def create_session(self, user_id: str, title: Optional[str] = None) -> dict[str, Any]:
        """Create a new chat session."""
        data: dict[str, Any] = {"user_id": user_id}
        if title:
            data["title"] = title

        response = self.supabase.table("chat_sessions").insert(data).execute()
        return response.data[0]

    def get_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """List all sessions for a user, newest first."""
        response = (
            self.supabase.table("chat_sessions")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return response.data

    def get_session(self, session_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """Get a single session by ID, scoped to user."""
        # limit(1) rather than maybe_single(): the latter returns None on 0 rows in
        # this supabase-py version, so `.data` then AttributeErrors (500) instead of
        # letting the caller 404 on an unknown/foreign session.
        response = (
            self.supabase.table("chat_sessions")
            .select("*")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session (FK cascade deletes messages). Returns True if deleted."""
        response = (
            self.supabase.table("chat_sessions")
            .delete()
            .eq("id", session_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(response.data) > 0

    def update_session_title(self, session_id: str, title: str) -> None:
        """Update the title of a session."""
        self.supabase.table("chat_sessions").update(
            {"title": title}
        ).eq("id", session_id).execute()

    def update_session_timestamp(self, session_id: str) -> None:
        """Bump updated_at to now (for ordering)."""
        self.supabase.table("chat_sessions").update(
            {"updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", session_id).execute()

    # --- Messages ---

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        citations: Optional[list[dict]] = None,
    ) -> dict[str, Any]:
        """Save a message to chat_messages."""
        data: dict[str, Any] = {
            "session_id": session_id,
            "role": role,
            "content": content,
        }
        if citations is not None:
            data["citations"] = citations

        response = self.supabase.table("chat_messages").insert(data).execute()
        return response.data[0]

    def get_messages(
        self,
        session_id: str,
        user_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get messages for a session, oldest first. Capped at limit.

        Verifies session belongs to user via join filter.
        """
        response = (
            self.supabase.table("chat_messages")
            .select("*, chat_sessions!inner(user_id)")
            .eq("session_id", session_id)
            .eq("chat_sessions.user_id", user_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        # Strip the join data from results
        return [
            {k: v for k, v in msg.items() if k != "chat_sessions"}
            for msg in response.data
        ]

    def get_recent_messages(
        self,
        session_id: str,
        user_id: str,
        limit: int = 10,
    ) -> list[ChatMessage]:
        """Get recent messages formatted for RAG history (ChatMessage TypedDicts).

        Returns oldest-first within the window (last N messages).
        """
        # Fetch last N messages, newest first
        response = (
            self.supabase.table("chat_messages")
            .select("role, content, chat_sessions!inner(user_id)")
            .eq("session_id", session_id)
            .eq("chat_sessions.user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        # Reverse to oldest-first, convert to ChatMessage TypedDicts
        messages: list[ChatMessage] = [
            {"role": row["role"], "content": row["content"]}
            for row in reversed(response.data)
        ]
        return messages
