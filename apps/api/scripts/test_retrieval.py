"""Test the retrieval pipeline by querying the vector DB.

Usage:
    cd apps/api
    python -m scripts.test_retrieval "How does creatine affect muscle growth?"
    python -m scripts.test_retrieval "protein timing" --top-k 3 --category nutrition
"""

import argparse
import asyncio
import logging

from src.core.retrieval import retrieve_chunks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test RAG retrieval pipeline")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve (default: 5)")
    parser.add_argument(
        "--category",
        choices=[
            "hypertrophy", "strength", "nutrition", "endurance",
            "recovery", "mobility", "programming", "general",
        ],
        help="Filter by category",
    )
    parser.add_argument("--threshold", type=float, help="Minimum similarity threshold")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    print(f"\nQuery: \"{args.query}\"")
    print(f"Top-k: {args.top_k}")
    if args.category:
        print(f"Category: {args.category}")
    if args.threshold:
        print(f"Threshold: {args.threshold}")
    print()

    result = await retrieve_chunks(
        query=args.query,
        top_k=args.top_k,
        category=args.category,
        similarity_threshold=args.threshold,
    )

    print(f"Retrieved {len(result.chunks)} chunks in {result.retrieval_time_ms:.0f}ms\n")

    if not result.chunks:
        print("No matching chunks found.")
        return

    print("-" * 80)
    for i, chunk in enumerate(result.chunks, 1):
        print(f"\n[{i}] {chunk.authors}, {chunk.year} — {chunk.title}")
        print(f"    Section: {chunk.section or 'N/A'} | Chunk {chunk.chunk_index} | Similarity: {chunk.similarity:.4f}")
        if chunk.token_count:
            print(f"    Tokens: {chunk.token_count}")
        print(f"    Category: {chunk.category} | Study type: {chunk.study_type or 'N/A'}")
        # Show first 300 chars of chunk text
        preview = chunk.chunk_text[:300]
        if len(chunk.chunk_text) > 300:
            preview += "..."
        print(f"\n    {preview}")
        print()
        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(main())
