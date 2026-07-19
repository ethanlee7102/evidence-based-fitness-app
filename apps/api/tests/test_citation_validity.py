"""Offline unit tests for the deterministic citation-grounding verifier.

Exercises `src/core/eval/citation_validity` — the checker that asserts every
`[Author, Year]` in a RAG answer maps to a chunk that was actually retrieved.
Pure and deterministic: no API keys, no DB, no LLM. Intentionally NOT marked
`eval` so it runs in CI under `pytest -m "not eval"`.

Each case is an anonymized shape of a real citation form found in the frozen
100-case fixture during design (indirect attribution, nested parentheticals,
accent/hyphen drift, multi-citation brackets), plus the fabrication cases the
checker exists to catch.
"""

from src.core.eval.citation_validity import (
    check_answer,
    normalize_author,
    parse_citations,
)


def _chunk(authors, year, page_start=None, page_end=None):
    """Minimal retrieved-chunk shape (dict path of check_answer)."""
    return {
        "authors": authors,
        "year": year,
        "page_start": page_start,
        "page_end": page_end,
    }


# --- normalize_author --------------------------------------------------------

def test_normalize_strips_et_al_and_case():
    assert normalize_author("Schoenfeld et al.") == "schoenfeld"


def test_normalize_strips_accents():
    assert normalize_author("Piñero et al.") == "pinero"


def test_normalize_collapses_hyphen_and_space_variants():
    # The same author appears both ways in real answers — they must collide.
    assert normalize_author("Androulakis-Korakakis et al.") == "androulakis korakakis"
    assert normalize_author("Androulakis Korakakis et al.") == "androulakis korakakis"


# --- direct grounding --------------------------------------------------------

def test_direct_citation_is_grounded():
    answer = "Moderate loads drive hypertrophy [Schoenfeld et al., 2021, p. 1]."
    res = check_answer(answer, [_chunk("Schoenfeld et al.", 2021, 1, 2)])
    assert res.total == 1
    assert len(res.grounded) == 1
    assert res.ungrounded == []


def test_accented_citation_matches_asciifolded_chunk():
    # Answer cites `Piñero`; chunk metadata stored without the accent.
    answer = "Training close to failure matters [Piñero et al., 2024, pp. 1-2]."
    res = check_answer(answer, [_chunk("Pinero et al.", 2024, 1, 2)])
    assert len(res.grounded) == 1
    assert res.ungrounded == []


def test_multi_citation_bracket_split_on_semicolon():
    answer = "Both agree [Latella et al., 2020, p. 1; Androulakis-Korakakis et al., 2021, p. 9]."
    chunks = [_chunk("Latella et al.", 2020, 1, 1), _chunk("Androulakis-Korakakis et al.", 2021, 9, 9)]
    res = check_answer(answer, chunks)
    assert res.total == 2
    assert len(res.grounded) == 2


# --- scholarly forms that must NOT be flagged --------------------------------

def test_indirect_attribution_validates_citing_source_not_primary():
    # `X, as cited in Y` — only Y (Montoro-Bombu) was retrieved; X (Ramirez) was not.
    # This is honest indirect attribution, NOT a fabrication.
    answer = ("Plyometrics help [Ramírez-Campillo et al., 2013, as cited in "
              "Montoró-Bombú et al., 2023, p. 7].")
    res = check_answer(answer, [_chunk("Montoró-Bombú et al.", 2023, 7, 8)])
    assert len(res.grounded) == 1
    assert res.ungrounded == []
    assert res.indirect_count == 1


def test_cited_in_without_as_is_also_indirect():
    answer = "Protein timing [Parr et al., 2023, cited in Ho et al., 2024, p. 14]."
    res = check_answer(answer, [_chunk("Ho et al.", 2024, 14, 15)])
    assert len(res.grounded) == 1
    assert res.ungrounded == []


def test_bare_in_connective_is_indirect():
    # `X in Y, YEAR` — the model uses bare "in" (not "cited in"); validate Y (Bird).
    answer = "Protein blends help [Kerksick et al. in Bird et al., 2024, p. 9]."
    res = check_answer(answer, [_chunk("Bird et al.", 2024, 8, 10)])
    assert len(res.grounded) == 1
    assert res.ungrounded == []
    assert res.indirect_count == 1


def test_bare_in_with_two_years_validates_citing_source():
    # `X, 2020 in Y, 2022` — two years; the retrieved source is the one after "in".
    answer = "Return-to-sport criteria [Ritsch, 2020 in Bonilla et al., 2022, p. 16]."
    res = check_answer(answer, [_chunk("Bonilla et al.", 2022, 15, 20)])
    assert len(res.grounded) == 1
    assert res.ungrounded == []


def test_unmarked_primary_to_unretrieved_paper_is_ungrounded():
    # STR-007 shape: a bare `[Author, Year]` to a paper NOT retrieved and with NO
    # indirect marker. The model reproduced a review's internal citation as if
    # direct — genuinely ungrounded, must stay flagged.
    answer = "Plyometrics improve sprint speed [Khlifa et al., 2010, p. 7]."
    res = check_answer(answer, [_chunk("Montoró-Bombú et al.", 2023, 7, 8)])
    assert len(res.ungrounded) == 1
    assert res.grounded == []


def test_nested_parenthetical_references_are_ignored():
    # Only the OUTER citation (Wicinski) is the model's source; the parenthetical
    # names are papers Wicinski cites and must not be parsed as separate citations.
    answer = ("Vitamin D is studied across athletes [Wicinski et al., 2019, p. 6 "
              "(Skalska et al., 2019; Orysiak et al., 2018; Fairbairn et al., 2017)].")
    res = check_answer(answer, [_chunk("Wicinski et al.", 2019, 6, 6)])
    assert res.total == 1
    assert len(res.grounded) == 1
    assert res.ungrounded == []


# --- fabrications that MUST be flagged ---------------------------------------

def test_fabricated_citation_is_ungrounded():
    answer = "This claim is unsupported [Madeup et al., 2099, p. 3]."
    res = check_answer(answer, [_chunk("Schoenfeld et al.", 2021, 1, 2)])
    assert len(res.ungrounded) == 1
    assert res.ungrounded[0].year == 2099


def test_right_author_wrong_year_is_ungrounded():
    answer = "Off by a year [Schoenfeld et al., 2018, p. 1]."
    res = check_answer(answer, [_chunk("Schoenfeld et al.", 2021, 1, 2)])
    assert len(res.ungrounded) == 1


def test_citation_in_ungrounded_answer_is_flagged():
    # A no-chunks answer that still fabricates a paper citation.
    answer = "I don't have specific research, but [Ghost et al., 2020, p. 1] says otherwise."
    res = check_answer(answer, [])
    assert res.applicable is True
    assert len(res.ungrounded) == 1


# --- report-only page checks (never affect grounding) ------------------------

def test_page_outside_retrieved_range_is_reported_not_ungrounded():
    # Paper is retrieved, but the cited page (10) isn't in the retrieved chunk (pp. 1-2).
    answer = "Claim [Schoenfeld et al., 2021, p. 10]."
    res = check_answer(answer, [_chunk("Schoenfeld et al.", 2021, 1, 2)])
    assert res.ungrounded == []            # still grounded — same paper
    assert len(res.grounded) == 1
    assert len(res.page_mismatches) == 1


def test_page_within_range_is_not_flagged():
    answer = "Claim [Schoenfeld et al., 2021, p. 2]."
    res = check_answer(answer, [_chunk("Schoenfeld et al.", 2021, 1, 3)])
    assert res.page_mismatches == []


# --- degenerate inputs -------------------------------------------------------

def test_clean_refusal_is_not_applicable():
    # No chunks, no citations — nothing to check (OOS refusal shape).
    answer = ("I don't have specific research papers on this topic, but based on "
              "general exercise science knowledge, easy runs build an aerobic base.")
    res = check_answer(answer, [])
    assert res.applicable is False
    assert res.total == 0


def test_numeric_and_section_brackets_are_not_citations():
    answer = "See ref [49] in section [Section: Abstract] for details."
    assert parse_citations(answer) == []


def test_empty_answer_yields_empty_result():
    res = check_answer("", [_chunk("Schoenfeld et al.", 2021)])
    assert res.total == 0
    assert res.grounded == []
    assert res.ungrounded == []
