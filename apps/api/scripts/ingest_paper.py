"""Ingest a single PDF paper into the RAG corpus.

Usage:
    cd apps/api
    python -m scripts.ingest_paper \
        --pdf papers/schoenfeld2017.pdf \
        --title "Dose-Response Relationship Between Weekly Resistance Training Volume and Increases in Muscle Mass" \
        --authors "Schoenfeld et al." \
        --year 2017 \
        --category hypertrophy \
        --license CC-BY \
        --journal "Journal of Sports Sciences" \
        --doi "10.1080/02640414.2016.1210197" \
        --study-type meta-analysis
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from src.core.ingestion import ingest_paper
from src.schema.rag import PaperMetadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest a PDF paper into the RAG corpus")

    # Required
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--title", required=True, help="Paper title")
    parser.add_argument("--authors", required=True, help='Authors (e.g. "Schoenfeld et al.")')
    parser.add_argument("--year", required=True, type=int, help="Publication year")
    parser.add_argument(
        "--category", required=True,
        choices=[
            "hypertrophy", "strength", "nutrition", "endurance",
            "recovery", "mobility", "programming", "general",
        ],
        help="Paper category",
    )
    parser.add_argument(
        "--license", required=True, dest="paper_license",
        choices=[
            "CC0", "CC-BY", "CC-BY-SA", "CC-BY-ND",
            "CC-BY-NC", "CC-BY-NC-SA", "CC-BY-NC-ND",
            "other", "unknown",
        ],
        help="Creative Commons license",
    )

    # Optional
    parser.add_argument("--journal", help="Journal name")
    parser.add_argument("--doi", help="DOI identifier")
    parser.add_argument("--url", help="URL to paper")
    parser.add_argument(
        "--study-type", dest="study_type",
        choices=[
            "meta-analysis", "systematic-review", "rct", "review",
            "observational", "case-study", "other",
        ],
        help="Study type",
    )
    parser.add_argument("--abstract", help="Paper abstract")

    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    # Validate PDF exists
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    metadata = PaperMetadata(
        title=args.title,
        authors=args.authors,
        year=args.year,
        category=args.category,
        license=args.paper_license,
        journal=args.journal,
        doi=args.doi,
        url=args.url,
        study_type=args.study_type,
        abstract=args.abstract,
    )

    print(f"\nIngesting: {metadata.title}")
    print(f"  PDF: {pdf_path}")
    print(f"  Category: {metadata.category}")
    print(f"  License: {metadata.license}")
    print()

    result = await ingest_paper(str(pdf_path), metadata)

    print("\nDone!")
    print(f"  Paper ID: {result.id}")
    print(f"  Chunks: {result.total_chunks}")
    print(f"  Embedding model: {result.embedding_model}")


if __name__ == "__main__":
    asyncio.run(main())
