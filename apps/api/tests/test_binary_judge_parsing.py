"""Offline unit tests for the binary/decomposed judge (`src/core/eval/binary_judge.py`).

Pure, deterministic pieces only — no API keys, no network. Intentionally NOT
marked `eval` so they run in the `pytest -m "not eval"` CI PR gate alongside the
citation/deterministic-check tests.

This file grows with the migration:
  - Step 1 (here): dataclasses + `average_precision`.
  - Step 2: the four per-metric parsers (bijection validation, JudgeParseError).
  - Step 3: the error-not-3 regression (a parse failure ERRORS the metric,
            never synthesizes a value).
"""

import asyncio
import json

import pytest

from src.core.eval.binary_judge import (
    AtomVerdict,
    BinaryJudgeResult,
    GateResult,
    MetricScore,
    average_precision,
    judge_all_binary,
    judge_faithfulness,
    judge_gate,
    judge_recall,
    judge_relevancy_precision,
    parse_chunk_verdicts,
    parse_faithfulness,
    parse_gate,
    parse_recall,
)
from src.core.eval.judge import JudgeParseError

CHUNKS = [{"chunk_text": "some text", "authors": "Smith", "year": 2020}]

# --- average_precision -------------------------------------------------------


@pytest.mark.parametrize(
    "verdicts,expected",
    [
        ([], 0.0),
        ([False, False], 0.0),
        ([True], 1.0),
        ([False, True], 0.5),  # (2/2)/1 = 0.5
        ([True, False, True, True], 0.8055555555555556),  # (1/1 + 2/3 + 3/4)/3
        ([True, True, True], 1.0),
        ([True, False, False], 1.0),  # single relevant at rank 1 -> perfect
        ([False, False, True], 1 / 3),  # (1/3)/1
    ],
)
def test_average_precision(verdicts, expected):
    assert average_precision(verdicts) == pytest.approx(expected)


def test_average_precision_is_order_sensitive():
    """Same relevant/retrieved fraction, different order -> different AP.

    This is the whole reason precision is kept distinct from relevancy: a
    relevant/retrieved fraction would score these two identically (both 3/5)."""
    front_loaded = [True, True, True, False, False]
    scattered = [True, False, False, True, True]
    assert average_precision(front_loaded) == pytest.approx(1.0)
    assert average_precision(scattered) == pytest.approx((1 / 1 + 2 / 4 + 3 / 5) / 3)
    assert average_precision(front_loaded) > average_precision(scattered)


# --- dataclass shapes --------------------------------------------------------


def test_metricscore_constructible_and_serializes():
    ms = MetricScore(
        score=0.75,
        atoms=[
            AtomVerdict(text="fact A", supported=True, reasoning="found", index=1),
            AtomVerdict(text="fact B", supported=False, reasoning="missing", index=2),
        ],
        reasoning="3 of 4 supported",
        extra={"supported": 3, "total": 4},
    )
    d = ms.to_dict()
    assert d["score"] == 0.75
    assert d["supported"] == 3 and d["total"] == 4
    assert d["error"] is None
    assert d["atoms"] == [
        {"text": "fact A", "supported": True, "reasoning": "found"},
        {"text": "fact B", "supported": False, "reasoning": "missing"},
    ]


def test_metricscore_errored_carries_none_score():
    ms = MetricScore(score=None, error="parse failed after retries")
    d = ms.to_dict()
    assert d["score"] is None
    assert d["error"] == "parse failed after retries"


def test_precision_metricscore_carries_ap():
    ms = MetricScore(score=0.5, extra={"ap": 0.806})
    assert ms.to_dict()["ap"] == 0.806


def test_gateresult_has_no_score_key():
    """The gate must not serialize a `score` key — downstream aggregation loops
    key on `["score"]` and rely on its absence to exclude the gate."""
    assert GateResult(passed=True).to_dict() == {
        "gate": "pass",
        "passed": True,
        "reasoning": "",
        "error": None,
    }
    assert GateResult(passed=False, reasoning="off-topic").to_dict()["gate"] == "fail"
    errored = GateResult(passed=None, error="parse failed").to_dict()
    assert errored["gate"] == "error" and errored["passed"] is None
    assert "score" not in GateResult(passed=True).to_dict()


def test_binaryjudgeresult_to_dict_shape():
    ms = MetricScore(score=1.0, extra={"supported": 1, "total": 1})
    result = BinaryJudgeResult(
        contextual_relevancy=ms,
        contextual_recall=ms,
        contextual_precision=MetricScore(score=1.0, extra={"ap": 1.0}),
        faithfulness=ms,
        answer_relevancy=GateResult(passed=True),
    )
    d = result.to_dict()
    assert set(d) == {
        "contextual_relevancy",
        "contextual_recall",
        "contextual_precision",
        "faithfulness",
        "answer_relevancy",
    }
    assert d["contextual_precision"]["ap"] == 1.0
    assert "score" not in d["answer_relevancy"]


# --- parse_recall ------------------------------------------------------------

FACTS = ["fact one", "fact two", "fact three"]


def _recall_json(*verdicts):
    return json.dumps({"verdicts": list(verdicts)})


def test_parse_recall_bijection_maps_atoms_to_facts():
    resp = _recall_json(
        {"fact_index": 1, "supported": True, "reasoning": "a"},
        {"fact_index": 2, "supported": False, "reasoning": "b"},
        {"fact_index": 3, "supported": True, "reasoning": "c"},
    )
    ms = parse_recall(resp, FACTS)
    assert ms.score == pytest.approx(2 / 3)
    assert ms.extra == {"supported": 2, "total": 3}
    # atoms mapped to the correct fact text, in index order
    assert [a.text for a in ms.atoms] == FACTS
    assert [a.supported for a in ms.atoms] == [True, False, True]


def test_parse_recall_out_of_order_input_is_sorted_by_index():
    resp = _recall_json(
        {"fact_index": 3, "supported": True},
        {"fact_index": 1, "supported": False},
        {"fact_index": 2, "supported": True},
    )
    ms = parse_recall(resp, FACTS)
    assert [a.index for a in ms.atoms] == [1, 2, 3]
    assert [a.text for a in ms.atoms] == FACTS
    assert [a.supported for a in ms.atoms] == [False, True, True]


def test_parse_recall_all_false_is_zero():
    resp = _recall_json(
        {"fact_index": 1, "supported": False},
        {"fact_index": 2, "supported": False},
        {"fact_index": 3, "supported": False},
    )
    assert parse_recall(resp, FACTS).score == 0.0


def test_parse_recall_strips_markdown_fence():
    resp = "```json\n" + _recall_json(
        {"fact_index": 1, "supported": True},
        {"fact_index": 2, "supported": True},
        {"fact_index": 3, "supported": True},
    ) + "\n```"
    assert parse_recall(resp, FACTS).score == 1.0


@pytest.mark.parametrize(
    "verdicts",
    [
        # missing fact 3
        [{"fact_index": 1, "supported": True}, {"fact_index": 2, "supported": True}],
        # extra fact 4
        [
            {"fact_index": 1, "supported": True},
            {"fact_index": 2, "supported": True},
            {"fact_index": 3, "supported": True},
            {"fact_index": 4, "supported": True},
        ],
        # duplicate fact 1
        [
            {"fact_index": 1, "supported": True},
            {"fact_index": 1, "supported": False},
            {"fact_index": 3, "supported": True},
        ],
        # non-bool supported
        [
            {"fact_index": 1, "supported": "yes"},
            {"fact_index": 2, "supported": True},
            {"fact_index": 3, "supported": True},
        ],
    ],
)
def test_parse_recall_raises_on_broken_bijection(verdicts):
    with pytest.raises(JudgeParseError):
        parse_recall(json.dumps({"verdicts": verdicts}), FACTS)


def test_parse_recall_raises_on_no_json():
    with pytest.raises(JudgeParseError):
        parse_recall("the model wrote prose with no json", FACTS)


# --- parse_chunk_verdicts (relevancy + precision) ----------------------------


def _chunk_json(*verdicts):
    return json.dumps({"verdicts": list(verdicts)})


def test_parse_chunk_verdicts_two_aggregations_from_same_atoms():
    resp = _chunk_json(
        {"chunk_index": 1, "relevant": True},
        {"chunk_index": 2, "relevant": False},
        {"chunk_index": 3, "relevant": True},
        {"chunk_index": 4, "relevant": True},
    )
    relevancy, precision = parse_chunk_verdicts(resp, 4)
    # relevancy == relevant/retrieved (order-independent mean)
    assert relevancy.score == pytest.approx(3 / 4)
    # precision == AP over the SAME verdicts in rank order
    assert precision.score == pytest.approx(average_precision([True, False, True, True]))
    # both share the same atom set
    assert relevancy.atoms == precision.atoms
    assert precision.extra["ap"] == round(precision.score, 4)


def test_parse_chunk_verdicts_out_of_order_sorted_before_ap():
    # front-loaded relevant chunks, delivered out of order -> must sort to ranks
    # 1..4 = [T, T, F, F] before computing AP (AP is order-sensitive).
    resp = _chunk_json(
        {"chunk_index": 4, "relevant": False},
        {"chunk_index": 2, "relevant": True},
        {"chunk_index": 1, "relevant": True},
        {"chunk_index": 3, "relevant": False},
    )
    relevancy, precision = parse_chunk_verdicts(resp, 4)
    assert relevancy.score == pytest.approx(2 / 4)
    assert precision.score == pytest.approx(average_precision([True, True, False, False]))
    assert precision.score == pytest.approx(1.0)  # both relevant ranked first


def test_parse_chunk_verdicts_raises_on_missing_chunk():
    resp = _chunk_json(
        {"chunk_index": 1, "relevant": True},
        {"chunk_index": 2, "relevant": True},
    )
    with pytest.raises(JudgeParseError):
        parse_chunk_verdicts(resp, 3)


# --- parse_faithfulness ------------------------------------------------------


def test_parse_faithfulness_proportion():
    resp = json.dumps(
        {
            "claims": [
                {"claim": "A", "supported": True, "reasoning": "x"},
                {"claim": "B", "supported": False},
                {"claim": "C", "supported": True},
            ]
        }
    )
    ms = parse_faithfulness(resp)
    assert ms.score == pytest.approx(2 / 3)
    assert ms.extra == {"supported": 2, "total": 3}
    assert [a.text for a in ms.atoms] == ["A", "B", "C"]


def test_parse_faithfulness_empty_claims_raises():
    with pytest.raises(JudgeParseError):
        parse_faithfulness(json.dumps({"claims": []}))


@pytest.mark.parametrize(
    "resp",
    [
        json.dumps({"claims": [{"claim": "A", "supported": "true"}]}),  # non-bool
        json.dumps({"claims": [{"claim": "", "supported": True}]}),  # empty text
        json.dumps({"claims": [{"supported": True}]}),  # missing claim text
        "no json at all",
    ],
)
def test_parse_faithfulness_raises_on_malformed(resp):
    with pytest.raises(JudgeParseError):
        parse_faithfulness(resp)


# --- parse_gate --------------------------------------------------------------


def test_parse_gate_pass_and_fail():
    assert parse_gate(json.dumps({"addresses_question": True})).passed is True
    fail = parse_gate(json.dumps({"addresses_question": False, "reasoning": "off"}))
    assert fail.passed is False and fail.reasoning == "off"


@pytest.mark.parametrize(
    "resp",
    [
        json.dumps({"addresses_question": "yes"}),  # non-bool
        json.dumps({"reasoning": "no verdict"}),  # missing key
        "prose only",
    ],
)
def test_parse_gate_raises_on_malformed(resp):
    with pytest.raises(JudgeParseError):
        parse_gate(resp)


# --- error-not-3 regression (the migration's core guard) ---------------------
# When every regenerate retry returns unparseable output, the metric must ERROR
# (score=None + error set) — never a synthesized value (no 3, no 0.6, no 0.0).


@pytest.fixture
def unparseable_judge(monkeypatch):
    """Force _generate_with_retry to always return junk, and no-op the retry
    sleeps so the exhausted-retry path runs fast."""

    async def fake_generate(*args, **kwargs):
        return "the model wrote prose and no JSON at all"

    async def fake_sleep(*args, **kwargs):
        return None

    monkeypatch.setattr("src.core.eval.judge._generate_with_retry", fake_generate)
    monkeypatch.setattr("src.core.eval.judge.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("src.core.eval.binary_judge.asyncio.sleep", fake_sleep)


def test_recall_errors_not_synthesizes(unparseable_judge):
    ms = asyncio.run(judge_recall(FACTS, CHUNKS))
    assert ms.score is None
    assert ms.error and "parse failed" in ms.error


def test_relevancy_precision_both_error(unparseable_judge):
    relevancy, precision = asyncio.run(judge_relevancy_precision("q?", CHUNKS))
    assert relevancy.score is None and relevancy.error
    assert precision.score is None and precision.error


def test_faithfulness_errors_not_synthesizes(unparseable_judge):
    ms = asyncio.run(judge_faithfulness(CHUNKS, "some answer"))
    assert ms.score is None and ms.error


def test_gate_errors_to_none_not_false(unparseable_judge):
    """A parse failure must be `passed=None` (errored), NOT `passed=False`
    (a real 'off-topic' verdict) — the two mean different things."""
    gate = asyncio.run(judge_gate("q?", "a"))
    assert gate.passed is None
    assert gate.error


def test_judge_all_binary_errors_every_metric(unparseable_judge):
    result = asyncio.run(judge_all_binary("q?", FACTS, CHUNKS, "answer"))
    assert result.contextual_recall.score is None
    assert result.contextual_relevancy.score is None
    assert result.contextual_precision.score is None
    assert result.faithfulness.score is None
    assert result.answer_relevancy.passed is None
    # to_dict is still serializable with all-errored metrics
    d = result.to_dict()
    assert d["contextual_recall"]["score"] is None
    assert d["answer_relevancy"]["gate"] == "error"


def test_no_synthesized_value_anywhere(unparseable_judge):
    """Belt-and-suspenders: the forbidden fallbacks (3, 0.6, 0.0) must NEVER
    appear from a parse failure. Only None is acceptable."""
    result = asyncio.run(judge_all_binary("q?", FACTS, CHUNKS, "answer"))
    for metric in (
        result.contextual_recall,
        result.contextual_relevancy,
        result.contextual_precision,
        result.faithfulness,
    ):
        assert metric.score is None  # not 3, not 0.6, not 0.0


# --- happy path: async judge functions parse a valid response ----------------
# The error tests above never actually PARSE anything, so they can't catch a
# wiring bug (wrong lambda, swapped relevancy/precision slots). These do.


@pytest.fixture
def good_judge(monkeypatch):
    """Patch _generate_with_retry to return valid JSON matched to each metric's
    prompt (by a marker only that prompt contains), and no-op the sleeps."""

    async def fake_generate(prompt, system, judge_model=None, temperature=0.0, **kw):
        if "fact_index" in prompt:  # recall
            return json.dumps(
                {"verdicts": [{"fact_index": i + 1, "supported": i == 0}
                              for i in range(len(FACTS))]}
            )
        if "chunk_index" in prompt:  # relevancy+precision
            n = prompt.count("[Chunk ")
            return json.dumps(
                {"verdicts": [{"chunk_index": i + 1, "relevant": True}
                              for i in range(n)]}
            )
        if "claims" in prompt:  # faithfulness
            return json.dumps(
                {"claims": [{"claim": "c1", "supported": True},
                            {"claim": "c2", "supported": False}]}
            )
        return json.dumps({"addresses_question": True})  # gate

    async def fake_sleep(*a, **k):
        return None

    monkeypatch.setattr("src.core.eval.judge._generate_with_retry", fake_generate)
    monkeypatch.setattr("src.core.eval.judge.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("src.core.eval.binary_judge.asyncio.sleep", fake_sleep)


def test_judge_recall_happy(good_judge):
    ms = asyncio.run(judge_recall(FACTS, CHUNKS))
    assert ms.score == pytest.approx(1 / 3)  # only fact 1 supported
    assert ms.error is None
    assert [a.text for a in ms.atoms] == FACTS
    assert ms.atoms[0].supported is True and ms.atoms[1].supported is False


def test_judge_relevancy_precision_happy_slots_not_swapped(monkeypatch):
    """Prove the (relevancy, precision) return order isn't swapped: pick a verdict
    pattern where mean != AP so the two are distinguishable."""

    async def chunk_fake(prompt, system, judge_model=None, temperature=0.0, **kw):
        return json.dumps(
            {"verdicts": [
                {"chunk_index": 1, "relevant": False},
                {"chunk_index": 2, "relevant": True},
                {"chunk_index": 3, "relevant": True},
                {"chunk_index": 4, "relevant": True},
            ]}
        )

    monkeypatch.setattr("src.core.eval.judge._generate_with_retry", chunk_fake)
    four = [{"chunk_text": f"c{i}", "authors": "A", "year": 2020} for i in range(4)]
    relevancy, precision = asyncio.run(judge_relevancy_precision("q?", four))
    assert relevancy.score == pytest.approx(3 / 4)  # mean
    assert precision.score == pytest.approx(average_precision([False, True, True, True]))
    assert relevancy.score != precision.score  # distinct -> slots correct


def test_judge_faithfulness_happy(good_judge):
    ms = asyncio.run(judge_faithfulness(CHUNKS, "answer text"))
    assert ms.score == pytest.approx(0.5)
    assert ms.error is None


def test_judge_gate_happy(good_judge):
    gate = asyncio.run(judge_gate("q?", "a"))
    assert gate.passed is True and gate.error is None


def test_judge_all_binary_happy(good_judge):
    result = asyncio.run(judge_all_binary("q?", FACTS, CHUNKS, "answer"))
    assert result.contextual_recall.score == pytest.approx(1 / 3)
    assert result.contextual_relevancy.score == pytest.approx(1.0)  # 1 chunk, relevant
    assert result.contextual_precision.score == pytest.approx(1.0)
    assert result.faithfulness.score == pytest.approx(0.5)
    assert result.answer_relevancy.passed is True
    for m in (result.contextual_recall, result.contextual_relevancy,
              result.contextual_precision, result.faithfulness):
        assert m.error is None
