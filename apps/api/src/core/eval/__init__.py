"""RAG evaluation pipeline — binary/decomposed LLM-as-judge scoring."""

from src.core.eval.binary_judge import (
    GATE_METRIC,
    HEADLINE_METRIC,
    SCORED_METRICS,
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
)
from src.core.eval.judge import JudgeParseError
from src.core.eval.report import compute_aggregates, print_summary, save_json_report
from src.core.eval.runner import EvalRunner, EvalTestResult

__all__ = [
    "SCORED_METRICS",
    "GATE_METRIC",
    "HEADLINE_METRIC",
    "AtomVerdict",
    "MetricScore",
    "GateResult",
    "BinaryJudgeResult",
    "average_precision",
    "judge_recall",
    "judge_relevancy_precision",
    "judge_faithfulness",
    "judge_gate",
    "judge_all_binary",
    "JudgeParseError",
    "EvalRunner",
    "EvalTestResult",
    "compute_aggregates",
    "print_summary",
    "save_json_report",
]
