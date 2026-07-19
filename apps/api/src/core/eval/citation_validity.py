"""Deterministic citation-grounding verifier (Phase 2.5, item 1).

Every grounded answer cites sources inline as `[Author, Year, p. X]` (enforced by
`rag_pipeline.SYSTEM_PROMPT`). Each citation is supposed to point to a chunk that
was ACTUALLY retrieved and handed to the model. The failure this catches: the
model emits a citation for a paper it was never given — a fabricated / misattributed
source. That is a domain-specific hallucination class none of the LLM-judge metrics
score directly.

Pure and deterministic: no API keys, no DB, no LLM — just parsing + normalization +
set membership against the retrieved chunks. Mirrors `src/core/noise_filter.py`.

Two legitimate scholarly forms must NOT be flagged (verified against the real
fixture during design — a naive matcher false-flagged ~47/1528 citations, almost
all of these):
  - Indirect attribution: `X, as cited in Y` / `X, cited in Y` — the model is
    honestly saying "this comes from a paper Y cites." Y is the retrieved source;
    validate Y, not X. X being absent is correct, not a fabrication.
  - Nested parentheticals: `[Wicinski et al., 2019, p. 6 (Skalska…; Orysiak…)]` —
    only the OUTER citation (Wicinski) is the model's source; the parenthetical
    names are papers Wicinski itself cites. Validate the outer citation only.

Page numbers are checked REPORT-ONLY (never gate): formats are messy (`p. 1, 5`,
`pp. 1-2 (Abstract)`) and one paper spans many chunks/pages, so a page outside the
retrieved chunk's range is informational, not a grounding failure.
"""

import re
import unicodedata
from dataclasses import dataclass, field

# A bracketed marker with no nested brackets. We keep only those containing a
# 4-digit year (drops numeric refs like `[49]` and `[Section: Abstract]`).
_BRACKET = re.compile(r"\[([^\[\]]*)\]")
_YEAR = re.compile(r"(?:19|20)\d{2}")
# Secondary-attribution connective: `as cited in Y`, `cited in Y`, or bare `X in Y`
# (the model uses all three). Longest alternatives first so `as cited in` wins over
# a bare `in`. Only treated as indirect when a valid author+year follows it (see
# _parse_part) — so a stray `in press` / `in athletes` falls through to a normal parse.
_INDIRECT = re.compile(r"\b(?:as\s+cited\s+in|cited\s+in|in)\b", re.I)
# Page spans: `p. 5`, `pp. 1-2`, `p. 1, 5`.
_PAGE_GROUP = re.compile(r"pp?\.\s*([\d,\s–-]+)")
_ETAL = re.compile(r"\bet\s*al\.?", re.I)


@dataclass
class Citation:
    """One parsed citation. `match_author`/`match_year` are what we validate
    against the retrieved chunks (the secondary source Y for indirect cites)."""

    raw: str
    author: str          # nominal author as written (X for indirect cites)
    year: int
    match_author: str    # normalized author to match (Y for indirect)
    match_year: int
    indirect: bool = False
    pages: list[int] = field(default_factory=list)


@dataclass
class AnswerCitationResult:
    total: int = 0
    grounded: list[Citation] = field(default_factory=list)
    ungrounded: list[Citation] = field(default_factory=list)
    # Report-only: grounded citations whose page isn't in the paper's retrieved range.
    page_mismatches: list[Citation] = field(default_factory=list)
    indirect_count: int = 0
    # False for a no-chunks refusal with nothing to check (clean OOS answer).
    applicable: bool = False


def normalize_author(name: str) -> str:
    """Canonical author key: strip accents, `et al.`, punctuation, case, hyphens.

    `Piñero et al.` -> `pinero`; `Androulakis-Korakakis et al.` -> `androulakis
    korakakis` (so the hyphen and space variants collide); `Schoenfeld et al.` ->
    `schoenfeld`.
    """
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    s = _ETAL.sub(" ", s).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)  # hyphens, commas, periods -> space
    return re.sub(r"\s+", " ", s).strip()


def _author_matches(cit: str, chunk: str) -> bool:
    """True if the citation author and chunk author refer to the same first author.

    Exact on the normalized key, or one is a whitespace-prefix of the other
    (`schoenfeld` vs `schoenfeld grgic`) — tolerates the model dropping/adding a
    second surname while staying conservative about unrelated authors.
    """
    if not cit or not chunk:
        return False
    return (
        cit == chunk
        or chunk.startswith(cit + " ")
        or cit.startswith(chunk + " ")
    )


def _extract_pages(text: str) -> list[int]:
    """All page integers mentioned after `p.`/`pp.` markers (report-only)."""
    pages: list[int] = []
    for grp in _PAGE_GROUP.findall(text):
        pages.extend(int(n) for n in re.findall(r"\d+", grp))
    return pages


def _split_top_level(inner: str) -> list[str]:
    """Split a bracket's inner text on `;` at paren-depth 0 only.

    Keeps `[A, 2020, p.1; B, 2021, p.9]` as two citations while leaving the
    semicolons inside `(Skalska…; Orysiak…)` untouched.
    """
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(inner):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == ";" and depth == 0:
            parts.append(inner[start:i])
            start = i + 1
    parts.append(inner[start:])
    return [p for p in parts if p.strip()]


def _strip_parens(text: str) -> str:
    """Remove parenthetical groups — nested references and `(Abstract)` tags."""
    return re.sub(r"\([^()]*\)", " ", text)


def _author_year(segment: str) -> tuple[str, int] | None:
    """Author (text before the first year) + year, from a paren-stripped segment."""
    m = _YEAR.search(segment)
    if not m:
        return None
    author = segment[: m.start()].strip().strip(",;").strip()
    if not author:
        return None
    return author, int(m.group())


def _parse_part(part: str) -> Citation | None:
    """Parse one primary citation (already split off a bracket)."""
    pages = _extract_pages(part)
    clean = _strip_parens(part)

    m = _INDIRECT.search(clean)
    if m:
        # `X (as) cited in Y` / `X in Y` — validate the citing source Y (retrieved).
        head, tail = clean[: m.start()], clean[m.end() :]
        target = _author_year(tail)
        if target is not None:
            nominal = _author_year(head)
            x_author = nominal[0] if nominal else target[0]
            x_year = nominal[1] if nominal else target[1]
            return Citation(
                raw=part.strip(), author=x_author, year=x_year,
                match_author=normalize_author(target[0]), match_year=target[1],
                indirect=True, pages=pages,
            )
        # marker present but nothing citable after it -> fall through to normal parse.

    ay = _author_year(clean)
    if ay is None:
        return None
    author, year = ay
    return Citation(
        raw=part.strip(), author=author, year=year,
        match_author=normalize_author(author), match_year=year,
        indirect=False, pages=pages,
    )


def parse_citations(answer: str) -> list[Citation]:
    """Extract every `[Author, Year, …]` citation from an answer."""
    out: list[Citation] = []
    for inner in _BRACKET.findall(answer or ""):
        if not _YEAR.search(inner):
            continue  # not a paper citation (numeric ref, section tag, …)
        for part in _split_top_level(inner):
            cit = _parse_part(part)
            if cit is not None:
                out.append(cit)
    return out


def _chunk_field(chunk, name: str):
    """Read a field from a ChunkResponse object or a raw fixture dict."""
    if isinstance(chunk, dict):
        return chunk.get(name)
    return getattr(chunk, name, None)


def check_answer(answer: str, chunks: list) -> AnswerCitationResult:
    """Validate every citation in `answer` against the retrieved `chunks`.

    `chunks` items may be ChunkResponse objects or raw dicts exposing
    `authors`, `year`, `page_start`, `page_end`.
    """
    citations = parse_citations(answer)

    # Normalized (author, year) -> union of retrieved page ranges for that paper.
    paper_pages: dict[tuple[str, int], set[int]] = {}
    for ch in chunks:
        key = (normalize_author(_chunk_field(ch, "authors") or ""), _chunk_field(ch, "year"))
        if not key[0] or key[1] is None:
            continue
        ps, pe = _chunk_field(ch, "page_start"), _chunk_field(ch, "page_end")
        rng = paper_pages.setdefault(key, set())
        if ps is not None:
            rng.update(range(int(ps), int(pe if pe is not None else ps) + 1))

    result = AnswerCitationResult(
        total=len(citations),
        applicable=bool(chunks) or bool(citations),
    )

    for cit in citations:
        if cit.indirect:
            result.indirect_count += 1
        matched_key = next(
            (
                k for k in paper_pages
                if k[1] == cit.match_year and _author_matches(cit.match_author, k[0])
            ),
            None,
        )
        if matched_key is None:
            result.ungrounded.append(cit)
            continue
        result.grounded.append(cit)
        # Report-only page check: did the model cite a page we didn't provide?
        rng = paper_pages[matched_key]
        if cit.pages and rng and not any(p in rng for p in cit.pages):
            result.page_mismatches.append(cit)

    return result
