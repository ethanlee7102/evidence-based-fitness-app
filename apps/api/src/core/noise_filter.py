"""Content-based noise detection for corpus chunks.

Identifies bibliography / reference-list / boilerplate chunks that carry no
synthesizable content. Used two ways from ONE definition:
  1. ingestion (`chunk_sections`) — drop noise chunks before embedding, so new
     papers never add reference-list pollution.
  2. one-time audit (`scripts/classify_noise_chunks.py`) — classify the existing
     corpus for the Phase 2 cleanup.

Why content-based, not section-label based: Docling frequently fails to emit a
"References" header (esp. MDPI/Frontiers), so reference lists inherit the
preceding section's label (e.g. "5. Conclusions"). Conversely, a chunk-boundary
split can leave real prose under a "References" label. The section label is
therefore only a secondary vote; the chunk text is the primary signal.

Validated (2026-07-06): over the 8,284-chunk corpus this flagged 1,402 chunks;
15 parallel reviewers reading every flagged chunk confirmed 1,387 as true noise
(98.9% precision). The 15 misses were all chunk-boundary spillage (a reference
list fused with a real conclusion/table) — the guards below spare that class.
"""

import re

# Section labels that are unambiguous boilerplate (secondary vote only).
BOILERPLATE_SECTION = re.compile(
    r"\b("
    r"references?|bibliography|acknowledg|"
    r"funding|conflict|competing interest|author contribution|"
    r"data availability|supplementary|declaration|abbreviation|"
    r"ethics|informed consent|publisher'?s note|appendix"
    r")\b",
    re.I,
)

# Prose words used to decide whether the HEAD of a chunk is real content.
PROSE_HEAD = re.compile(
    r"\b(the|this|that|these|those|is|are|was|were|be|been|being|has|have|had|"
    r"can|may|might|should|would|could|will|because|however|therefore|although|"
    r"while|when|thus|our|we|it|its|their|there|based|despite|"
    r"demonstrates?|concludes?|suggests?|indicates?|shows?|found|"
    r"results?|effects?|training|exercise|muscle|significant)\b",
    re.I,
)
AUTHOR_INIT_HEAD = re.compile(r"[A-Z][\w’'-]+,?\s+[A-Z]\.")

# Publisher first-page front-matter (MDPI / Frontiers). When spliced into an
# OPENING chunk it fools the head-prose guard, but the chunk is real content.
# The same markers can appear in a genuine reference chunk, so this only spares
# when the chunk is also near the START of the paper.
PUBLISHER_FRONTMATTER = re.compile(
    r"MDPI stays neutral|Licensee MDPI|Academic Editor:|"
    r"This article is an open access article distributed|"
    r"Publisher’?s Note: MDPI",
    re.I,
)
FRONTMATTER_MAX_INDEX = 3


def biblio_detail(text: str) -> dict:
    """Reference-list scoring components + verdict. Returns a dict with:
    verdict (bool), doi, repo, author_init, prose_ratio, biblio_evidence.
    """
    if not text:
        return {"verdict": False, "doi": 0, "repo": 0, "author_init": 0,
                "prose_ratio": 0.0, "biblio_evidence": 0}
    doi = len(re.findall(r"doi:\s*10\.|https?://(?:dx\.)?doi|10\.\d{4}/", text, re.I))
    repo = len(re.findall(r"\[(CrossRef|Internet|PubMed|PubMed Central|Google Scholar)\]", text, re.I))
    author_init = len(re.findall(r"[A-Z][a-z]+,\s+[A-Z]\.\s*[A-Z]?\.?", text))
    author_init += len(re.findall(r"[A-Z][a-z]+\s+[A-Z]{1,3},", text))
    prose = len(re.findall(
        r"\b(the|this|that|because|however|therefore|although|suggests?|"
        r"found|showed|these|which|while|when|study|results?|effect)\b",
        text, re.I,
    ))
    n_words = max(1, len(text.split()))
    prose_ratio = prose / n_words
    biblio_evidence = doi + repo * 2 + author_init
    verdict = (
        repo >= 3
        or (author_init >= 8 and doi >= 3)
        or (biblio_evidence >= 8 and prose_ratio < 0.05)
    )
    return {"verdict": verdict, "doi": doi, "repo": repo, "author_init": author_init,
            "prose_ratio": round(prose_ratio, 4), "biblio_evidence": biblio_evidence}


# --- Conservative-mode content guard (ingestion only) --------------------------
# The audit rule was tuned aggressively (98.9% precision) because 15 human
# reviewers were the safety net. Ingestion has no reviewer, so its 1.1% false
# positives would be SILENT drops of real content — specifically the boundary
# chunks where a reference list is fused with a trailing conclusion / table /
# prescription (the 15 the reviewers rescued). In conservative mode we add a
# content guard that SPARES any flagged chunk showing real content, flipping the
# error direction to the safe side: the filter now errs toward keeping (a little
# noise leaks through, swept later by a reviewed pass) rather than losing content.
#
# Two content signals, validated to keep all 15 reviewer-confirmed false
# positives while the filter still auto-drops ~65% of true noise:
#   1. a long uninterrupted prose span (a real paragraph, not citation titles),
#   2. dosage / rep-scheme / statistic patterns (catches data tables & meta-
#      regression results, where numbers break prose runs so signal 1 misses).
# Threshold 20 sits below the observed FP minimum (23) for margin against
# unseen, slightly shorter boundary chunks.
CONSERVATIVE_PROSE_RUN = 20

_CITE_TOKEN = re.compile(r"\b(19|20)\d{2}\b|doi|https?://|10\.\d{4}/|\[(CrossRef|Internet|PubMed|Google Scholar)\]", re.I)
_AUTH_TOKEN = re.compile(r"^[A-Z][\w’'-]+,?$|^[A-Z]\.([A-Z]\.)*[,;]?$|^[A-Z]{1,3}[,;]$")
_ETAL_TOKEN = re.compile(r"^et$|^al\.?,?$", re.I)
_DATA_CONTENT = re.compile(
    r"\d+\s*(?:to|[-–])\s*\d+\s*(?:repetition|rep|set|%|g\b|week)|"
    r"\d+\s*(?:mg/kg|g/kg|g/day|mg\b|mcg|µg|reps|repetition|sets?\b|%\s?1?-?RM|IU)|"
    r"~\s?\d+\s?%|\d+\s*[-–]\s*\d+\s*%|\(\s*-?\d+\.\d+\s*,\s*-?\d+\.\d+\s*\)",
    re.I,
)


def _has_real_content(text: str) -> bool:
    """True if the chunk shows a real content span (long prose run or data)."""
    run = best = 0
    for w in text.split():
        if _CITE_TOKEN.search(w) or _AUTH_TOKEN.match(w) or _ETAL_TOKEN.match(w):
            run = 0
        else:
            run += 1
            best = max(best, run)
    return best >= CONSERVATIVE_PROSE_RUN or bool(_DATA_CONTENT.search(text))


def _head_is_prose(text: str, nwords: int = 40) -> bool:
    """Does the chunk OPEN with a real sentence (vs a citation)?

    Spare guard for boundary chunks — a section transitioning into its reference
    list has real prose first and refs after. The whole-chunk prose ratio is
    fooled by common words in cited titles, so we look only at the head. Errs
    toward KEEPING.
    """
    if not text:
        return False
    head = " ".join(text.split()[:nwords])
    hw = max(1, len(head.split()))
    prose = len(PROSE_HEAD.findall(head))
    inits = len(AUTHOR_INIT_HEAD.findall(head))
    return (prose / hw) >= 0.14 and inits <= 1


def is_noise(text: str, section: str | None, chunk_index: int,
             conservative: bool = False) -> tuple[bool, str]:
    """Classify a chunk. Returns (is_noise, reason).

    reason is "" when kept, or one of: biblio-text, boilerplate-section-nonprose.

    conservative=True (used at ingestion, where there is no human reviewer) adds
    a content guard that spares any otherwise-flagged chunk showing real content,
    so the filter never silently drops content — it errs toward keeping. The
    default (aggressive) mode is what the one-time, human-reviewed corpus audit
    used.
    """
    text = text or ""
    section = section or ""

    if not text.strip():
        return False, ""

    # Opening chunk carrying publisher front-matter -> always real content.
    if chunk_index <= FRONTMATTER_MAX_INDEX and PUBLISHER_FRONTMATTER.search(text):
        return False, ""

    bib = biblio_detail(text)
    head_prose = _head_is_prose(text)

    flagged = False
    reason = ""
    if bib["verdict"] and not head_prose:
        flagged, reason = True, "biblio-text"
    elif BOILERPLATE_SECTION.search(section) and bib["prose_ratio"] < 0.03 and not head_prose:
        flagged, reason = True, "boilerplate-section-nonprose"

    if flagged and conservative and _has_real_content(text):
        return False, ""  # spare: shows real content, don't drop at ingestion
    return flagged, reason
