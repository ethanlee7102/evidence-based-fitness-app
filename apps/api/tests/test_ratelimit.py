"""Offline unit tests for the per-IP chat rate limiter (src/utils/ratelimit).

No network, no server - exercises the client-IP extraction and the limits-based
allow/deny. Not marked `eval` -> runs in the CI `not eval` gate.
"""

from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

from src.utils.ratelimit import client_ip


class _Req:
    """Minimal stand-in for a Starlette Request."""

    def __init__(self, headers=None, client_host=None):
        self.headers = headers or {}
        self.client = type("C", (), {"host": client_host})() if client_host else None


def test_client_ip_prefers_xff_first_hop():
    req = _Req(headers={"x-forwarded-for": "1.2.3.4, 5.6.7.8"})
    assert client_ip(req) == "1.2.3.4"


def test_client_ip_falls_back_to_peer():
    req = _Req(headers={}, client_host="9.9.9.9")
    assert client_ip(req) == "9.9.9.9"


def test_client_ip_unknown_when_no_peer():
    assert client_ip(_Req()) == "unknown"


def test_limit_allows_then_blocks():
    limiter = MovingWindowRateLimiter(MemoryStorage())
    item = parse("2/minute")
    assert limiter.hit(item, "chat", "ip-a") is True
    assert limiter.hit(item, "chat", "ip-a") is True
    assert limiter.hit(item, "chat", "ip-a") is False  # third over the limit
    # a different IP has its own independent budget
    assert limiter.hit(item, "chat", "ip-b") is True


def test_zero_limit_blocks_immediately():
    limiter = MovingWindowRateLimiter(MemoryStorage())
    assert limiter.hit(parse("0/day"), "chat", "ip") is False
