"""Automated RAG evaluation pipeline — CLI interface.

Usage:
    cd apps/api

    # Full run (separate judges, default)
    python -m scripts.evaluate_rag

    # Combined judge mode (faster, 1 call per test case)
    python -m scripts.evaluate_rag --combined

    # Dry run (print expected call count, don't execute)
    python -m scripts.evaluate_rag --dry-run
    python -m scripts.evaluate_rag --combined --dry-run

    # Specific test cases
    python -m scripts.evaluate_rag --ids HYP-001 NUT-001

    # Only retrieval metrics (skip answer_relevancy + faithfulness)
    python -m scripts.evaluate_rag --metrics retrieval

    # Only generation metrics (skip contextual_*)
    python -m scripts.evaluate_rag --metrics generation

    # Custom judge model (cross-validation)
    python -m scripts.evaluate_rag --judge-model gpt-4o

    # Custom dataset
    python -m scripts.evaluate_rag --dataset path/to/custom.json

    # Save JSON report
    python -m scripts.evaluate_rag --output results/eval_001.json

    # Verbose (print each question as it runs)
    python -m scripts.evaluate_rag --verbose
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path

from src.core.eval.report import compute_aggregates, print_summary, save_json_report
from src.core.eval.runner import EvalRunner
from src.utils.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

DEFAULT_DATASET = Path(__file__).resolve().parent.parent / "tests" / "eval" / "test_dataset.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RAG evaluation pipeline")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(DEFAULT_DATASET),
        help="Path to test dataset JSON (default: tests/eval/test_dataset.json)",
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        help="Run only specific test case IDs (e.g., --ids HYP-001 NUT-001)",
    )
    parser.add_argument(
        "--combined",
        action="store_true",
        help="Use combined judge mode (1 call per test case, faster)",
    )
    parser.add_argument(
        "--metrics",
        choices=["retrieval", "generation"],
        help="Only run specific metric group (retrieval=contextual_*, generation=answer+faithfulness)",
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        default=None,
        help="Override judge model (default: same as RAG model)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save JSON report to file (e.g., results/eval_001.json)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress for each test case",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print expected call counts without running",
    )
    return parser.parse_args()


def load_dataset(path: str, ids: list[str] | None = None) -> list[dict]:
    """Load test dataset from JSON file, optionally filtering by IDs."""
    with open(path) as f:
        dataset = json.load(f)

    if ids:
        id_set = set(ids)
        dataset = [tc for tc in dataset if tc["id"] in id_set]
        found = {tc["id"] for tc in dataset}
        missing = id_set - found
        if missing:
            print(f"Warning: IDs not found in dataset: {missing}")

    return dataset


def print_dry_run(dataset: list[dict], combined: bool, judge_model: str | None) -> None:
    """Print expected call counts without executing."""
    n = len(dataset)
    oos_count = sum(1 for tc in dataset if "out-of-scope" in tc.get("tags", []))
    scored_count = n - oos_count

    if combined:
        # OOS: 1 RAG call each, scored: 1 RAG + 1 judge each
        gemini_calls = n + scored_count  # RAG calls + judge calls
        mode = "combined"
    else:
        # OOS: 1 RAG call each, scored: 1 RAG + 5 judge calls each
        gemini_calls = n + (scored_count * 5)
        mode = "separate"

    voyage_calls = n  # 1 embedding per test case
    pct = (gemini_calls / 250) * 100
    est_time = (n * 37 / 60) if not combined else (n * 12 / 60)

    print(f"\nDRY RUN — Phase 8 RAG Evaluation")
    print(f"  Dataset: {DEFAULT_DATASET.name} ({n} cases, {oos_count} out-of-scope)")
    print(f"  Mode: {mode}")
    print(f"  Judge model: {judge_model or config.LLM_MODEL}")
    print(f"  Expected Gemini calls: {gemini_calls} (of 250 RPD limit = {pct:.0f}%)")
    print(f"  Expected Voyage calls: {voyage_calls}")
    print(f"  Estimated duration: ~{est_time:.0f} min\n")


async def main() -> None:
    args = parse_args()

    # Load dataset
    dataset = load_dataset(args.dataset, args.ids)
    if not dataset:
        print("No test cases to evaluate.")
        return

    # Dry run
    if args.dry_run:
        print_dry_run(dataset, args.combined, args.judge_model)
        return

    # Run evaluation
    runner = EvalRunner(
        min_delay=7.0,
        verbose=args.verbose,
        combined=args.combined,
        inter_call_delay=5.0,
        judge_model=args.judge_model,
        metrics=args.metrics,
    )

    report = await runner.run(dataset)
    report = compute_aggregates(report)

    # Save JSON report first — don't lose results if printing crashes
    if args.output:
        save_json_report(report, args.output)

    # Print console summary
    print_summary(report)


if __name__ == "__main__":
    asyncio.run(main())
