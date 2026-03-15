"""Threshold-based pytest assertions for RAG evaluation.

Run with: pytest tests/eval/ -m eval -v

Thresholds should be set AFTER the first baseline run.
Run the eval script first, review scores, then set thresholds at mean - 0.5.
"""

import pytest

# Set after baseline run — start conservative, tighten after first results
THRESHOLDS = {
    "contextual_relevancy": 3.5,
    "contextual_recall": 3.0,
    "contextual_precision": 3.5,
    "answer_relevancy": 3.5,
    "faithfulness": 4.0,  # Highest bar — hallucination is worst failure mode
    "overall": 3.5,
}


@pytest.mark.eval
class TestAggregateThresholds:
    """Test that aggregate metric scores meet minimum thresholds."""

    def test_contextual_relevancy(self, eval_results):
        agg = eval_results["aggregate"]
        assert "contextual_relevancy" in agg, "Missing contextual_relevancy in aggregate"
        score = agg["contextual_relevancy"]["mean"]
        threshold = THRESHOLDS["contextual_relevancy"]
        assert score >= threshold, (
            f"Contextual Relevancy {score:.2f} below threshold {threshold}"
        )

    def test_contextual_recall(self, eval_results):
        agg = eval_results["aggregate"]
        assert "contextual_recall" in agg, "Missing contextual_recall in aggregate"
        score = agg["contextual_recall"]["mean"]
        threshold = THRESHOLDS["contextual_recall"]
        assert score >= threshold, (
            f"Contextual Recall {score:.2f} below threshold {threshold}"
        )

    def test_contextual_precision(self, eval_results):
        agg = eval_results["aggregate"]
        assert "contextual_precision" in agg, "Missing contextual_precision in aggregate"
        score = agg["contextual_precision"]["mean"]
        threshold = THRESHOLDS["contextual_precision"]
        assert score >= threshold, (
            f"Contextual Precision {score:.2f} below threshold {threshold}"
        )

    def test_answer_relevancy(self, eval_results):
        agg = eval_results["aggregate"]
        assert "answer_relevancy" in agg, "Missing answer_relevancy in aggregate"
        score = agg["answer_relevancy"]["mean"]
        threshold = THRESHOLDS["answer_relevancy"]
        assert score >= threshold, (
            f"Answer Relevancy {score:.2f} below threshold {threshold}"
        )

    def test_faithfulness(self, eval_results):
        agg = eval_results["aggregate"]
        assert "faithfulness" in agg, "Missing faithfulness in aggregate"
        score = agg["faithfulness"]["mean"]
        threshold = THRESHOLDS["faithfulness"]
        assert score >= threshold, (
            f"Faithfulness {score:.2f} below threshold {threshold}"
        )

    def test_overall(self, eval_results):
        agg = eval_results["aggregate"]
        assert "overall" in agg, "Missing overall in aggregate"
        score = agg["overall"]["mean"]
        threshold = THRESHOLDS["overall"]
        assert score >= threshold, (
            f"Overall {score:.2f} below threshold {threshold}"
        )


@pytest.mark.eval
class TestNoErrors:
    """Test that no test cases had errors."""

    def test_no_errors(self, eval_results):
        results = eval_results["results"]
        errors = [r for r in results if r.get("error")]
        assert not errors, (
            f"{len(errors)} test case(s) had errors: "
            + ", ".join(f"{r['id']}: {r['error'][:60]}" for r in errors)
        )


@pytest.mark.eval
class TestNoCatastrophicFailures:
    """Test that no individual metric scored 1 (catastrophic failure)."""

    def test_no_score_of_1(self, eval_results):
        results = eval_results["results"]
        failures = []
        for r in results:
            if not r.get("scores"):
                continue
            for metric, data in r["scores"].items():
                if data.get("score") == 1:
                    failures.append(f"{r['id']}/{metric}")
        assert not failures, (
            f"Catastrophic scores (1) found: {', '.join(failures)}"
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
