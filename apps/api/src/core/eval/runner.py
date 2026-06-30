"""Eval runner — orchestrates RAG query + judge scoring for a test dataset.

Processes test cases sequentially with rate limiting to stay within
Gemini rate limits (free tier: 20 RPD; paid tier: 2000 RPD).
"""

import asyncio
import logging
import time
from dataclasses import dataclass

from src.core.eval.judge import JudgeResult, judge_all
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
    scores: dict | None = None  # JudgeResult.to_dict()
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


class EvalRunner:
    """Runs RAG evaluation against a test dataset."""

    def __init__(
        self,
        min_delay: float = 7.0,
        verbose: bool = False,
        combined: bool = False,
        inter_call_delay: float = 5.0,
        judge_model: str | None = None,
        metrics: str | None = None,
        fixture_map: dict | None = None,
    ):
        self.min_delay = min_delay
        self.verbose = verbose
        self.combined = combined
        self.inter_call_delay = inter_call_delay
        self.judge_model = judge_model
        self.metrics = metrics  # "retrieval", "generation", or None (all)
        # {case_id: fixture_entry} — when set, judge frozen RAG outputs
        # instead of calling rag_query live.
        self.fixture_map = fixture_map

    async def evaluate_single(self, test_case: dict) -> EvalTestResult:
        """Evaluate a single test case: RAG query + judge scoring."""
        case_id = test_case["id"]
        question = test_case["question"]
        category = test_case.get("category")
        expected_facts = test_case.get("expected_facts", [])
        difficulty = test_case.get("difficulty", "unknown")
        tags = test_case.get("tags", [])
        is_oos = "out-of-scope" in tags

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

            # 2. Run judge scoring
            judge_result: JudgeResult = await judge_all(
                question=question,
                expected_facts=expected_facts,
                chunks=rag_result.chunks,
                answer=rag_result.answer,
                combined=self.combined,
                inter_call_delay=self.inter_call_delay,
                judge_model=self.judge_model,
            )

            scores_dict = judge_result.to_dict()

            # Apply metric filter if set
            if self.metrics == "retrieval":
                # Only contextual_* metrics
                filtered = {
                    k: v
                    for k, v in scores_dict.items()
                    if k.startswith("contextual_")
                }
                overall = (
                    sum(v["score"] for v in filtered.values()) / len(filtered)
                    if filtered
                    else 0.0
                )
            elif self.metrics == "generation":
                # Only answer_relevancy + faithfulness
                filtered = {
                    k: v
                    for k, v in scores_dict.items()
                    if k in ("answer_relevancy", "faithfulness")
                }
                overall = (
                    sum(v["score"] for v in filtered.values()) / len(filtered)
                    if filtered
                    else 0.0
                )
            else:
                filtered = scores_dict
                overall = (
                    sum(v["score"] for v in filtered.values()) / len(filtered)
                    if filtered
                    else 0.0
                )

            if self.verbose:
                print(f"         Overall: {overall:.2f}")

            return EvalTestResult(
                id=case_id,
                question=question,
                category=category,
                difficulty=difficulty,
                tags=tags,
                scores=scores_dict,
                overall_score=round(overall, 2),
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

    async def run(self, dataset: list[dict]) -> dict:
        """Run evaluation on the full dataset. Returns report dict."""
        start_time = time.time()
        results: list[EvalTestResult] = []
        mode = "combined" if self.combined else "separate"

        print(f"\nStarting RAG evaluation ({len(dataset)} cases, mode={mode})...\n")

        for i, test_case in enumerate(dataset):
            result = await self.evaluate_single(test_case)
            results.append(result)

            # Rate limit between test cases (skip after last)
            if i < len(dataset) - 1:
                await asyncio.sleep(self.min_delay)

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
