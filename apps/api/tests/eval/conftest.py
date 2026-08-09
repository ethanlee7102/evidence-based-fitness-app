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
def eval_results():
    """Run the binary judge over the frozen canonical fixture and cache results.

    Scores the SAME frozen RAG outputs as the shipped baseline (RAG side
    deterministic via `fixture_map`; the judge runs live), so the threshold
    assertions are reproducible rather than gated on live retrieval variance.
    Expensive (live judge API calls) — runs once per session, eval-marked only.
    """
    import asyncio
    import json

    from src.core.eval.fixtures import current_fixture_path
    from src.core.eval.report import compute_aggregates
    from src.core.eval.runner import EvalRunner

    with open(current_fixture_path()) as f:
        cases = json.load(f)["cases"]

    runner = EvalRunner(
        min_delay=7.0,
        verbose=True,
        inter_call_delay=5.0,
        fixture_map={c["id"]: c for c in cases},
    )

    report = asyncio.run(runner.run(cases))
    report = compute_aggregates(report)
    return report
