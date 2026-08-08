"""Threshold-based pytest assertions for the binary RAG evaluation.

Run with: pytest tests/eval/ -m eval -v

Metrics are proportions in [0, 1] (see `binary_judge.py`). answer_relevancy is a
GATE, asserted as a pass-rate, not a scored threshold.

These are eval-marked (live judge API calls) and excluded from CI. They are a
regression tripwire, run on demand against the current system.
"""

import pytest

# Finalized from the v2 binary baseline (results/run2_binary_baseline.json, 2026-08-08;
# refined atomic facts + chunk-vs-chunk recall prompt):
#   Rel 0.882 / Rec 0.791 / Pre 0.959 / Fai 0.978 / Overall 0.902 / Gate 1.000.
# Set ~0.10 below each baseline mean: a tripwire that catches a real system
# regression without false-alarming on run-to-run judge variance (temp 0, but
# faithfulness claim-generation and the recall/relevancy calls still wobble).
THRESHOLDS = {
    "contextual_relevancy": 0.78,
    "contextual_recall": 0.69,
    "contextual_precision": 0.85,
    "faithfulness": 0.88,  # highest bar — hallucination is the worst failure mode
    "overall": 0.80,
}

# answer_relevancy gate: the answer must address the question on nearly every case.
GATE_MIN_PASS_RATE = 0.95


@pytest.mark.eval
class TestAggregateThresholds:
    """Test that aggregate metric proportions meet minimum thresholds."""

    def test_contextual_relevancy(self, eval_results):
        agg = eval_results["aggregate"]
        assert "contextual_relevancy" in agg, "Missing contextual_relevancy in aggregate"
        score = agg["contextual_relevancy"]["mean"]
        threshold = THRESHOLDS["contextual_relevancy"]
        assert score >= threshold, (
            f"Contextual Relevancy {score:.3f} below threshold {threshold}"
        )

    def test_contextual_recall(self, eval_results):
        agg = eval_results["aggregate"]
        assert "contextual_recall" in agg, "Missing contextual_recall in aggregate"
        score = agg["contextual_recall"]["mean"]
        threshold = THRESHOLDS["contextual_recall"]
        assert score >= threshold, (
            f"Contextual Recall {score:.3f} below threshold {threshold}"
        )

    def test_contextual_precision(self, eval_results):
        agg = eval_results["aggregate"]
        assert "contextual_precision" in agg, "Missing contextual_precision in aggregate"
        score = agg["contextual_precision"]["mean"]
        threshold = THRESHOLDS["contextual_precision"]
        assert score >= threshold, (
            f"Contextual Precision {score:.3f} below threshold {threshold}"
        )

    def test_faithfulness(self, eval_results):
        agg = eval_results["aggregate"]
        assert "faithfulness" in agg, "Missing faithfulness in aggregate"
        score = agg["faithfulness"]["mean"]
        threshold = THRESHOLDS["faithfulness"]
        assert score >= threshold, (
            f"Faithfulness {score:.3f} below threshold {threshold}"
        )

    def test_overall(self, eval_results):
        agg = eval_results["aggregate"]
        assert "overall" in agg, "Missing overall in aggregate"
        score = agg["overall"]["mean"]
        threshold = THRESHOLDS["overall"]
        assert score >= threshold, (
            f"Overall {score:.3f} below threshold {threshold}"
        )


@pytest.mark.eval
class TestAnswerRelevancyGate:
    """The answer-relevancy tripwire: answers must address the question."""

    def test_gate_pass_rate(self, eval_results):
        gate = eval_results["aggregate"].get("answer_relevancy_gate", {})
        rate = gate.get("pass_rate")
        assert rate is not None, "Missing answer_relevancy_gate pass_rate"
        assert rate >= GATE_MIN_PASS_RATE, (
            f"Answer-relevancy gate pass-rate {rate:.3f} below {GATE_MIN_PASS_RATE} "
            f"(failures: {gate.get('failures')})"
        )


@pytest.mark.eval
class TestNoErrors:
    """No case-level errors, and no metric silently errored out of the aggregate."""

    def test_no_case_errors(self, eval_results):
        results = eval_results["results"]
        errors = [r for r in results if r.get("error")]
        assert not errors, (
            f"{len(errors)} test case(s) had errors: "
            + ", ".join(f"{r['id']}: {r['error'][:60]}" for r in errors)
        )

    def test_no_errored_metrics(self, eval_results):
        errored = eval_results["aggregate"].get("errored_metrics", [])
        assert not errored, (
            f"{len(errored)} metric(s) errored (excluded from aggregates): "
            + ", ".join(f"{e['id']}/{e['metric']}" for e in errored)
        )


@pytest.mark.eval
class TestNoCatastrophicFailures:
    """No scored metric bottomed out at 0.0 (nothing supported / no relevant chunk)."""

    def test_no_score_of_zero(self, eval_results):
        results = eval_results["results"]
        failures = []
        for r in results:
            if not r.get("scores"):
                continue
            for metric, data in r["scores"].items():
                # gate has no 'score' key; scored metrics may be None (errored)
                if data.get("score") == 0.0:
                    failures.append(f"{r['id']}/{metric}")
        assert not failures, (
            f"Catastrophic scores (0.0) found: {', '.join(failures)}"
        )


@pytest.mark.eval
class TestOutOfScope:
    """Test that out-of-scope questions return grounded=false."""

    def test_oos_ungrounded(self, eval_results):
        results = eval_results["results"]
        oos = [r for r in results if "out-of-scope" in r.get("tags", [])]
        assert oos, "No out-of-scope test cases found"

        grounded_oos = [
            r["id"]
            for r in oos
            if r.get("rag_result", {}).get("grounded", True)
        ]
        assert not grounded_oos, (
            f"Out-of-scope cases returned grounded=true: {grounded_oos}"
        )
