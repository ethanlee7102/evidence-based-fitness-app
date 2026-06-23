"""Offline unit tests for the LLM-as-judge parsing/dispatch logic.

These exercise the pure, deterministic pieces of `src/core/eval/judge.py` — no
API keys, no network. They are the regression tests for behaviour the project
relied on but had only ever "unit-verified" by hand:

- the 429+5xx retry classifier (incl. Anthropic's 529 overloaded),
- the markdown-fence-stripping JSON extractor,
- single + combined judge-response parsing and their JudgeParseError signals,
- the claude-* / gemini-* provider dispatch in _generate_with_retry.

Intentionally NOT marked `eval` — they must run in CI under `pytest -m "not eval"`.
"""

import asyncio

import pytest

from src.core.eval.judge import (
    JudgeParseError,
    JudgeResult,
    MetricScore,
    _extract_json_block,
    _generate_with_retry,
    _is_retryable_error,
    _parse_combined_response,
    _parse_single_score,
    extract_score,
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


# --- _parse_single_score -----------------------------------------------------


def test_parse_single_score_clean_json():
    ms = _parse_single_score('{"score": 5, "reasoning": "great"}')
    assert ms.score == 5
    assert ms.reasoning == "great"
    assert ms.extra == {}


def test_parse_single_score_keeps_extra_fields():
    ms = _parse_single_score(
        '{"score": 4, "reasoning": "r", "fact_coverage": {"f1": "supported"}}'
    )
    assert ms.score == 4
    assert ms.extra == {"fact_coverage": {"f1": "supported"}}


def test_parse_single_score_regex_fallback_when_score_out_of_range():
    # JSON parses but score is invalid (9) -> falls through to 'Score: X' regex.
    ms = _parse_single_score('{"score": 9}\nScore: 3')
    assert ms.score == 3


def test_parse_single_score_regex_fallback_no_json():
    ms = _parse_single_score("I'd rate this. Score: 2")
    assert ms.score == 2


def test_parse_single_score_raises_when_unparseable():
    with pytest.raises(JudgeParseError):
        _parse_single_score("totally unparseable, no score anywhere")


# --- _parse_combined_response ------------------------------------------------


def _full_combined_json() -> str:
    return (
        "{"
        '"contextual_relevancy": {"score": 5, "reasoning": "a"},'
        '"contextual_recall": {"score": 4, "reasoning": "b"},'
        '"contextual_precision": {"score": 3, "reasoning": "c"},'
        '"answer_relevancy": {"score": 5, "reasoning": "d"},'
        '"faithfulness": {"score": 4, "reasoning": "e", "unsupported_claims": []}'
        "}"
    )


def test_parse_combined_response_full():
    result = _parse_combined_response(_full_combined_json())
    assert isinstance(result, JudgeResult)
    assert result.contextual_relevancy.score == 5
    assert result.contextual_recall.score == 4
    assert result.contextual_precision.score == 3
    assert result.answer_relevancy.score == 5
    assert result.faithfulness.score == 4


def test_parse_combined_response_missing_key_degrades_only_that_metric():
    # An omitted key resolves to {} (still a dict) -> defaults to score 3, not a crash.
    partial = (
        "{"
        '"contextual_relevancy": {"score": 5, "reasoning": "a"},'
        '"contextual_recall": {"score": 4, "reasoning": "b"},'
        '"contextual_precision": {"score": 2, "reasoning": "c"},'
        '"answer_relevancy": {"score": 5, "reasoning": "d"}'
        # faithfulness omitted
        "}"
    )
    result = _parse_combined_response(partial)
    assert result.contextual_relevancy.score == 5  # other metrics untouched
    assert result.faithfulness.score == 3  # degraded, not a crash


def test_parse_combined_response_non_dict_metric_degrades_to_3():
    # A metric whose value isn't a dict hits the explicit "Missing {key}" branch.
    raw = (
        "{"
        '"contextual_relevancy": {"score": 5, "reasoning": "a"},'
        '"contextual_recall": {"score": 4, "reasoning": "b"},'
        '"contextual_precision": {"score": 3, "reasoning": "c"},'
        '"answer_relevancy": {"score": 5, "reasoning": "d"},'
        '"faithfulness": "not a dict"'
        "}"
    )
    result = _parse_combined_response(raw)
    assert result.faithfulness.score == 3
    assert "Missing faithfulness" in result.faithfulness.reasoning


def test_parse_combined_response_clamps_out_of_range_score():
    raw = (
        "{"
        '"contextual_relevancy": {"score": 99, "reasoning": "a"},'
        '"contextual_recall": {"score": 4, "reasoning": "b"},'
        '"contextual_precision": {"score": 3, "reasoning": "c"},'
        '"answer_relevancy": {"score": 5, "reasoning": "d"},'
        '"faithfulness": {"score": 4, "reasoning": "e"}'
        "}"
    )
    result = _parse_combined_response(raw)
    assert result.contextual_relevancy.score == 5  # clamped to max


def test_parse_combined_response_raises_when_no_json():
    with pytest.raises(JudgeParseError):
        _parse_combined_response("the model refused and wrote prose only")


# --- extract_score (non-raising wrapper) -------------------------------------


def test_extract_score_success():
    score, reasoning, extra = extract_score('{"score": 5, "reasoning": "ok"}')
    assert score == 5
    assert reasoning == "ok"


def test_extract_score_falls_back_to_3():
    score, reasoning, _ = extract_score("garbage with no score")
    assert score == 3
    assert "failed" in reasoning.lower()


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


def test_metricscore_is_constructible():
    """Smoke check that the dataclass import path is intact."""
    ms = MetricScore(score=3, reasoning="x")
    assert ms.score == 3
    assert ms.extra == {}
