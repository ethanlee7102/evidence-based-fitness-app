"""Pytest configuration for RAG evaluation tests."""

import json
from pathlib import Path

import pytest


def pytest_configure(config):
    """Register the 'eval' marker."""
    config.addinivalue_line(
        "markers",
        "eval: marks tests as RAG evaluation tests (may be slow, uses API calls)",
    )


@pytest.fixture(scope="session")
def test_dataset():
    """Load the test dataset from JSON."""
    dataset_path = Path(__file__).parent / "test_dataset.json"
    with open(dataset_path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def eval_results(test_dataset):
    """Run the evaluation and cache results for the session.

    This is expensive (API calls), so it runs once per pytest session.
    """
    import asyncio

    from src.core.eval.report import compute_aggregates
    from src.core.eval.runner import EvalRunner

    runner = EvalRunner(
        min_delay=7.0,
        verbose=True,
        combined=True,  # Use combined mode for faster test runs
        inter_call_delay=5.0,
    )

    report = asyncio.run(runner.run(test_dataset))
    report = compute_aggregates(report)
    return report
