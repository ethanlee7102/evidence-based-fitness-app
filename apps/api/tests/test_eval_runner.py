"""Offline tests for EvalRunner orchestration (concurrency plumbing).

No API: evaluate_single is monkeypatched. Verifies the concurrent path bounds
in-flight work to `concurrency`, preserves dataset order, and processes every
case. Not eval-marked -> runs in the `pytest -m "not eval"` CI gate.
"""

import asyncio

from src.core.eval.runner import EvalRunner, EvalTestResult


def _fake_dataset(n):
    return [{"id": f"C{i}", "question": "q", "category": None, "tags": []}
            for i in range(n)]


def test_run_concurrent_preserves_order_and_count(monkeypatch):
    max_in_flight = {"cur": 0, "peak": 0}

    async def fake_eval(self, tc):
        max_in_flight["cur"] += 1
        max_in_flight["peak"] = max(max_in_flight["peak"], max_in_flight["cur"])
        await asyncio.sleep(0.01)  # force real overlap
        max_in_flight["cur"] -= 1
        return EvalTestResult(id=tc["id"], question="q", category=None,
                              difficulty="", tags=[])

    monkeypatch.setattr(EvalRunner, "evaluate_single", fake_eval)
    runner = EvalRunner(concurrency=3)
    report = asyncio.run(runner.run(_fake_dataset(10)))

    # order preserved despite concurrent completion
    assert [r["id"] for r in report["results"]] == [f"C{i}" for i in range(10)]
    # semaphore actually bounded concurrency
    assert max_in_flight["peak"] <= 3
    assert max_in_flight["peak"] > 1  # and did run concurrently
    assert report["metadata"]["concurrency"] == 3


def test_concurrency_disables_inter_call_delay():
    # Under concurrency the redundant per-call pacing is dropped.
    assert EvalRunner(concurrency=4, inter_call_delay=5.0).inter_call_delay == 0.0
    # Sequential keeps it.
    assert EvalRunner(concurrency=1, inter_call_delay=5.0).inter_call_delay == 5.0


def test_run_sequential_still_works(monkeypatch):
    async def fake_eval(self, tc):
        return EvalTestResult(id=tc["id"], question="q", category=None,
                              difficulty="", tags=[])

    monkeypatch.setattr(EvalRunner, "evaluate_single", fake_eval)
    # min_delay=0 so the sequential path doesn't actually sleep in the test.
    runner = EvalRunner(concurrency=1, min_delay=0.0)
    report = asyncio.run(runner.run(_fake_dataset(4)))
    assert [r["id"] for r in report["results"]] == ["C0", "C1", "C2", "C3"]
    assert report["metadata"]["concurrency"] == 1
