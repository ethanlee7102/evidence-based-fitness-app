"""Offline unit tests for the Gemini payload builder.

Guards the thinking-token budget control on `_build_gemini_payload`. Query
rewriting is a mechanical task run with a small `max_tokens`; if Gemini 2.5
thinking is left enabled, hidden thinking tokens exhaust the budget and truncate
the visible output mid-sentence (observed in production: a follow-up rewrite was
cut off before the word "sleep", silently corrupting retrieval). These tests lock
in the ability to disable thinking per-call without touching other callers.
"""

from src.core.llm_provider import _build_gemini_payload


def test_thinking_budget_omitted_by_default():
    """Callers that don't pass thinking_budget get no thinkingConfig (default behavior)."""
    payload = _build_gemini_payload("hello")
    assert "thinkingConfig" not in payload["generationConfig"]


def test_thinking_budget_zero_disables_thinking():
    """thinking_budget=0 emits thinkingConfig.thinkingBudget=0 (thinking disabled)."""
    payload = _build_gemini_payload("hello", thinking_budget=0)
    assert payload["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}


def test_thinking_budget_positive_value_passthrough():
    """A positive budget is passed through verbatim."""
    payload = _build_gemini_payload("hello", thinking_budget=1024)
    assert payload["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 1024}


def test_max_tokens_and_temperature_still_set_with_thinking_config():
    """Adding thinkingConfig must not drop the existing generationConfig fields."""
    payload = _build_gemini_payload(
        "hello", temperature=0.0, max_tokens=512, thinking_budget=0
    )
    gc = payload["generationConfig"]
    assert gc["temperature"] == 0.0
    assert gc["maxOutputTokens"] == 512
    assert gc["thinkingConfig"] == {"thinkingBudget": 0}
