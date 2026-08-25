"""Per-IP rate limiting for the public demo, built directly on the `limits` lib.

The check runs in the chat route body (not a decorator) so the owner account can
be exempted from it together with the global daily ceiling, under one guard, using
the already-verified user id.

Best-effort by design: X-Forwarded-For can be spoofed and the in-memory store is
per-process (resets on cold start, not shared across App Runner instances). The
hard, un-bypassable cost cap is the global daily ceiling in chat.py - not this.
"""

from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from starlette.requests import Request

from src.utils.config import config

_storage = MemoryStorage()
_limiter = MovingWindowRateLimiter(_storage)
_chat_limit = parse(config.DEMO_CHAT_RATE)


def client_ip(request: Request) -> str:
    # Behind App Runner the real client IP is the first hop of X-Forwarded-For.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def chat_rate_ok(request: Request) -> bool:
    """Consume one unit of the caller IP's chat budget. False if over the limit."""
    return _limiter.hit(_chat_limit, "chat", client_ip(request))
