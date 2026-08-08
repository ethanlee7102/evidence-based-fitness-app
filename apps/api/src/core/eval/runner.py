"""Eval runner — orchestrates RAG query + binary judge scoring for a test dataset.

Processes test cases sequentially with rate limiting to stay within
Gemini rate limits (free tier: 20 RPD; paid tier: 2000 RPD).

Uses the binary/decomposed judge (`binary_judge.py`): four LLM calls per scored
case (recall, relevancy+precision shared, faithfulness, answer-relevancy gate),
each a proportion in [0, 1] computed from binary atoms — or `None` when errored.
"""

import asyncio
import logging
import time
from dataclasses import dataclass

from src.core.eval.binary_judge import (
    SCORED_METRICS,
    BinaryJudgeResult,
    judge_all_binary,
)
from src.schema.rag import ChunkResponse, RAGResult
from src.utils.config import config

logger = logging.getLogger(__name__)


@dataclass
class EvalTestResult:
    """Result from evaluating a single test case."""

    id: str
    question: str
    category: str | None
    difficulty: str
    tags: list[str]
    scores: dict | None = None  # BinaryJudgeResult.to_dict()
    overall_score: float | None = None
    rag_result: dict | None = None
    error: str | None = None


async def _rag_query_with_retry(
    question: str,
    category: str | None = None,
    max_retries: int = 3,
) -> RAGResult:
    """Wrap rag_query with retry logic for 429/503 errors."""
    # Imported lazily so that importing the eval package (e.g. the offline judge
    # unit tests) doesn't pull in the full RAG pipeline -> retrieval -> supabase
    # chain, which isn't installed in the lean CI environment.
    from src.core.rag_pipeline import rag_query

    delays = [2.0, 5.0, 10.0]

    for attempt in range(max_retries):
        try:
            return await rag_query(query=question, category=category)
        except RuntimeError as e:
            err = str(e)
            if ("429" in err or "503" in err) and attempt < max_retries - 1:
                delay = delays[attempt]
                logger.warning(
                    f"RAG query retryable error (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                raise

    raise RuntimeError("Max retries exceeded for rag_query")


def _rag_result_from_fixture(entry: dict, query: str) -> RAGResult:
    """Rebuild a RAGResult from a frozen fixture entry (no live rag_query).

    Lets the custom judge score the exact same RAG outputs as the Ragas
    runner. `prompt_sent` / `embedding_time_ms` aren't persisted in the
    fixture and aren't needed for judging, so they're zeroed.
    """
    chunks = [ChunkResponse(**c) for c in entry.get("chunks", [])]
    return RAGResult(
        answer=entry.get("answer", ""),
        chunks=chunks,
        query=query,
        rewritten_query=entry.get("rewritten_query"),
        prompt_sent="",
        retrieval_time_ms=entry.get("retrieval_time_ms", 0.0),
        embedding_time_ms=0.0,
        rerank_time_ms=entry.get("rerank_time_ms", 0.0),
        generation_time_ms=entry.get("generation_time_ms", 0.0),
        model=entry.get("model", config.LLM_MODEL),
        grounded=entry.get("grounded", len(chunks) > 0),
    )


def _rag_result_to_dict(result: RAGResult) -> dict:
    """Extract serializable metadata from RAGResult."""
    return {
        "answer": result.answer,
        "grounded": result.grounded,
        "chunks_retrieved": len(result.chunks),
        "papers": list(
            {f"{c.authors}, {c.year}" for c in result.chunks}
        ),
        "retrieval_time_ms": round(result.retrieval_time_ms, 1),
        "generation_time_ms": round(result.generation_time_ms, 1),
        "model": result.model,
        "rewritten_query": result.rewritten_query,
    }


# Which scored metrics contribute to `overall` per --metrics filter. The gate
# (answer_relevancy) has no numeric score and never contributes.
_RETRIEVAL_METRICS = (
    "contextual_relevancy",
    "contextual_recall",
    "contextual_precision",
)
_GENERATION_METRICS = ("faithfulness",)


def _compute_overall(scores_dict: dict, metrics_filter: str | None) -> float | None:
    """Mean of the scored metric proportions selected by the filter.

    Excludes errored metrics (score=None) and the gate (no `score` key). Returns
    None when nothing in the selection scored (e.g. every metric errored).
    """
    if metrics_filter == "retrieval":
        keys: tuple[str, ...] = _RETRIEVAL_METRICS
    elif metrics_filter == "generation":
        keys = _GENERATION_METRICS
    else:
        keys = SCORED_METRICS
    vals = [
        scores_dict[k]["score"]
        for k in keys
        if k in scores_dict and scores_dict[k].get("score") is not None
    ]
    return round(sum(vals) / len(vals), 4) if vals else None


class EvalRunner:
    """Runs RAG evaluation against a test dataset."""

    def __init__(
        self,
        min_delay: float = 7.0,
        verbose: bool = False,
        inter_call_delay: float = 5.0,
        judge_model: str | None = None,
        metrics: str | None = None,
        fixture_map: dict | None = None,
        concurrency: int = 1,
    ):
        self.min_delay = min_delay
        self.verbose = verbose
        self.judge_model = judge_model
        self.metrics = metrics  # "retrieval", "generation", or None (all)
        # {case_id: fixture_entry} — when set, judge frozen RAG outputs
        # instead of calling rag_query live.
        self.fixture_map = fixture_map
        # Max cases judged concurrently. Bounded by a semaphore in run(); the
        # 429/5xx exponential-backoff retry in judge._generate_with_retry is the
        # rate-limit safety net. concurrency=1 preserves the old sequential path.
        self.concurrency = max(1, concurrency)
        # The per-call pacing was a free-tier RPM workaround; under bounded
        # concurrency it is redundant, so drop it when running concurrently.
        self.inter_call_delay = 0.0 if self.concurrency > 1 else inter_call_delay

    async def evaluate_single(self, test_case: dict) -> EvalTestResult:
        """Evaluate a single test case: RAG query + judge scoring."""
        case_id = test_case["id"]
        question = test_case["question"]
        category = test_case.get("category")
        expected_facts = test_case.get("expected_facts", [])
        difficulty = test_case.get("difficulty", "unknown")
        tags = test_case.get("tags", [])
        # A case is out-of-scope when tagged OR carrying zero expected_facts (same
        # definition as deterministic_checks.check_refusal). The 0-fact clause also
        # guards the binary recall judge, which cannot score supported/total over an
        # empty fact set — such a case is skipped here (grounded-flag check only).
        is_oos = "out-of-scope" in tags or not expected_facts

        if self.verbose:
            print(f"  [{case_id}] {question[:60]}...")

        try:
            # 1. Get RAG outputs — frozen fixture if provided, else live query
            fixture_entry = self.fixture_map.get(case_id) if self.fixture_map else None
            if fixture_entry is not None:
                rag_result = _rag_result_from_fixture(fixture_entry, query=question)
            else:
                rag_result = await _rag_query_with_retry(question, category)
            rag_dict = _rag_result_to_dict(rag_result)

            # For out-of-scope questions, just check grounded flag
            if is_oos:
                if self.verbose:
                    grounded = rag_result.grounded
                    print(f"         OOS → grounded={grounded}")
                return EvalTestResult(
                    id=case_id,
                    question=question,
                    category=category,
                    difficulty=difficulty,
                    tags=tags,
                    scores=None,
                    overall_score=None,
                    rag_result=rag_dict,
                    error=None,
                )

            # 2. Run binary judge scoring (4 calls: recall, relevancy+precision,
            #    faithfulness, answer-relevancy gate)
            judge_result: BinaryJudgeResult = await judge_all_binary(
                question=question,
                expected_facts=expected_facts,
                chunks=rag_result.chunks,
                answer=rag_result.answer,
                inter_call_delay=self.inter_call_delay,
                judge_model=self.judge_model,
            )

            scores_dict = judge_result.to_dict()
            overall = _compute_overall(scores_dict, self.metrics)

            if self.verbose:
                shown = f"{overall:.3f}" if overall is not None else "n/a (all errored)"
                print(f"         Overall: {shown}")

            return EvalTestResult(
                id=case_id,
                question=question,
                category=category,
                difficulty=difficulty,
                tags=tags,
                scores=scores_dict,
                overall_score=overall,
                rag_result=rag_dict,
                error=None,
            )

        except Exception as e:
            logger.error(f"[{case_id}] Error: {e}")
            if self.verbose:
                print(f"         ERROR: {e}")
            return EvalTestResult(
                id=case_id,
                question=question,
                category=category,
                difficulty=difficulty,
                tags=tags,
                error=str(e),
            )

    async def _run_sequential(self, dataset: list[dict]) -> list[EvalTestResult]:
        """One case at a time with an inter-case delay (free-tier-safe pacing)."""
        results: list[EvalTestResult] = []
        for i, test_case in enumerate(dataset):
            results.append(await self.evaluate_single(test_case))
            if i < len(dataset) - 1:
                await asyncio.sleep(self.min_delay)
        return results

    async def _run_concurrent(self, dataset: list[dict]) -> list[EvalTestResult]:
        """Judge up to `concurrency` cases at once, bounded by a semaphore.

        gather preserves input order, so results align with `dataset`. Rate
        limits are handled by the per-call 429/5xx backoff, not by pacing.
        """
        sem = asyncio.Semaphore(self.concurrency)

        async def _bounded(test_case: dict) -> EvalTestResult:
            async with sem:
                return await self.evaluate_single(test_case)

        return list(await asyncio.gather(*(_bounded(tc) for tc in dataset)))

    async def run(self, dataset: list[dict]) -> dict:
        """Run evaluation on the full dataset. Returns report dict."""
        start_time = time.time()
        mode = "binary"

        print(
            f"\nStarting RAG evaluation ({len(dataset)} cases, mode={mode}, "
            f"concurrency={self.concurrency})...\n"
        )

        if self.concurrency > 1:
            results = await self._run_concurrent(dataset)
        else:
            results = await self._run_sequential(dataset)

        duration_s = time.time() - start_time

        # Build report
        report = {
            "metadata": {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "model": config.LLM_MODEL,
                "judge_model": self.judge_model or config.LLM_MODEL,
                "top_k": config.RAG_TOP_K,
                "similarity_threshold": config.RAG_SIMILARITY_THRESHOLD,
                "duration_s": round(duration_s, 1),
                "judge_mode": mode,
                "total_cases": len(dataset),
                "failed_cases": sum(1 for r in results if r.error),
                "metrics_filter": self.metrics,
                "concurrency": self.concurrency,
                "from_fixture": self.fixture_map is not None,
            },
            "results": [
                {
                    "id": r.id,
                    "question": r.question,
                    "category": r.category,
                    "difficulty": r.difficulty,
                    "tags": r.tags,
                    "scores": r.scores,
                    "overall_score": r.overall_score,
                    "rag_result": r.rag_result,
                    "error": r.error,
                }
                for r in results
            ],
        }

        return report
