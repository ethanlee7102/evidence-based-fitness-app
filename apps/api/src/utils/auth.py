"""Request authentication - local JWT verification against Supabase's JWKS.

Supabase signs its access tokens with ES256 (asymmetric ECC P-256) and publishes
the public key set at `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`. We verify
tokens locally with that public key instead of calling `supabase.auth.get_user()`
on every request, which removes a per-request network round-trip to Supabase Auth
from the hot path (and the dependency on it being reachable under load).

Security: verification trusts the ES256 signature (unforgeable without Supabase's
private key), not the token's self-reported header - `algorithms=["ES256"]` is
pinned to defeat the classic `alg:none` / algorithm-confusion attacks. Accepted
tradeoff: a locally-verified token can't be checked against server-side revocation
until it expires (~1h). Fine for this app.
"""

import asyncio
import logging

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientConnectionError, PyJWKClientError

from src.utils.config import config

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Module-level JWKS client: caches the signing keys (refetched on its own lifespan)
# so steady-state verification is a pure local crypto op. Pre-warmed in app.py's
# lifespan startup so the first authenticated request doesn't pay the cold fetch.
#
# Built lazily on first use, not at import: PyJWKClient validates the URL in its
# constructor, so instantiating at import would crash any environment without
# SUPABASE_URL set (e.g. CI, which imports this module to collect tests but never
# reaches Supabase). Tests inject a fake by setting this global before verifying;
# a non-None value short-circuits construction.
jwks_client: PyJWKClient | None = None


def get_jwks_client() -> PyJWKClient:
    """Return the shared JWKS client, constructing it on first use."""
    global jwks_client
    if jwks_client is None:
        jwks_client = PyJWKClient(
            config.SUPABASE_JWKS_URL,
            cache_keys=True,
            timeout=config.SUPABASE_JWKS_TIMEOUT,
        )
    return jwks_client


def _verify_token(token: str) -> dict:
    """Verify a Supabase JWT locally and return its claims. Synchronous (blocking
    JWKS fetch on a cache miss) - call via ``asyncio.to_thread`` from async code.

    Raises:
        HTTPException(401): invalid / expired / wrong-audience / wrong-issuer /
            tampered token, or one signed by an unrecognized key.
        HTTPException(503): the JWKS endpoint is unreachable - a transient Supabase
            outage, distinguished from a bad token so valid users aren't 401'd out.
    """
    try:
        signing_key = get_jwks_client().get_signing_key_from_jwt(token)
    except PyJWKClientConnectionError as e:
        logger.error(f"JWKS unreachable: {type(e).__name__}: {e}")
        raise HTTPException(status_code=503, detail="Auth temporarily unavailable")
    except (PyJWKClientError, jwt.PyJWTError) as e:
        # Unknown `kid` / empty JWKS, OR a malformed token whose header can't be
        # parsed (jwt.DecodeError) - either way it isn't signed by a key we trust,
        # so reject as invalid rather than 500.
        logger.warning(f"Cannot resolve signing key: {type(e).__name__}: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],  # pinned - do NOT infer from the token header
            audience=config.SUPABASE_JWT_AUD,
            issuer=config.SUPABASE_JWT_ISSUER,
            leeway=config.JWT_LEEWAY,
        )
    except jwt.PyJWTError as e:
        logger.warning(f"JWT verification failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


async def _authenticated_claims(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """Verified JWT claims for the request. FastAPI caches this dependency per
    request, so `get_current_user` and `get_current_token` share one verification."""
    return await asyncio.to_thread(_verify_token, credentials.credentials)


async def get_current_user(claims: dict = Security(_authenticated_claims)) -> str:
    """The authenticated user's id (JWT `sub`)."""
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token")
    return sub


async def get_current_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    _claims: dict = Security(_authenticated_claims),
) -> str:
    """The raw, verified JWT - used to build a per-request RLS-scoped Supabase
    client (see src/db.py). The `_claims` dependency enforces verification; the
    shared cache means this does not re-verify when the route also depends on
    `get_current_user`."""
    return credentials.credentials
