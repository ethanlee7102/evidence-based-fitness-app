"""Binary/decomposed LLM-as-judge (Phase 2.5, item 4).

Replaces the holistic 1-5 Likert judge (`judge.py`) with metrics **computed from
binary atoms** instead of emitted as a single fuzzy rating. The axis that matters
is emitted-vs-computed: a directly-emitted 0.85 is just Likert rescaled and
carries the same undefined-gap variance; a *computed* 0.85 (17 of 20 binary atoms
supported) is a proportion, arrived at by arithmetic over N reliable y/n calls.

Five metrics (see ROADMAP #25):
  - contextual_recall     — per expected_fact: supported y/n vs chunks -> supported/total
                            (FACT-grounded; the headline "% expected facts retrieved").
                            Attribution semantics: SUPPORTED if >=1 chunk states/implies
                            the fact, even if another chunk disagrees (conflicting
                            corpus evidence is not a recall failure).
  - contextual_relevancy  — per retrieved chunk: relevant-to-question y/n -> relevant/retrieved
  - contextual_precision  — rank-weighted Average Precision over the SAME per-chunk
                            verdicts (rewards relevant chunks ranked early)
  - faithfulness          — per answer-claim: supported-by-chunks y/n -> supported/total
                            (CHUNK-grounded; claims judge-generated per run)
  - answer_relevancy      — binary GATE/tripwire ("addresses the question? y/n"),
                            NOT a scored headline metric

relevancy + precision are computed from ONE shared per-chunk LLM call (two
aggregations of the same atom set). recall's atoms are frozen in the dataset
(`expected_facts`); precision's and faithfulness's are generated per run.

Scoring rule: every metric is a proportion in [0, 1], or `None` when the metric
ERRORED (parse failed after all regenerate retries). A `None` metric is excluded
from aggregates and surfaced — it is NEVER replaced with a synthesized midpoint.
This is the deliberate break from the old judge, which defaulted parse failures
to score 3 (a fabricated value for what is now a computed proportion).

Reuses the shared transport layer from `judge.py`: `_generate_and_parse`
(regenerate-on-parse-failure at escalating temperature), `_format_chunks_for_judge`,
`_extract_json_block`, `JudgeParseError`, and the provider dispatch.
"""

import asyncio
import json
from dataclasses import dataclass, field

from src.core.eval.judge import (
    JUDGE_SYSTEM,
    JudgeParseError,
    _extract_json_block,
    _format_chunks_for_judge,
    _generate_and_parse,
)

# Metric taxonomy — the single source of truth for which metrics are scored
# proportions vs the gate. Imported by runner.py and report.py so the split lives
# in one place. answer_relevancy is a GATE (no numeric score), never in aggregates.
SCORED_METRICS = (
    "contextual_relevancy",
    "contextual_recall",
    "contextual_precision",
    "faithfulness",
)
GATE_METRIC = "answer_relevancy"
HEADLINE_METRIC = "contextual_recall"  # "% expected facts retrieved"

__all__ = [
    "JUDGE_SYSTEM",
    "SCORED_METRICS",
    "GATE_METRIC",
    "HEADLINE_METRIC",
    "AtomVerdict",
    "MetricScore",
    "GateResult",
    "BinaryJudgeResult",
    "average_precision",
    "parse_recall",
    "parse_chunk_verdicts",
    "parse_faithfulness",
    "parse_gate",
    "judge_recall",
    "judge_relevancy_precision",
    "judge_faithfulness",
    "judge_gate",
    "judge_all_binary",
]

# --- Dataclasses -------------------------------------------------------------


@dataclass
class AtomVerdict:
    """One binary decomposition unit: an expected_fact, a retrieved chunk, or an
    answer-claim. `supported` is the y/n verdict (for chunks it means "relevant").
    `index` is the 1-based source position (chunk retrieval rank / fact index)."""

    text: str
    supported: bool
    reasoning: str = ""
    index: int | None = None

    def to_dict(self) -> dict:
        return {"text": self.text, "supported": self.supported, "reasoning": self.reasoning}


@dataclass
class MetricScore:
    """Computed-from-atoms score for one scored metric.

    `score` is a proportion in [0, 1], or `None` when the metric ERRORED and is
    excluded from aggregates. Never a synthesized fallback value. `extra` carries
    the arithmetic provenance (`supported`, `total`, and for precision `ap`).
    """

    score: float | None
    atoms: list[AtomVerdict] = field(default_factory=list)
    reasoning: str = ""
    extra: dict = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict:
        out: dict = {"score": self.score, "reasoning": self.reasoning}
        out.update(self.extra)
        out["atoms"] = [a.to_dict() for a in self.atoms]
        out["error"] = self.error
        return out


@dataclass
class GateResult:
    """Binary pass/fail tripwire (answer_relevancy) — NOT a scored headline metric.

    Serializes WITHOUT a `"score"` key so every downstream loop keyed on
    `["score"]` (report aggregation, overall, analyze_eval_agreement) naturally
    excludes it. `passed` is `None` only on parse error.
    """

    passed: bool | None
    reasoning: str = ""
    error: str | None = None

    def to_dict(self) -> dict:
        gate = "pass" if self.passed else "fail"
        if self.passed is None:
            gate = "error"
        return {
            "gate": gate,
            "passed": self.passed,
            "reasoning": self.reasoning,
            "error": self.error,
        }


@dataclass
class BinaryJudgeResult:
    """All five metric results for a single test case."""

    contextual_relevancy: MetricScore
    contextual_recall: MetricScore  # headline
    contextual_precision: MetricScore
    faithfulness: MetricScore
    answer_relevancy: GateResult

    def to_dict(self) -> dict:
        return {
            "contextual_relevancy": self.contextual_relevancy.to_dict(),
            "contextual_recall": self.contextual_recall.to_dict(),
            "contextual_precision": self.contextual_precision.to_dict(),
            "faithfulness": self.faithfulness.to_dict(),
            "answer_relevancy": self.answer_relevancy.to_dict(),
        }


# --- Average Precision -------------------------------------------------------


def average_precision(verdicts: list[bool]) -> float:
    """Rank-weighted Average Precision over per-chunk relevance verdicts.

    `verdicts` are in retrieval order (rank 1 first). AP rewards relevant chunks
    appearing early: it is the mean, over the relevant positions, of precision@k
    at each relevant rank k. This is the signal a plain relevant/retrieved
    fraction cannot see (same set, better order scores higher).

        AP = (1 / R) * Σ_k  [chunk k relevant] * (relevant in ranks 1..k) / k

    Edge cases: no relevant chunk retrieved (R == 0) and the empty list both
    return 0.0 (standard IR convention; consistent with relevancy == 0.0).
    """
    relevant_total = sum(verdicts)
    if relevant_total == 0:
        return 0.0

    hits = 0
    precision_sum = 0.0
    for rank, is_relevant in enumerate(verdicts, start=1):
        if is_relevant:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / relevant_total


# --- Prompts -----------------------------------------------------------------
# All four reuse JUDGE_SYSTEM + _format_chunks_for_judge. Each asks for a per-atom
# binary verdict; the SCORE is computed by arithmetic here, never emitted by the
# model. `{{ }}` are literal braces for str.format.

RECALL_PROMPT = """\
Evaluate whether the retrieved chunks contain each expected fact.

For EACH expected fact below, decide independently whether it is SUPPORTED by the \
retrieved chunks (a chunk states or clearly implies it) or NOT supported. Judge \
strictly against what the chunks actually say — do not use outside knowledge.

Note on conflicting evidence: chunks may come from different papers that disagree. If \
one chunk states or implies a fact, do NOT mark it unsupported merely because a \
*different* chunk reports a conflicting or opposite result — disagreement between \
chunks is not a recall failure. (This does not lower the bar for support: a fact still \
needs a chunk that actually states or implies it, not merely a weaker or related claim.)

**Expected Facts (numbered):**
{facts}

**Retrieved Chunks:**
{chunks}

Return ONLY JSON with one verdict per fact, keyed by fact number. Include every \
fact index from 1 to {n} exactly once; "supported" must be true or false:
{{"verdicts": [
    {{"fact_index": 1, "supported": true, "reasoning": "<brief>"}}
]}}\
"""

CHUNK_PROMPT = """\
Evaluate whether each retrieved chunk is relevant to the user's question.

For EACH chunk below, decide independently whether it is RELEVANT to answering the \
question (it contains information that helps address the question) or NOT relevant. \
Judge each chunk on its own merits.

**Question:** {question}

**Retrieved Chunks (in retrieval order):**
{chunks}

Return ONLY JSON with one verdict per chunk, keyed by chunk number. Include every \
chunk index from 1 to {n} exactly once; "relevant" must be true or false:
{{"verdicts": [
    {{"chunk_index": 1, "relevant": true, "reasoning": "<brief>"}}
]}}\
"""

FAITHFULNESS_PROMPT = """\
Break the answer into its distinct factual STATEMENTS — roughly one per sentence — \
then judge whether EACH statement is supported by the retrieved chunks. Keep each \
statement at the granularity a reader would verify as a single fact: do NOT split a \
sentence into many sub-claims, and merge trivially-related fragments. Expect a \
handful of statements, not dozens. A statement is SUPPORTED only if the chunks state \
or clearly imply it; one drawn from outside the chunks is NOT supported. If any part \
of a statement is unsupported, mark the whole statement NOT supported. Ignore \
citations, hedging, and non-factual framing.

**Retrieved Chunks:**
{chunks}

**Answer:** {answer}

Return ONLY JSON, one entry per statement; "supported" must be true or false:
{{"claims": [
    {{"claim": "<one factual statement>", "supported": true, "reasoning": "<brief>"}}
]}}\
"""

GATE_PROMPT = """\
Does the answer directly address the user's question? This is a BINARY check of \
relevance only — not quality, completeness, or correctness. An answer that engages \
the right topic and responds to what was asked passes; an off-topic, evasive, or \
non-responsive answer fails.

**Question:** {question}

**Answer:** {answer}

Return ONLY JSON: {{"addresses_question": true, "reasoning": "<brief>"}}\
"""


def _format_facts(expected_facts: list[str]) -> str:
    return "\n".join(f"{i}. {fact}" for i, fact in enumerate(expected_facts, start=1))


def build_recall_prompt(expected_facts: list[str], chunks: list) -> str:
    return RECALL_PROMPT.format(
        facts=_format_facts(expected_facts),
        chunks=_format_chunks_for_judge(chunks),
        n=len(expected_facts),
    )


def build_chunk_prompt(question: str, chunks: list) -> str:
    return CHUNK_PROMPT.format(
        question=question,
        chunks=_format_chunks_for_judge(chunks),
        n=len(chunks),
    )


def build_faithfulness_prompt(chunks: list, answer: str) -> str:
    return FAITHFULNESS_PROMPT.format(
        chunks=_format_chunks_for_judge(chunks), answer=answer
    )


def build_gate_prompt(question: str, answer: str) -> str:
    return GATE_PROMPT.format(question=question, answer=answer)


# --- Parsers -----------------------------------------------------------------
# Every parser raises JudgeParseError on ANY structural defect, so the shared
# `_generate_and_parse` regenerate loop gets a chance to re-sample. After the
# retries exhaust, the caller (step 3) turns the propagated error into an ERRORED
# metric (score=None) — never a synthesized value.


def _parse_json_object(response: str) -> dict:
    """Extract and json-load the response into a dict, or raise JudgeParseError."""
    try:
        data = json.loads(_extract_json_block(response))
    except (json.JSONDecodeError, ValueError) as e:
        raise JudgeParseError(f"Invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise JudgeParseError("Top-level JSON is not an object")
    return data


def _is_int(value) -> bool:
    # bool is a subclass of int — reject it so a JSON `true` index doesn't pass.
    return isinstance(value, int) and not isinstance(value, bool)


def _indexed_verdicts(
    data: dict, list_key: str, index_key: str, bool_key: str, n: int
) -> list[tuple[int, bool, str]]:
    """Validate a list of {index_key, bool_key, reasoning} into an exact bijection
    over 1..n, returned sorted by index. Raises JudgeParseError on any missing,
    extra, duplicate, or wrong-typed unit — never pads or guesses."""
    items = data.get(list_key)
    if not isinstance(items, list):
        raise JudgeParseError(f"Expected a list under '{list_key}'")

    seen: dict[int, tuple[bool, str]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise JudgeParseError(f"'{list_key}' entry is not an object: {item!r}")
        idx = item.get(index_key)
        val = item.get(bool_key)
        if not _is_int(idx):
            raise JudgeParseError(f"'{index_key}' is not an int: {idx!r}")
        if not isinstance(val, bool):
            raise JudgeParseError(f"'{bool_key}' is not a bool: {val!r}")
        if idx in seen:
            raise JudgeParseError(f"Duplicate {index_key} {idx}")
        seen[idx] = (val, str(item.get("reasoning", "")))

    if set(seen) != set(range(1, n + 1)):
        raise JudgeParseError(
            f"Expected exactly {index_key} 1..{n}, got {sorted(seen)}"
        )
    return [(i, seen[i][0], seen[i][1]) for i in range(1, n + 1)]


def parse_recall(response: str, expected_facts: list[str]) -> MetricScore:
    """Per-fact binary recall: supported / total. FACT-grounded."""
    n = len(expected_facts)
    if n == 0:
        # OOS/0-fact cases never reach the judge (runner skips them); guard anyway.
        raise ValueError("parse_recall called with no expected_facts")
    data = _parse_json_object(response)
    verdicts = _indexed_verdicts(data, "verdicts", "fact_index", "supported", n)
    atoms = [
        AtomVerdict(text=expected_facts[i - 1], supported=s, reasoning=r, index=i)
        for (i, s, r) in verdicts
    ]
    supported = sum(1 for a in atoms if a.supported)
    return MetricScore(
        score=supported / n,
        atoms=atoms,
        reasoning=f"{supported}/{n} expected facts supported",
        extra={"supported": supported, "total": n},
    )


def parse_chunk_verdicts(
    response: str, n_chunks: int
) -> tuple[MetricScore, MetricScore]:
    """Parse the ONE shared per-chunk relevance call into (relevancy, precision).

    relevancy = relevant / retrieved (order-independent mean); precision =
    rank-weighted Average Precision over the SAME verdicts in retrieval order.
    """
    if n_chunks == 0:
        # Zero-chunk in-scope cases are handled by the caller without an LLM call.
        raise ValueError("parse_chunk_verdicts called with no chunks")
    data = _parse_json_object(response)
    verdicts = _indexed_verdicts(data, "verdicts", "chunk_index", "relevant", n_chunks)
    atoms = [
        AtomVerdict(text=f"chunk {i}", supported=s, reasoning=r, index=i)
        for (i, s, r) in verdicts
    ]
    ranked = [a.supported for a in atoms]  # already sorted by index == retrieval rank
    relevant = sum(ranked)

    relevancy = MetricScore(
        score=relevant / n_chunks,
        atoms=atoms,
        reasoning=f"{relevant}/{n_chunks} retrieved chunks relevant",
        extra={"supported": relevant, "total": n_chunks},
    )
    ap = average_precision(ranked)
    precision = MetricScore(
        score=ap,
        atoms=atoms,
        reasoning=f"Average Precision over {n_chunks} ranked chunks",
        extra={"ap": round(ap, 4), "relevant": relevant, "total": n_chunks},
    )
    return relevancy, precision


def parse_faithfulness(response: str) -> MetricScore:
    """Per-claim binary faithfulness: supported / total. CHUNK-grounded.

    Claims are judge-generated per run (not frozen), so an empty claim list on a
    non-empty answer is treated as a parse failure (regenerate, then error)."""
    data = _parse_json_object(response)
    claims = data.get("claims")
    if not isinstance(claims, list) or not claims:
        raise JudgeParseError("Expected a non-empty 'claims' list")

    atoms: list[AtomVerdict] = []
    for i, claim in enumerate(claims, start=1):
        if not isinstance(claim, dict):
            raise JudgeParseError(f"'claims' entry is not an object: {claim!r}")
        text = claim.get("claim")
        val = claim.get("supported")
        if not isinstance(text, str) or not text.strip():
            raise JudgeParseError(f"Claim {i} has no text")
        if not isinstance(val, bool):
            raise JudgeParseError(f"Claim {i} 'supported' is not a bool: {val!r}")
        atoms.append(
            AtomVerdict(
                text=text.strip(),
                supported=val,
                reasoning=str(claim.get("reasoning", "")),
                index=i,
            )
        )

    supported = sum(1 for a in atoms if a.supported)
    total = len(atoms)
    return MetricScore(
        score=supported / total,
        atoms=atoms,
        reasoning=f"{supported}/{total} answer claims supported",
        extra={"supported": supported, "total": total},
    )


def parse_gate(response: str) -> GateResult:
    """Binary answer-relevancy gate: does the answer address the question?"""
    data = _parse_json_object(response)
    val = data.get("addresses_question")
    if not isinstance(val, bool):
        raise JudgeParseError(
            f"Missing/non-bool 'addresses_question': {val!r}"
        )
    return GateResult(passed=val, reasoning=str(data.get("reasoning", "")))


# --- Async judge functions ---------------------------------------------------
# Each wraps the shared regenerate-on-parse-failure loop (`_generate_and_parse`).
# On a TERMINAL parse failure (all regenerate retries exhausted) it returns an
# ERRORED result — score=None / passed=None — NEVER a synthesized value. This is
# the deliberate break from the old judge's "default to score 3".

_NO_CHUNKS_NOTE = "no chunks retrieved"


async def _errored(label: str, exc: Exception) -> MetricScore:
    return MetricScore(score=None, error=f"{label} parse failed after retries: {exc}")


async def judge_recall(
    expected_facts: list[str], chunks: list, judge_model: str | None = None
) -> MetricScore:
    """Per-fact binary recall (fact-grounded). Assumes expected_facts is non-empty
    (OOS/0-fact cases are skipped upstream by the runner)."""
    prompt = build_recall_prompt(expected_facts, chunks)
    try:
        return await _generate_and_parse(
            prompt, JUDGE_SYSTEM, lambda r: parse_recall(r, expected_facts), judge_model
        )
    except JudgeParseError as e:
        return await _errored("recall", e)


async def judge_relevancy_precision(
    question: str, chunks: list, judge_model: str | None = None
) -> tuple[MetricScore, MetricScore]:
    """One shared per-chunk call -> (relevancy, precision)."""
    if not chunks:
        # Defensive: an in-scope case with zero chunks is a total retrieval failure
        # (already flagged by the deterministic refusal check). Score 0.0, no LLM
        # call. Does not occur on the current fixture (only OOS cases have 0 chunks,
        # and those are skipped upstream).
        relevancy = MetricScore(
            score=0.0, reasoning=_NO_CHUNKS_NOTE,
            extra={"supported": 0, "total": 0, "note": _NO_CHUNKS_NOTE},
        )
        precision = MetricScore(
            score=0.0, reasoning=_NO_CHUNKS_NOTE,
            extra={"ap": 0.0, "relevant": 0, "total": 0, "note": _NO_CHUNKS_NOTE},
        )
        return relevancy, precision

    prompt = build_chunk_prompt(question, chunks)
    try:
        return await _generate_and_parse(
            prompt, JUDGE_SYSTEM, lambda r: parse_chunk_verdicts(r, len(chunks)), judge_model
        )
    except JudgeParseError as e:
        return await _errored("relevancy", e), await _errored("precision", e)


async def judge_faithfulness(
    chunks: list, answer: str, judge_model: str | None = None
) -> MetricScore:
    """Per-claim binary faithfulness (chunk-grounded)."""
    if not chunks:
        return MetricScore(
            score=0.0, reasoning=_NO_CHUNKS_NOTE,
            extra={"supported": 0, "total": 0, "note": _NO_CHUNKS_NOTE},
        )
    prompt = build_faithfulness_prompt(chunks, answer)
    try:
        return await _generate_and_parse(
            prompt, JUDGE_SYSTEM, parse_faithfulness, judge_model
        )
    except JudgeParseError as e:
        return await _errored("faithfulness", e)


async def judge_gate(
    question: str, answer: str, judge_model: str | None = None
) -> GateResult:
    """Binary answer-relevancy gate."""
    prompt = build_gate_prompt(question, answer)
    try:
        return await _generate_and_parse(prompt, JUDGE_SYSTEM, parse_gate, judge_model)
    except JudgeParseError as e:
        return GateResult(passed=None, error=f"gate parse failed after retries: {e}")


async def judge_all_binary(
    question: str,
    expected_facts: list[str],
    chunks: list,
    answer: str,
    *,
    inter_call_delay: float = 5.0,
    judge_model: str | None = None,
) -> BinaryJudgeResult:
    """Run all four binary judge calls (separate mode only) with rate-limit delays.

    Four LLM calls per scored case: recall, relevancy+precision (shared),
    faithfulness, gate. OOS/0-fact cases are skipped by the runner, not here.
    """
    recall = await judge_recall(expected_facts, chunks, judge_model)
    await asyncio.sleep(inter_call_delay)

    relevancy, precision = await judge_relevancy_precision(question, chunks, judge_model)
    await asyncio.sleep(inter_call_delay)

    faithfulness = await judge_faithfulness(chunks, answer, judge_model)
    await asyncio.sleep(inter_call_delay)

    gate = await judge_gate(question, answer, judge_model)

    return BinaryJudgeResult(
        contextual_relevancy=relevancy,
        contextual_recall=recall,
        contextual_precision=precision,
        faithfulness=faithfulness,
        answer_relevancy=gate,
    )
