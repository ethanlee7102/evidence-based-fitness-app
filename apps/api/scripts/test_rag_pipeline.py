"""Test the full RAG pipeline end-to-end.

Usage:
    cd apps/api

    # Basic query
    python -m scripts.test_rag_pipeline "How does creatine affect muscle growth?"

    # With category filter
    python -m scripts.test_rag_pipeline "best rep range for hypertrophy" --category hypertrophy

    # Streaming mode
    python -m scripts.test_rag_pipeline "How does creatine affect muscle growth?" --stream

    # Follow-up with history (JSON array of {role, content} objects)
    python -m scripts.test_rag_pipeline "Tell me more about the dosing" --history '[
        {"role": "user", "content": "How does creatine affect muscle growth?"},
        {"role": "assistant", "content": "Creatine increases lean mass by..."}
    ]'

    # Show the full prompt sent to the LLM
    python -m scripts.test_rag_pipeline "How does creatine work?" --show-prompt
"""

import argparse
import asyncio
import json
import logging

from src.core.rag_pipeline import rag_query, rag_query_stream

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test RAG generation pipeline")
    parser.add_argument("query", help="Question to ask")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve (default: 5)")
    parser.add_argument(
        "--category",
        choices=[
            "hypertrophy", "strength", "nutrition", "endurance",
            "recovery", "mobility", "programming", "general",
        ],
        help="Filter by category",
    )
    parser.add_argument(
        "--history",
        type=str,
        help='Conversation history as JSON array: [{"role":"user","content":"..."},...]',
    )
    parser.add_argument("--stream", action="store_true", help="Use streaming mode")
    parser.add_argument("--show-prompt", action="store_true", help="Print the full prompt sent to the LLM")
    return parser.parse_args()


def _print_metadata(
    query: str,
    rewritten_query: str | None,
    chunks: list,
    grounded: bool,
    model: str,
    retrieval_time_ms: float,
    generation_time_ms: float | None = None,
) -> None:
    """Print metadata header."""
    print(f"\n{'='*80}")
    print(f"Query:           \"{query}\"")
    if rewritten_query:
        print(f"Rewritten:       \"{rewritten_query}\"")
    print(f"Model:           {model}")
    print(f"Grounded:        {grounded}")
    print(f"Chunks:          {len(chunks)}")
    print(f"Retrieval:       {retrieval_time_ms:.0f}ms")
    if generation_time_ms is not None:
        print(f"Generation:      {generation_time_ms:.0f}ms")
        print(f"Total:           {retrieval_time_ms + generation_time_ms:.0f}ms")
    print(f"{'='*80}")


def _print_sources(chunks: list) -> None:
    """Print retrieved sources summary."""
    if not chunks:
        print("\nNo sources retrieved.")
        return

    print("\nSources:")
    print("-" * 60)
    for i, chunk in enumerate(chunks, 1):
        section = chunk.section or "N/A"
        print(f"  [{i}] {chunk.authors}, {chunk.year} — {chunk.title}")
        print(f"      Section: {section} | Similarity: {chunk.similarity:.4f}")
    print("-" * 60)


async def run_non_streaming(args: argparse.Namespace, history: list | None) -> None:
    """Run the non-streaming pipeline and print results."""
    result = await rag_query(
        query=args.query,
        history=history,
        top_k=args.top_k,
        category=args.category,
    )

    _print_metadata(
        query=result.query,
        rewritten_query=result.rewritten_query,
        chunks=result.chunks,
        grounded=result.grounded,
        model=result.model,
        retrieval_time_ms=result.retrieval_time_ms,
        generation_time_ms=result.generation_time_ms,
    )
    _print_sources(result.chunks)

    if args.show_prompt:
        print(f"\n{'='*40} PROMPT {'='*40}")
        print(result.prompt_sent)
        print(f"{'='*87}")

    print(f"\n{'='*40} ANSWER {'='*40}")
    print(result.answer)
    print(f"{'='*87}\n")


async def run_streaming(args: argparse.Namespace, history: list | None) -> None:
    """Run the streaming pipeline and print tokens as they arrive."""
    result = await rag_query_stream(
        query=args.query,
        history=history,
        top_k=args.top_k,
        category=args.category,
    )

    _print_metadata(
        query=result.query,
        rewritten_query=result.rewritten_query,
        chunks=result.chunks,
        grounded=result.grounded,
        model=result.model,
        retrieval_time_ms=result.retrieval_time_ms,
    )
    _print_sources(result.chunks)

    if args.show_prompt:
        print(f"\n{'='*40} PROMPT {'='*40}")
        print(result.prompt_sent)
        print(f"{'='*87}")

    print(f"\n{'='*40} ANSWER (streaming) {'='*27}")
    async for token in result.stream:
        print(token, end="", flush=True)
    print(f"\n{'='*87}\n")


async def main() -> None:
    args = parse_args()

    # Parse history if provided
    history = None
    if args.history:
        try:
            history = json.loads(args.history)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --history: {e}")
            return

    if args.stream:
        await run_streaming(args, history)
    else:
        await run_non_streaming(args, history)


if __name__ == "__main__":
    asyncio.run(main())
