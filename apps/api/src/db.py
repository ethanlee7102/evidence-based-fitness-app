"""Supabase client factories.

Two clients, two trust levels:

- `get_admin_supabase()` - service-role key, **bypasses RLS**. Reserved for
  SYSTEM/admin paths only: the daily-usage ceiling RPC, fire-and-forget trace
  logging, and offline scripts (seeding). Never use it to serve interactive
  user-data reads/writes.
- `get_user_supabase(token)` - a client scoped to the caller's JWT so PostgREST
  runs as role `authenticated` and Postgres RLS enforces isolation (`auth.uid()`
  = the user). This is what user-data services must use, so a missing app-level
  filter can't leak another user's rows. Cached per token (bounded LRU) so we
  don't build - and leak - a fresh client on every request.
"""

from collections import OrderedDict

from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from src.utils.config import config

_admin: Client | None = None

# Bounded LRU of per-user clients, keyed by JWT. One client per active user,
# reused across their requests, instead of a fresh client (with its own httpx
# connection pools) per request - which accumulates open sockets under load.
_USER_CLIENT_CACHE_MAX = 128
_user_clients: "OrderedDict[str, Client]" = OrderedDict()


def get_admin_supabase() -> Client:
    """Service-role client (bypasses RLS). System/admin ops only."""
    global _admin
    if _admin is None:
        if not config.SUPABASE_URL or not config.SUPABASE_SECRET_KEY:
            raise ValueError("Supabase service credentials not configured")
        _admin = create_client(config.SUPABASE_URL, config.SUPABASE_SECRET_KEY)
    return _admin


def get_user_supabase(token: str) -> Client:
    """Client whose PostgREST calls carry the user's JWT, so RLS applies. Cached by
    token: each token gets its own client with the JWT set once (no shared-mutable-
    auth race between users). Evicted clients are reclaimed by GC - promptly, once
    no in-flight request references them."""
    if not config.SUPABASE_URL or not config.SUPABASE_ANON_KEY:
        raise ValueError("Supabase anon credentials not configured")
    cached = _user_clients.get(token)
    if cached is not None:
        _user_clients.move_to_end(token)
        return cached
    client = create_client(
        config.SUPABASE_URL,
        config.SUPABASE_ANON_KEY,
        SyncClientOptions(auto_refresh_token=False, persist_session=False),
    )
    client.postgrest.auth(token)  # scope table/rpc calls to this user's JWT
    _user_clients[token] = client
    if len(_user_clients) > _USER_CLIENT_CACHE_MAX:
        _user_clients.popitem(last=False)  # drop least-recently-used; GC reclaims it
    return client


def get_supabase() -> Client:
    """Deprecated alias → admin client. Retained for non-user-data callers
    (storage, system logging). Do NOT use for interactive user-data CRUD."""
    return get_admin_supabase()
