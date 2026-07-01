"""Capture a frozen RAG-output fixture for cross-implementation eval.

Runs the RAG pipeline ONCE over the test dataset and persists the full
answer + retrieved chunk objects per case. Both the custom judge
(`evaluate_rag --from-fixture`) and the Ragas runner
(`evaluate_rag_ragas`) score this SAME artifact, so any score gap between
them is purely the evaluation implementation — not a re-generation
(temperature 0.3) confound.

It also closes a logging gap: the custom eval runner only ever persisted
chunk *counts* + citations, never the chunk texts. Ragas needs the texts as
`retrieved_contexts`, so they have to be captured here.

Runs in the MAIN venv (imports the app's RAG pipeline).

Usage:
    cd apps/api
    # Full capture (100 cases)
    python -m scripts.capture_rag_fixture

    # Subset for smoke-testing
    python -m scripts.capture_rag_fixture --ids HYP-001 NUT-003 --output results/_fixture_smoke.json
"""

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path

from scripts.evaluate_rag import load_dataset
from src.core.eval.runner import _rag_query_with_retry
from src.core.retrieval import retrieve_reranked
from src.utils.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_DATASET = Path(__file__).resolve().parent.parent / "tests" / "eval" / "test_dataset.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "results" / "rag_outputs_fixture.json"

# Match the custom runner's inter-case rate limit (Gemini-friendly).
INTER_CASE_DELAY = 7.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a frozen RAG-output fixture")
    parser.add_argument("--dataset", type=str, default=str(DEFAULT_DATASET))
    parser.add_argument("--ids", nargs="+", help="Capture only specific test case IDs")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Skip LLM generation — capture reranked chunks only (for chunk-level "
        "retrieval-metric judging; empty answer). Much faster/cheaper.",
    )
    parser.add_argument(
        "--per-paper-cap",
        type=int,
        default=None,
        help="Override the per-paper cap for --retrieval-only (e.g. 999 = no cap). "
        "Used for the cap ablation.",
    )
    parser.add_argument(
        "--cap-margin",
        type=float,
        default=None,
        help="Score-gated cap margin for --retrieval-only (>0 enables the score gate; "
        "0 = hard cap). Used for the cap ablation.",
    )
    parser.add_argument(
        "--cap-normalize",
        action="store_true",
        help="Interpret --cap-margin as a fraction of the query's score range (relative).",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Override the number of chunks returned for --retrieval-only (e.g. 20 to "
        "freeze a reranked POOL that cap variants can be applied to offline, noise-free).",
    )
    parser.add_argument(
        "--inter-case-delay",
        type=float,
        default=INTER_CASE_DELAY,
        help=f"Seconds to pause between generation cases (default {INTER_CASE_DELAY}). "
        "Lower it on a generous rate tier to speed up the capture.",
    )
    return parser.parse_args()


async def capture_case(
    test_case: dict,
    retrieval_only: bool = False,
    per_paper_cap: int | None = None,
    cap_margin: float | None = None,
    cap_normalize: bool = False,
    top_n: int | None = None,
) -> dict:
    """Run the RAG pipeline for one case and build a fixture entry.

    retrieval_only: skip generation, capture only the reranked chunks (answer left
    empty). The 3 retrieval metrics are judged on chunks alone, so this supports a
    cheap chunk-level ablation (e.g. cap on vs off) without paying for generation.
    """
    question = test_case["question"]
    category = test_case.get("category")

    if retrieval_only:
        retr = await retrieve_reranked(
            question,
            top_n=top_n,
            category=category,
            per_paper_cap=per_paper_cap,
            cap_margin=cap_margin,
            cap_normalize=cap_normalize,
        )
        return {
            "id": test_case["id"],
            "question": question,
            "category": category,
            "expected_facts": test_case.get("expected_facts", []),
            "difficulty": test_case.get("difficulty", "unknown"),
            "tags": test_case.get("tags", []),
            "answer": "",  # no generation — generation metrics must be skipped (--metrics retrieval)
            "grounded": len(retr.chunks) > 0,
            "rewritten_query": None,
            "model": config.LLM_MODEL,
            "retrieval_time_ms": round(retr.retrieval_time_ms, 1),
            "rerank_time_ms": round(retr.rerank_time_ms, 1),
            "generation_time_ms": 0.0,
            "chunks": [c.model_dump(mode="json") for c in retr.chunks],
        }

    rag_result = await _rag_query_with_retry(question, category)

    return {
        # Pass-through test metadata (so consumers need only the fixture)
        "id": test_case["id"],
        "question": question,
        "category": category,
        "expected_facts": test_case.get("expected_facts", []),
        "difficulty": test_case.get("difficulty", "unknown"),
        "tags": test_case.get("tags", []),
        # Frozen RAG outputs
        "answer": rag_result.answer,
        "grounded": rag_result.grounded,
        "rewritten_query": rag_result.rewritten_query,
        "model": rag_result.model,
        "retrieval_time_ms": round(rag_result.retrieval_time_ms, 1),
        "generation_time_ms": round(rag_result.generation_time_ms, 1),
        # Full chunk objects — custom judge rebuilds ChunkResponse(**c);
        # Ragas reads c["chunk_text"] as retrieved_contexts.
        "chunks": [c.model_dump(mode="json") for c in rag_result.chunks],
    }


async def main() -> None:
    args = parse_args()
    dataset = load_dataset(args.dataset, args.ids)
    if not dataset:
        print("No test cases to capture.")
        return

    print(f"\nCapturing RAG fixture for {len(dataset)} cases (model={config.LLM_MODEL})...\n")
    start = time.time()
    entries: list[dict] = []
    failures: list[str] = []

    for i, test_case in enumerate(dataset):
        case_id = test_case["id"]
        try:
            entry = await capture_case(
                test_case,
                args.retrieval_only,
                args.per_paper_cap,
                args.cap_margin,
                args.cap_normalize,
                args.top_n,
            )
            entries.append(entry)
            print(
                f"  [{case_id}] {len(entry['chunks'])} chunks, "
                f"grounded={entry['grounded']}, answer={len(entry['answer'])} chars"
            )
        except Exception as e:  # noqa: BLE001 — capture is best-effort per case
            logger.error(f"[{case_id}] capture failed: {e}")
            failures.append(case_id)

        # Generation needs the Gemini rate-limit pause; retrieval-only doesn't.
        if not args.retrieval_only and i < len(dataset) - 1:
            await asyncio.sleep(args.inter_case_delay)

    fixture = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model": config.LLM_MODEL,
            "top_k": config.RAG_TOP_K,
            "similarity_threshold": config.RAG_SIMILARITY_THRESHOLD,
            "retrieval_only": args.retrieval_only,
            "per_paper_cap": args.per_paper_cap if args.retrieval_only else None,
            "cap_margin": args.cap_margin if args.retrieval_only else None,
            "cap_normalize": args.cap_normalize if args.retrieval_only else None,
            "duration_s": round(time.time() - start, 1),
            "total_cases": len(dataset),
            "captured_cases": len(entries),
            "failed_cases": len(failures),
            "failed_ids": failures,
        },
        "cases": entries,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(fixture, f, indent=2, default=str)

    print(f"\nCaptured {len(entries)}/{len(dataset)} cases → {out_path}")
    if failures:
        print(f"FAILED: {failures}")


if __name__ == "__main__":
    asyncio.run(main())
