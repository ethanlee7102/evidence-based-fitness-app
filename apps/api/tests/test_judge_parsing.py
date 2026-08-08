"""Offline unit tests for the judge TRANSPORT layer (`src/core/eval/judge.py`).

These exercise the pure, deterministic plumbing shared by every judge call — no
API keys, no network:

- the 429+5xx retry classifier (incl. Anthropic's 529 overloaded),
- the markdown-fence-stripping JSON extractor,
- the claude-* / gemini-* provider dispatch in `_generate_with_retry`.

The metric-specific parsing (per-fact / per-chunk / per-claim bijection, AP, the
error-not-synthesize behaviour) is tested in `test_binary_judge_parsing.py`.

Intentionally NOT marked `eval` — they must run in CI under `pytest -m "not eval"`.
"""

import asyncio

import pytest

from src.core.eval.judge import (
    JudgeParseError,
    _extract_json_block,
    _generate_with_retry,
    _is_retryable_error,
)

# --- _is_retryable_error -----------------------------------------------------


@pytest.mark.parametrize(
    "err,expected",
    [
        ("Gemini API error 429: rate limited", True),
        ("Anthropic API error 500: internal", True),
        ("Gemini API error 503: unavailable", True),
        ("Anthropic API error 529: overloaded", True),  # the case the old check missed
        ("Gemini API error 200: ok", False),
        ("Anthropic API error 400: bad request", False),
        ("Gemini API error 404: not found", False),
        ("some unrelated error with no status code", False),
        ("", False),
    ],
)
def test_is_retryable_error(err, expected):
    assert _is_retryable_error(err) is expected


# --- _extract_json_block -----------------------------------------------------


def test_extract_json_block_plain():
    assert _extract_json_block('{"score": 5}') == '{"score": 5}'


def test_extract_json_block_strips_json_fence():
    raw = '```json\n{"score": 4, "reasoning": "ok"}\n```'
    assert _extract_json_block(raw) == '{"score": 4, "reasoning": "ok"}'


def test_extract_json_block_strips_bare_fence():
    raw = '```\n{"score": 3}\n```'
    assert _extract_json_block(raw) == '{"score": 3}'


def test_extract_json_block_grabs_object_amid_prose():
    raw = 'Here is my evaluation: {"score": 2, "reasoning": "weak"} — done.'
    assert _extract_json_block(raw) == '{"score": 2, "reasoning": "weak"}'


def test_extract_json_block_raises_when_absent():
    with pytest.raises(JudgeParseError):
        _extract_json_block("no json here at all")


# --- provider dispatch in _generate_with_retry -------------------------------


def test_dispatch_routes_claude_to_anthropic(monkeypatch):
    """claude-* model IDs must route to the Anthropic provider."""
    calls = {"anthropic": 0, "gemini": 0}

    async def fake_anthropic(**kwargs):
        calls["anthropic"] += 1
        assert kwargs["model"] == "claude-haiku-4-5"
        return "anthropic-response"

    async def fake_gemini(**kwargs):
        calls["gemini"] += 1
        return "gemini-response"

    monkeypatch.setattr("src.core.anthropic_provider.generate", fake_anthropic)
    monkeypatch.setattr("src.core.llm_provider.generate", fake_gemini)

    out = asyncio.run(
        _generate_with_retry("p", "sys", judge_model="claude-haiku-4-5")
    )
    assert out == "anthropic-response"
    assert calls == {"anthropic": 1, "gemini": 0}


def test_dispatch_routes_gemini_model_to_gemini(monkeypatch):
    calls = {"anthropic": 0, "gemini": 0}

    async def fake_anthropic(**kwargs):
        calls["anthropic"] += 1
        return "anthropic-response"

    async def fake_gemini(**kwargs):
        calls["gemini"] += 1
        assert kwargs["model"] == "gemini-2.5-flash"
        return "gemini-response"

    monkeypatch.setattr("src.core.anthropic_provider.generate", fake_anthropic)
    monkeypatch.setattr("src.core.llm_provider.generate", fake_gemini)

    out = asyncio.run(
        _generate_with_retry("p", "sys", judge_model="gemini-2.5-flash")
    )
    assert out == "gemini-response"
    assert calls == {"anthropic": 0, "gemini": 1}


def test_dispatch_defaults_none_to_gemini(monkeypatch):
    """judge_model=None falls back to the default Gemini judge, not Anthropic."""
    calls = {"anthropic": 0, "gemini": 0}

    async def fake_anthropic(**kwargs):
        calls["anthropic"] += 1
        return "anthropic-response"

    async def fake_gemini(**kwargs):
        calls["gemini"] += 1
        return "gemini-response"

    monkeypatch.setattr("src.core.anthropic_provider.generate", fake_anthropic)
    monkeypatch.setattr("src.core.llm_provider.generate", fake_gemini)

    out = asyncio.run(_generate_with_retry("p", "sys", judge_model=None))
    assert out == "gemini-response"
    assert calls["anthropic"] == 0
    assert calls["gemini"] == 1
