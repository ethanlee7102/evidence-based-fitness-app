"""Bundled deterministic eval assertions (Phase 2.5, item 2).

A small family of pure, offline checks over a RAG case — no API keys, no DB, no
LLM, just string/structure inspection. They sit alongside `citation_validity.py`
(item 1) and share its posture: the *checkers* are unit-tested (those tests run
in the `pytest -m "not eval"` PR gate); the *fixture measurement* over the frozen
100-case artifact is report-only / scheduled, not a per-PR gate (running static
data every PR is low-value — the answers only change when the system is
re-captured).

Three checks, each catching a failure the LLM-judge metrics don't score directly:

  1. check_refusal      — did the system decline exactly when it should?
                          OOS / no-fact questions MUST refuse; answerable
                          questions must NOT falsely refuse (a silent retrieval
                          failure hiding as "I don't have enough research").
  2. check_format       — every *grounded* answer must carry ≥1 well-formed
                          [Author, Year] citation (SYSTEM_PROMPT rule 1). Catches
                          a model that quietly stops citing.
  3. no_verbatim        — REPORT-ONLY. Longest contiguous word-run the answer
                          copies from any retrieved chunk. Pressure-tests the
                          copyright-safe design claim ("synthesizes, never shows
                          chunks verbatim"). No clean gap in the real distribution,
                          so this reports a length, never hard-fails.

`run_all` aggregates the three plus the item-1 citation check into one dict, giving
the CI/scheduled layer (item 3) a single entry point.
"""

import re
from dataclasses import dataclass, field

from src.core.eval.citation_validity import check_answer, parse_citations

# --- Refusal markers ---------------------------------------------------------
# Source of truth: rag_pipeline.SYSTEM_PROMPT rule 4 (insufficient sources) and
# NO_CHUNKS_INSTRUCTION (no chunks -> general-knowledge answer WITH a disclaimer).
# Duplicated here as literals rather than imported: importing rag_pipeline pulls
# the RAG -> DB -> supabase chain into these offline unit tests (the exact reason
# the eval package made its rag_query import lazy). Keep this module import-light.
INSUFFICIENT_MARKER = "I don't have enough research to answer this confidently"
NO_SOURCES_MARKER = "I don't have specific research papers on this topic"

# Longest verbatim run (in words) at/above which we flag a copied span. Calibrated
# on the frozen fixture: the run-length distribution is smooth (no natural gap);
# ≥20 words reads as a reproduced source sentence rather than coincidental common
# phrasing, and flags ~5/100 cases. REPORT-ONLY — tune before ever gating.
DEFAULT_VERBATIM_WORDS = 20

_CITATION_BRACKET = re.compile(r"\[[^\]]*\]")
_NON_WORD = re.compile(r"[^a-z0-9 ]")
_WS = re.compile(r"\s+")


def is_refusal(answer: str) -> bool:
    """True if the answer is a refusal or an unsourced general-knowledge answer.

    Either canonical disclaimer counts — both mean "this is NOT a confident,
    literature-grounded answer," which is the property the refusal check cares
    about.
    """
    a = answer or ""
    return INSUFFICIENT_MARKER in a or NO_SOURCES_MARKER in a


# --- 1. Refusal grounding ----------------------------------------------------


@dataclass
class RefusalResult:
    oos: bool           # should this question be refused?
    refused: bool       # did the system refuse (marker present or grounded=False)?
    ok: bool
    failure: str | None = None  # "answered_oos" | "false_refusal" | None


def check_refusal(
    answer: str,
    *,
    expected_facts: list | None,
    category: str | None,
    grounded: bool | None,
) -> RefusalResult:
    """Assert the system refused iff the question is out-of-scope / unanswerable.

    `oos` is derived from the dataset, not a dedicated field: a case is
    out-of-scope when tagged `out-of-scope` OR carries zero `expected_facts`
    (the two OOS cases satisfy both). `refused` trusts either the answer text
    markers or the pipeline's `grounded=False` flag.
    """
    oos = (category or "").strip().lower() == "out-of-scope" or not (expected_facts or [])
    refused = is_refusal(answer) or grounded is False

    if oos and not refused:
        return RefusalResult(oos, refused, ok=False, failure="answered_oos")
    if not oos and refused:
        # An answerable question that got a refusal => retrieval likely failed.
        return RefusalResult(oos, refused, ok=False, failure="false_refusal")
    return RefusalResult(oos, refused, ok=True)


# --- 2. Citation-presence / format ------------------------------------------


@dataclass
class FormatResult:
    applicable: bool    # only grounded answers are required to cite
    n_citations: int
    ok: bool
    failure: str | None = None  # "grounded_no_citation" | None


def check_format(answer: str, *, grounded: bool | None) -> FormatResult:
    """Every grounded answer must carry at least one parseable [Author, Year].

    Refusals / unsourced general-knowledge answers legitimately carry none, so
    the check is skipped (not failed) when `grounded` is not True.
    """
    if grounded is not True:
        return FormatResult(applicable=False, n_citations=0, ok=True)
    n = len(parse_citations(answer))
    if n == 0:
        return FormatResult(applicable=True, n_citations=0, ok=False,
                            failure="grounded_no_citation")
    return FormatResult(applicable=True, n_citations=n, ok=True)


# --- 3. No verbatim copying (report-only) ------------------------------------


def _norm_words(text: str) -> list[str]:
    """Lowercase word list with citation brackets and punctuation removed."""
    t = _CITATION_BRACKET.sub(" ", text or "")
    t = _NON_WORD.sub(" ", t.lower())
    return _WS.sub(" ", t).strip().split()


def _longest_common_run(a: list[str], b: list[str]) -> tuple[int, int]:
    """Longest contiguous common word-run between two word lists.

    Returns (length, end_index_in_a). Space-optimized DP (two rows), O(len(a)*len(b)).
    """
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return 0, 0
    prev = [0] * (m + 1)
    best = best_end = 0
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        ai = a[i - 1]
        for j in range(1, m + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best, best_end = cur[j], i
        prev = cur
    return best, best_end


def _chunk_text(chunk) -> str:
    if isinstance(chunk, dict):
        return chunk.get("chunk_text") or ""
    return getattr(chunk, "chunk_text", "") or ""


@dataclass
class VerbatimResult:
    longest_run: int = 0        # longest contiguous copied word-run
    span: str = ""              # the copied text (for inspection)
    flagged: bool = False       # longest_run >= threshold (report-only signal)


def longest_verbatim_run(answer: str, chunks: list) -> tuple[int, str]:
    """Longest word-run the answer reproduces from ANY retrieved chunk."""
    aw = _norm_words(answer)
    best, span = 0, ""
    for ch in chunks:
        cw = _norm_words(_chunk_text(ch))
        length, end = _longest_common_run(aw, cw)
        if length > best:
            best, span = length, " ".join(aw[end - length:end])
    return best, span


def check_no_verbatim(
    answer: str, chunks: list, threshold: int = DEFAULT_VERBATIM_WORDS,
) -> VerbatimResult:
    """Report-only: measure the longest copied span; flag if >= threshold."""
    length, span = longest_verbatim_run(answer, chunks)
    return VerbatimResult(longest_run=length, span=span, flagged=length >= threshold)


# --- Aggregator --------------------------------------------------------------


@dataclass
class CaseChecks:
    refusal: RefusalResult
    format: FormatResult
    verbatim: VerbatimResult
    citation: object            # citation_validity.AnswerCitationResult
    hard_failures: list[str] = field(default_factory=list)


def run_all(case: dict, *, verbatim_threshold: int = DEFAULT_VERBATIM_WORDS) -> CaseChecks:
    """Run every deterministic check over one fixture/case dict.

    `hard_failures` collects only the gating checks (refusal, format, ungrounded
    citations). Verbatim is report-only and never appears there.
    """
    answer = case.get("answer", "")
    chunks = case.get("chunks", [])
    grounded = case.get("grounded")

    refusal = check_refusal(
        answer,
        expected_facts=case.get("expected_facts"),
        category=case.get("category"),
        grounded=grounded,
    )
    fmt = check_format(answer, grounded=grounded)
    verbatim = check_no_verbatim(answer, chunks, threshold=verbatim_threshold)
    citation = check_answer(answer, chunks)

    hard: list[str] = []
    if refusal.failure:
        hard.append(f"refusal:{refusal.failure}")
    if fmt.failure:
        hard.append(f"format:{fmt.failure}")
    if citation.ungrounded:
        hard.append(f"citation:{len(citation.ungrounded)}_ungrounded")

    return CaseChecks(refusal=refusal, format=fmt, verbatim=verbatim,
                      citation=citation, hard_failures=hard)
