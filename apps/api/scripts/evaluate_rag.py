"""Automated RAG evaluation pipeline — CLI interface.

Usage:
    cd apps/api

    # Full run (binary judge, live RAG)
    python -m scripts.evaluate_rag

    # Score the frozen canonical fixture (no live RAG — the reproducible baseline)
    python -m scripts.evaluate_rag \
        --from-fixture results/rag_outputs_fixture_sgnorm015_full.json \
        --output results/run1_binary_baseline.json

    # Dry run (print expected call count, don't execute)
    python -m scripts.evaluate_rag --dry-run

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
        "--from-fixture",
        type=str,
        default=None,
        help="Judge frozen RAG outputs from a fixture JSON (results/rag_outputs_fixture.json) "
        "instead of running rag_query live. Used for apples-to-apples comparison with Ragas.",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save JSON report to file (e.g., results/eval_001.json)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Judge up to N cases concurrently (bounded by a semaphore; 429/5xx "
        "backoff handles rate limits). Default 1 = sequential. Use ~4 on paid tier.",
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


def load_fixture(path: str, ids: list[str] | None = None) -> list[dict]:
    """Load frozen RAG-output fixture cases, optionally filtering by IDs.

    Each fixture case carries the full test metadata (id, question, category,
    expected_facts, difficulty, tags) plus the frozen answer + chunks, so it
    doubles as both the dataset and the fixture map.
    """
    with open(path) as f:
        fixture = json.load(f)
    cases = fixture.get("cases", [])

    if ids:
        id_set = set(ids)
        cases = [c for c in cases if c["id"] in id_set]
        missing = id_set - {c["id"] for c in cases}
        if missing:
            print(f"Warning: IDs not found in fixture: {missing}")

    return cases


# Binary judge = 4 LLM calls per scored case: recall, relevancy+precision (shared),
# faithfulness, answer-relevancy gate.
JUDGE_CALLS_PER_CASE = 4


def print_dry_run(
    dataset: list[dict], judge_model: str | None, from_fixture: bool = False
) -> None:
    """Print expected call counts without executing."""
    n = len(dataset)
    oos_count = sum(1 for tc in dataset if "out-of-scope" in tc.get("tags", []))
    scored_count = n - oos_count
    # Fixture mode skips live rag_query, so no RAG calls — judge calls only.
    rag_calls = 0 if from_fixture else n

    gemini_calls = rag_calls + (scored_count * JUDGE_CALLS_PER_CASE)
    voyage_calls = 0 if from_fixture else n  # 1 embedding per live RAG query
    pct = (gemini_calls / 250) * 100
    est_time = n * 30 / 60

    print("\nDRY RUN — Binary RAG Evaluation")
    source = f"fixture ({n} cases)" if from_fixture else f"{DEFAULT_DATASET.name} ({n} cases)"
    print(f"  Source: {source}, {oos_count} out-of-scope")
    print(f"  Mode: binary{' (from fixture — no RAG calls)' if from_fixture else ''}")
    print(f"  Judge model: {judge_model or config.LLM_MODEL}")
    print(f"  Judge calls/scored case: {JUDGE_CALLS_PER_CASE} ({scored_count} scored cases)")
    print(f"  Expected Gemini calls: {gemini_calls} (of 250 RPD limit = {pct:.0f}%)")
    print(f"  Expected Voyage calls: {voyage_calls}")
    print(f"  Estimated duration: ~{est_time:.0f} min\n")


async def main() -> None:
    args = parse_args()

    # Load cases. Fixture mode uses the fixture's own cases (self-contained:
    # they carry test metadata + frozen RAG outputs) and builds a fixture map
    # so the judge scores frozen outputs instead of querying live.
    fixture_map: dict | None = None
    if args.from_fixture:
        dataset = load_fixture(args.from_fixture, args.ids)
        fixture_map = {c["id"]: c for c in dataset}
    else:
        dataset = load_dataset(args.dataset, args.ids)

    if not dataset:
        print("No test cases to evaluate.")
        return

    # Dry run
    if args.dry_run:
        print_dry_run(dataset, args.judge_model, from_fixture=bool(args.from_fixture))
        return

    # Run evaluation
    runner = EvalRunner(
        min_delay=7.0,
        verbose=args.verbose,
        inter_call_delay=5.0,
        judge_model=args.judge_model,
        metrics=args.metrics,
        fixture_map=fixture_map,
        concurrency=args.concurrency,
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
