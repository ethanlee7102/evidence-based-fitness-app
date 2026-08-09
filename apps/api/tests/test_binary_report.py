"""Offline unit tests for binary-eval aggregation (`src/core/eval/report.py`).

Feeds synthetic report dicts (0-1 proportions, an errored metric, a gate fail, an
OOS case, a case-level error, an all-errored case) and asserts the aggregation
rules that encode the migration's decisions: errored metrics are EXCLUDED (never
counted as 0), the headline is recall, and the gate is a separate pass-rate.

Not marked `eval` -> runs in the `pytest -m "not eval"` CI gate.
"""

import pytest

from src.core.eval.report import compute_aggregates, print_summary


def _scored(rel, rec, pre, fai, gate_passed, overall):
    """A scored case's dict. Any metric value of None means it errored."""

    def metric(score):
        d = {"score": score, "reasoning": "", "atoms": [], "error": None}
        if score is None:
            d["error"] = "parse failed after retries"
        return d

    gate = {"gate": "pass" if gate_passed else "fail", "passed": gate_passed,
            "reasoning": "", "error": None}
    if gate_passed is None:
        gate = {"gate": "error", "passed": None, "reasoning": "", "error": "boom"}
    return {
        "scores": {
            "contextual_relevancy": metric(rel),
            "contextual_recall": metric(rec),
            "contextual_precision": metric(pre),
            "faithfulness": metric(fai),
            "answer_relevancy": gate,
        },
        "overall_score": overall,
    }


def _case(cid, category, difficulty, tags, scores_case=None, error=None):
    base = {
        "id": cid,
        "question": f"q for {cid}",
        "category": category,
        "difficulty": difficulty,
        "tags": tags,
        "scores": None,
        "overall_score": None,
        "rag_result": {"grounded": bool(scores_case), "answer": "a"},
        "error": error,
    }
    if scores_case:
        base.update(scores_case)
    return base


def _report():
    A = _case("HYP-A", "hypertrophy", "medium", ["multi-paper"],
              _scored(0.8, 0.6, 0.9, 1.0, True, 0.825))
    B = _case("STR-B", "strength", "hard", ["single-paper"],
              _scored(0.6, 0.4, None, 0.8, False, 0.6))  # precision errored, gate fail
    C = _case("OOS-1", "out-of-scope", "medium", ["out-of-scope"])  # scores=None
    D = _case("ERR-D", "nutrition", "easy", [], error="rag query failed")  # case error
    E = _case("ALL-E", "recovery", "medium", [],
              _scored(None, None, None, None, None, None))  # every metric errored
    return {
        "metadata": {
            "timestamp": "2026-07-24T00:00:00",
            "model": "gemini-2.5-flash",
            "judge_model": "gemini-2.5-flash",
            "top_k": 5,
            "duration_s": 120.0,
            "judge_mode": "binary",
            "total_cases": 5,
            "failed_cases": 1,
            "metrics_filter": None,
        },
        "results": [A, B, C, D, E],
    }


def test_recall_mean_excludes_oos_and_errors():
    agg = compute_aggregates(_report())["aggregate"]
    # recall values come from A (0.6) and B (0.4) only; C/D/E excluded.
    assert agg["contextual_recall"]["mean"] == pytest.approx(0.5)
    assert agg["contextual_recall"]["n"] == 2


def test_headline_is_recall():
    agg = compute_aggregates(_report())["aggregate"]
    assert agg["headline"]["recall"] == pytest.approx(0.5)


def test_errored_metric_excluded_and_counted():
    agg = compute_aggregates(_report())["aggregate"]
    pre = agg["contextual_precision"]
    # A supplies 0.9; B errored; E errored -> mean is 0.9 over n=1, 2 errored.
    assert pre["mean"] == pytest.approx(0.9)
    assert pre["n"] == 1
    assert pre["n_errored"] == 2


def test_errored_metrics_surfaced():
    agg = compute_aggregates(_report())["aggregate"]
    errored = agg["errored_metrics"]
    pairs = {(e["id"], e["metric"]) for e in errored}
    assert ("STR-B", "contextual_precision") in pairs
    # every metric of the all-errored case is surfaced, incl. the gate
    assert ("ALL-E", "contextual_recall") in pairs
    assert ("ALL-E", "answer_relevancy") in pairs


def test_gate_pass_rate():
    agg = compute_aggregates(_report())["aggregate"]
    gate = agg["answer_relevancy_gate"]
    # A passes, B fails, E errored (excluded). pass_rate = 1/2.
    assert gate["passed"] == 1
    assert gate["failures"] == ["STR-B"]
    assert gate["pass_rate"] == pytest.approx(0.5)
    assert gate["n_errored"] == 1


def test_overall_blended_mean_excludes_none():
    agg = compute_aggregates(_report())["aggregate"]
    # overall from A (0.825) and B (0.6); E has overall None -> excluded.
    # aggregate means are rounded to 3 dp, so compare with abs tolerance.
    assert agg["overall"]["mean"] == pytest.approx((0.825 + 0.6) / 2, abs=1e-3)


def test_no_errored_metric_counted_as_zero():
    """The core guard: precision mean must be 0.9 (A only), NOT dragged toward 0
    by B's and E's errored precision. An errored metric is absent, not a zero."""
    agg = compute_aggregates(_report())["aggregate"]
    assert agg["contextual_precision"]["mean"] == pytest.approx(0.9)


def test_by_category_present():
    report = compute_aggregates(_report())
    assert "hypertrophy" in report["by_category"]
    assert report["by_category"]["hypertrophy"]["n"] == 1


def test_print_summary_does_not_crash():
    report = compute_aggregates(_report())
    print_summary(report)  # must handle errored metrics, gate fail, OOS, case error


def test_empty_report_no_scored():
    report = {
        "metadata": {
            "timestamp": "2026-07-24T00:00:00", "model": "m", "judge_model": "m",
            "duration_s": 1.0, "judge_mode": "binary", "total_cases": 0,
            "failed_cases": 0, "metrics_filter": None,
        },
        "results": [],
    }
    out = compute_aggregates(report)
    assert out["aggregate"] == {"note": "No scored results"}
    print_summary(out)


# --- Ragas-schema compatibility (report.py is shared with ragas_runner) ------
# Ragas emits ALL FIVE metrics as scored {"score": 0.x} — including
# answer_relevancy — and has no gate. compute_aggregates/print_summary must
# handle that schema too (report.py is loaded standalone by ragas_runner.py).


def _ragas_report():
    def rcase(cid, category, rel, rec, pre, ans, fai):
        overall = round((rel + rec + pre + ans + fai) / 5, 4)
        return {
            "id": cid, "question": "q", "category": category, "difficulty": "medium",
            "tags": [], "overall_score": overall, "error": None,
            "rag_result": {"grounded": True, "answer": "a"},
            "scores": {
                "contextual_relevancy": {"score": rel},
                "contextual_recall": {"score": rec},
                "contextual_precision": {"score": pre},
                "answer_relevancy": {"score": ans},  # SCORED, not a gate
                "faithfulness": {"score": fai},
            },
        }

    return {
        "metadata": {
            "timestamp": "2026-07-24T00:00:00", "model": "gemini-2.5-flash",
            "judge_model": "gemini-2.5-flash", "duration_s": 60.0,
            "judge_mode": "ragas", "total_cases": 2, "failed_cases": 0,
            "metrics_filter": None,
        },
        "results": [
            rcase("A", "hypertrophy", 0.8, 0.7, 0.9, 1.0, 0.85),
            rcase("B", "strength", 0.6, 0.5, 0.7, 0.9, 0.8),
        ],
    }


def test_ragas_answer_relevancy_shown_as_scored_metric():
    agg = compute_aggregates(_ragas_report())["aggregate"]
    # answer_relevancy is scored in the Ragas schema -> appears in the table...
    assert "answer_relevancy" in agg
    assert agg["answer_relevancy"]["mean"] == pytest.approx((1.0 + 0.9) / 2)
    # ...and there is NO gate block (nothing gate-shaped present).
    assert "answer_relevancy_gate" not in agg


def test_ragas_headline_and_overall_present():
    report = compute_aggregates(_ragas_report())
    agg = report["aggregate"]
    assert agg["headline"]["recall"] == pytest.approx((0.7 + 0.5) / 2)
    assert "overall" in agg
    # by_category surfaces answer_relevancy on a Ragas report
    assert "answer_relevancy" in report["by_category"]["hypertrophy"]


def test_ragas_no_false_errored_metrics():
    # Ragas metric dicts have no 'error' key -> nothing should be flagged errored.
    agg = compute_aggregates(_ragas_report())["aggregate"]
    assert "errored_metrics" not in agg


def test_ragas_print_summary_ok():
    print_summary(compute_aggregates(_ragas_report()))


def test_binary_report_has_no_answer_relevancy_in_table():
    """Complement to the Ragas test: on the BINARY report, answer_relevancy is a
    gate (no score) -> it must NOT appear in the scored table, only as the gate."""
    agg = compute_aggregates(_report())["aggregate"]
    assert "answer_relevancy" not in agg  # not in the scored table
    assert "answer_relevancy_gate" in agg  # present as a gate
