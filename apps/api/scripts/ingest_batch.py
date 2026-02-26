"""Batch-ingest papers from manifest.json into the RAG corpus.

Usage:
    cd apps/api
    python -m scripts.ingest_batch

Reads papers/manifest.json for metadata and file paths.
Each entry needs: filename, title, authors, year, category, license.
Optional: journal, doi, url, study_type, abstract.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

from src.core.ingestion import ingest_paper
from src.schema.rag import PaperMetadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

PAPERS_DIR = Path(__file__).resolve().parent.parent / "papers"
MANIFEST_PATH = PAPERS_DIR / "manifest.json"


async def main() -> None:
    if not MANIFEST_PATH.exists():
        print(f"Error: manifest not found at {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    if not manifest:
        print("Manifest is empty, nothing to ingest.")
        return

    print(f"Found {len(manifest)} papers in manifest\n")

    results = {"ingested": 0, "skipped": 0, "failed": 0}

    for i, entry in enumerate(manifest, 1):
        filename = entry.get("filename")
        if not filename:
            print(f"[{i}/{len(manifest)}] SKIP — no filename")
            results["failed"] += 1
            continue

        pdf_path = PAPERS_DIR / filename
        if not pdf_path.exists():
            print(f"[{i}/{len(manifest)}] SKIP — file not found: {pdf_path}")
            results["failed"] += 1
            continue

        print(f"[{i}/{len(manifest)}] {entry.get('title', filename)}")

        try:
            metadata = PaperMetadata(
                title=entry["title"],
                authors=entry["authors"],
                year=entry["year"],
                category=entry["category"],
                license=entry.get("license", "unknown"),
                journal=entry.get("journal"),
                doi=entry.get("doi"),
                url=entry.get("url"),
                study_type=entry.get("study_type"),
                abstract=entry.get("abstract"),
            )

            result = await ingest_paper(str(pdf_path), metadata)

            # Check if it was a dedup skip (ingested_at would be older)
            # Simple heuristic: if total_chunks > 0 and we didn't create it just now
            print(f"  -> {result.total_chunks} chunks, ID: {result.id}")
            results["ingested"] += 1

        except Exception as e:
            print(f"  -> FAILED: {e}")
            results["failed"] += 1

    print(f"\n{'='*50}")
    print(f"Results: {results['ingested']} ingested, {results['skipped']} skipped, {results['failed']} failed")


if __name__ == "__main__":
    asyncio.run(main())
