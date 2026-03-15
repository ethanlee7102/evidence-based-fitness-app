"""RAG evaluation pipeline — custom LLM-as-judge scoring."""

from src.core.eval.judge import (
    JudgeResult,
    MetricScore,
    judge_all,
    judge_answer_relevancy,
    judge_combined,
    judge_contextual_precision,
    judge_contextual_recall,
    judge_contextual_relevancy,
    judge_faithfulness,
)
from src.core.eval.report import compute_aggregates, print_summary, save_json_report
from src.core.eval.runner import EvalRunner, EvalTestResult

__all__ = [
    "MetricScore",
    "JudgeResult",
    "judge_contextual_relevancy",
    "judge_contextual_recall",
    "judge_contextual_precision",
    "judge_answer_relevancy",
    "judge_faithfulness",
    "judge_combined",
    "judge_all",
    "EvalRunner",
    "EvalTestResult",
    "compute_aggregates",
    "print_summary",
    "save_json_report",
]
