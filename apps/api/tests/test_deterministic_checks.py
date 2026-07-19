"""Offline unit tests for the bundled deterministic eval assertions.

Exercises `src/core/eval/deterministic_checks` — refusal grounding, citation-
presence/format, and the report-only verbatim-copy measure. Pure and
deterministic: no API keys, no DB, no LLM. Intentionally NOT marked `eval` so it
runs in CI under `pytest -m "not eval"` (this is the real per-PR protection for
the checkers; the frozen-fixture measurement is scheduled, not gated).

Inputs mirror shapes seen in the real 100-case fixture: the general-knowledge
disclaimer preface used for OOS questions, grounded answers with inline
[Author, Year] citations, and the sentence-length verbatim spans the copy check
was calibrated against.
"""

from src.core.eval.deterministic_checks import (
    DEFAULT_VERBATIM_WORDS,
    check_format,
    check_no_verbatim,
    check_refusal,
    is_refusal,
    longest_verbatim_run,
    run_all,
)


def _chunk(text):
    return {"chunk_text": text}


# --- is_refusal --------------------------------------------------------------

def test_is_refusal_insufficient_marker():
    assert is_refusal("I don't have enough research to answer this confidently.")


def test_is_refusal_no_sources_marker():
    a = "I don't have specific research papers on this topic, but based on general..."
    assert is_refusal(a)


def test_is_refusal_false_on_normal_answer():
    assert not is_refusal("Moderate loads drive hypertrophy [Schoenfeld, 2021, p. 5].")


# --- check_refusal -----------------------------------------------------------

def test_oos_case_refused_is_ok():
    # OOS by empty facts; answer uses the no-sources disclaimer; grounded False.
    res = check_refusal(
        "I don't have specific research papers on this topic, but generally...",
        expected_facts=[], category="out-of-scope", grounded=False,
    )
    assert res.oos and res.refused and res.ok and res.failure is None


def test_oos_case_answered_confidently_fails():
    res = check_refusal(
        "Creatine improves strength [Kreider, 2017, p. 3].",
        expected_facts=[], category="out-of-scope", grounded=True,
    )
    assert res.oos and not res.refused and not res.ok
    assert res.failure == "answered_oos"


def test_in_scope_answered_is_ok():
    res = check_refusal(
        "Protein timing matters less than total intake [Aragon, 2013, p. 2].",
        expected_facts=["fact one", "fact two"], category="nutrition", grounded=True,
    )
    assert not res.oos and not res.refused and res.ok


def test_in_scope_false_refusal_fails():
    # Answerable question, but the system refused => likely a retrieval failure.
    res = check_refusal(
        "I don't have enough research to answer this confidently.",
        expected_facts=["fact one"], category="hypertrophy", grounded=False,
    )
    assert not res.oos and res.refused and not res.ok
    assert res.failure == "false_refusal"


def test_oos_derived_from_empty_facts_without_category():
    # Even if category is missing, zero expected_facts marks it out-of-scope.
    res = check_refusal(
        "I don't have specific research papers on this topic, but generally...",
        expected_facts=[], category=None, grounded=False,
    )
    assert res.oos and res.ok


# --- check_format ------------------------------------------------------------

def test_grounded_answer_with_citation_ok():
    res = check_format("Loads matter [Schoenfeld, 2021, p. 5].", grounded=True)
    assert res.applicable and res.n_citations == 1 and res.ok


def test_grounded_answer_without_citation_fails():
    res = check_format("Loads matter for hypertrophy.", grounded=True)
    assert res.applicable and res.n_citations == 0 and not res.ok
    assert res.failure == "grounded_no_citation"


def test_refusal_answer_not_required_to_cite():
    res = check_format(
        "I don't have specific research papers on this topic...", grounded=False,
    )
    assert not res.applicable and res.ok


# --- verbatim ----------------------------------------------------------------

def test_longest_verbatim_run_detects_copied_span():
    chunk = "beta alanine is a non proteogenic amino acid produced in the liver"
    answer = "In short, beta alanine is a non proteogenic amino acid produced in the liver, per the source."
    length, span = longest_verbatim_run(answer, [_chunk(chunk)])
    assert length == 12
    assert span == "beta alanine is a non proteogenic amino acid produced in the liver"


def test_verbatim_flag_respects_threshold():
    chunk = "one two three four five six"
    answer = "one two three four five six seven"
    assert check_no_verbatim(answer, [_chunk(chunk)], threshold=6).flagged
    assert not check_no_verbatim(answer, [_chunk(chunk)], threshold=7).flagged


def test_verbatim_zero_on_no_overlap():
    res = check_no_verbatim("completely different wording here", [_chunk("nothing shared")])
    assert res.longest_run == 0 and not res.flagged


def test_verbatim_ignores_citation_bracket_content():
    # A shared [Author, Year] must not count as copied prose.
    chunk = "Schoenfeld 2021 studied training volume"
    answer = "Volume matters [Schoenfeld, 2021, p. 5]."
    length, _ = longest_verbatim_run(answer, [_chunk(chunk)])
    assert length <= 1  # only incidental single-word overlap, brackets stripped


# --- run_all -----------------------------------------------------------------

def test_run_all_clean_case_has_no_hard_failures():
    case = {
        "answer": "Moderate loads drive hypertrophy [Schoenfeld, 2021, p. 5].",
        "grounded": True,
        "expected_facts": ["moderate loads work"],
        "category": "hypertrophy",
        "chunks": [{"chunk_text": "training study", "authors": "Schoenfeld", "year": 2021,
                    "page_start": 5, "page_end": 5}],
    }
    checks = run_all(case)
    assert checks.hard_failures == []
    assert checks.refusal.ok and checks.format.ok


def test_run_all_collects_hard_failures():
    # OOS question answered confidently with an ungrounded citation.
    case = {
        "answer": "Creatine helps [Ghost, 1999, p. 1].",
        "grounded": True,
        "expected_facts": [],
        "category": "out-of-scope",
        "chunks": [{"chunk_text": "unrelated", "authors": "Other", "year": 2020,
                    "page_start": 1, "page_end": 1}],
    }
    checks = run_all(case)
    assert any(f.startswith("refusal:answered_oos") for f in checks.hard_failures)
    assert any(f.startswith("citation:") for f in checks.hard_failures)


def test_default_threshold_is_reasonable():
    assert DEFAULT_VERBATIM_WORDS == 20
