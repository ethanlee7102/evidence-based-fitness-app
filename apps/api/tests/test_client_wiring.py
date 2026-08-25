"""Offline wiring tests for the service-role -> per-request JWT-scoped refactor.

Regression guards:
- `get_user_supabase` caches one client per token (bounded LRU), not a fresh one
  per request.
- `RoutineService` threads the caller's token into its inner `WorkoutService`
  (otherwise it constructs `WorkoutService()` with no arg and every /routines
  endpoint 500s - the exact bug this file guards against).

Uses fakes for `create_client`, so nothing hits the network or needs real creds.
Not marked `eval` -> runs in the CI `not eval` gate.
"""

import src.db as db


class _FakePostgrest:
    def __init__(self):
        self.token = None

    def auth(self, token):
        self.token = token


class _FakeClient:
    def __init__(self):
        self.postgrest = _FakePostgrest()


def _install_fake_create(monkeypatch):
    created = []

    def fake_create(url, key, options=None):
        c = _FakeClient()
        created.append(c)
        return c

    monkeypatch.setattr(db, "create_client", fake_create)
    monkeypatch.setattr(db.config, "SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setattr(db.config, "SUPABASE_ANON_KEY", "sb_publishable_fake")
    db._user_clients.clear()
    return created


def test_user_client_cached_and_scoped_per_token(monkeypatch):
    created = _install_fake_create(monkeypatch)
    a1 = db.get_user_supabase("tokA")
    a2 = db.get_user_supabase("tokA")
    b = db.get_user_supabase("tokB")
    assert a1 is a2                       # same token -> reused, not rebuilt
    assert b is not a1                    # different token -> its own client
    assert a1.postgrest.token == "tokA"   # JWT scoped once, at build time
    assert len(created) == 2


def test_user_client_lru_evicts_oldest(monkeypatch):
    _install_fake_create(monkeypatch)
    monkeypatch.setattr(db, "_USER_CLIENT_CACHE_MAX", 2)
    db.get_user_supabase("t1")
    db.get_user_supabase("t2")
    db.get_user_supabase("t3")            # over cap -> evict least-recently-used (t1)
    assert set(db._user_clients) == {"t2", "t3"}


def test_routine_service_threads_token_to_inner_workout_service(monkeypatch):
    import src.service.routine_service as rs
    import src.service.workout_service as ws
    from src.service.routine_service import RoutineService

    seen = []
    monkeypatch.setattr(rs, "get_user_supabase", lambda t: seen.append(("rs", t)) or object())
    monkeypatch.setattr(ws, "get_user_supabase", lambda t: seen.append(("ws", t)) or object())

    svc = RoutineService("tok-123")
    assert ("rs", "tok-123") in seen
    assert ("ws", "tok-123") in seen      # inner WorkoutService got the SAME token
    assert svc.workout_service is not None
