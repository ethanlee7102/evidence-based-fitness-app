import logging

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.db import get_supabase

security = HTTPBearer()
logger = logging.getLogger(__name__)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """Verify JWT token using Supabase and return user ID."""
    token = credentials.credentials

    try:
        supabase = get_supabase()
        response = supabase.auth.get_user(token)

        if not response or not response.user:
            logger.error(f"No user in response: {response}")
            raise HTTPException(status_code=401, detail="Invalid token")

        return response.user.id

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
