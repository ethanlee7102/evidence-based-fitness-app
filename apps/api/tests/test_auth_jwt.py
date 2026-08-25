"""Offline unit tests for local ES256 JWT verification (`src/utils/auth`).

Generates an ephemeral EC P-256 keypair, stubs the module-level JWKS client to
return that public key, and signs tokens with the matching private key. No
network, no Supabase, no real keys. Not marked `eval` -> runs in the CI
`pytest -m "not eval"` gate.
"""

import asyncio
import datetime as dt

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from jwt import PyJWKClientConnectionError, PyJWKClientError

from src.utils import auth
from src.utils.config import config

ISS = "https://test.supabase.co/auth/v1"
AUD = "authenticated"


class _Creds:
    """Stand-in for FastAPI's HTTPAuthorizationCredentials."""

    def __init__(self, token: str):
        self.credentials = token


@pytest.fixture
def keypair():
    priv = ec.generate_private_key(ec.SECP256R1())
    return priv, priv.public_key()


@pytest.fixture(autouse=True)
def _stub(monkeypatch, keypair):
    """Point the verifier at our ephemeral public key + fixed iss/aud."""
    _, pub = keypair

    class _Key:
        key = pub

    class _JWKS:
        def get_signing_key_from_jwt(self, token):
            return _Key()

    monkeypatch.setattr(auth, "jwks_client", _JWKS())
    monkeypatch.setattr(config, "SUPABASE_JWT_ISSUER", ISS)
    monkeypatch.setattr(config, "SUPABASE_JWT_AUD", AUD)


def _token(priv, *, sub="user-123", aud=AUD, iss=ISS, exp_delta=3600,
           alg="ES256", key=None, extra=None):
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": sub,
        "aud": aud,
        "iss": iss,
        "iat": now,
        "exp": now + dt.timedelta(seconds=exp_delta),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, key if key is not None else priv, algorithm=alg)


# --- happy path ---


def test_valid_token_returns_claims(keypair):
    priv, _ = keypair
    claims = auth._verify_token(_token(priv, sub="abc", extra={"is_anonymous": True}))
    assert claims["sub"] == "abc"
    assert claims["is_anonymous"] is True


def test_get_current_user_returns_sub():
    assert asyncio.run(auth.get_current_user(claims={"sub": "abc"})) == "abc"


def test_authenticated_claims_full_path(keypair):
    priv, _ = keypair
    claims = asyncio.run(auth._authenticated_claims(_Creds(_token(priv, sub="xyz"))))
    assert claims["sub"] == "xyz"


# --- rejection: bad tokens -> 401 ---


def test_expired_token_401(keypair):
    priv, _ = keypair
    with pytest.raises(HTTPException) as e:
        auth._verify_token(_token(priv, exp_delta=-120))  # beyond the 30s leeway
    assert e.value.status_code == 401


def test_wrong_audience_401(keypair):
    priv, _ = keypair
    with pytest.raises(HTTPException) as e:
        auth._verify_token(_token(priv, aud="not-authenticated"))
    assert e.value.status_code == 401


def test_wrong_issuer_401(keypair):
    priv, _ = keypair
    with pytest.raises(HTTPException) as e:
        auth._verify_token(_token(priv, iss="https://evil.example/auth/v1"))
    assert e.value.status_code == 401


def test_tampered_signature_401(keypair):
    priv, _ = keypair
    tok = _token(priv)
    head, payload, sig = tok.split(".")
    bad = sig[:-2] + ("aa" if sig[-2:] != "aa" else "bb")
    with pytest.raises(HTTPException) as e:
        auth._verify_token(f"{head}.{payload}.{bad}")
    assert e.value.status_code == 401


def test_algorithm_confusion_hs256_rejected(keypair):
    """A token forged with HS256 must be refused - we pin ES256, never infer alg."""
    priv, _ = keypair
    hs_token = _token(priv, alg="HS256", key="a-shared-secret")
    with pytest.raises(HTTPException) as e:
        auth._verify_token(hs_token)
    assert e.value.status_code == 401


def test_missing_sub_401():
    with pytest.raises(HTTPException) as e:
        asyncio.run(auth.get_current_user(claims={"aud": AUD}))
    assert e.value.status_code == 401


# --- key-resolution failures ---


def test_jwks_unreachable_503(keypair, monkeypatch):
    priv, _ = keypair

    class _Boom:
        def get_signing_key_from_jwt(self, token):
            raise PyJWKClientConnectionError("connection refused")

    monkeypatch.setattr(auth, "jwks_client", _Boom())
    with pytest.raises(HTTPException) as e:
        auth._verify_token(_token(priv))
    assert e.value.status_code == 503


def test_unknown_kid_401(keypair, monkeypatch):
    priv, _ = keypair

    class _NoKey:
        def get_signing_key_from_jwt(self, token):
            raise PyJWKClientError("Unable to find a signing key")

    monkeypatch.setattr(auth, "jwks_client", _NoKey())
    with pytest.raises(HTTPException) as e:
        auth._verify_token(_token(priv))
    assert e.value.status_code == 401


def test_malformed_token_401(monkeypatch):
    """A garbage/non-JWT string must 401, not 500 (public endpoint hygiene)."""

    class _Boom:
        def get_signing_key_from_jwt(self, token):
            raise jwt.DecodeError("Not enough segments")

    monkeypatch.setattr(auth, "jwks_client", _Boom())
    with pytest.raises(HTTPException) as e:
        auth._verify_token("not.a.jwt")
    assert e.value.status_code == 401
