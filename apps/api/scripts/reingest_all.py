"""Delete all existing papers/chunks and re-ingest from papers/ directory.

Usage:
    cd apps/api
    python -m scripts.reingest_all
"""

import asyncio
import logging

from src.core.ingestion import ingest_paper
from src.db import get_supabase
from src.schema.rag import PaperMetadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Metadata for all 9 papers (matches original ingestion)
PAPERS = [
    {
        "filename": "nutrients-13-01915.pdf",
        "title": "Creatine for Exercise and Sports Performance, with Recovery Considerations for Healthy Populations",
        "authors": "Wax et al.",
        "year": 2021,
        "category": "nutrition",
        "license": "CC-BY",
        "journal": "Nutrients",
        "study_type": "review",
    },
    {
        "filename": "nutrients-17-02748.pdf",
        "title": "The Effects of Creatine Supplementation on Upper- and Lower-Body Strength and Power in Healthy Adults: A Systematic Review with Meta-Analysis",
        "authors": "Kazeminasab et al.",
        "year": 2025,
        "category": "nutrition",
        "license": "CC-BY",
        "journal": "Nutrients",
        "study_type": "meta-analysis",
    },
    {
        "filename": "ijerph-16-04897.pdf",
        "title": "Maximizing Muscle Hypertrophy: A Systematic Review of Advanced Resistance Training Techniques and Methods",
        "authors": "Krzysztofik et al.",
        "year": 2019,
        "category": "hypertrophy",
        "license": "CC-BY",
        "journal": "International Journal of Environmental Research and Public Health",
        "study_type": "systematic-review",
    },
    {
        "filename": "fspor-04-949021.pdf",
        "title": "Resistance Training Variables for Optimization of Muscle Hypertrophy: An Umbrella Review",
        "authors": "Bernardez-Vazquez et al.",
        "year": 2022,
        "category": "hypertrophy",
        "license": "CC-BY",
        "journal": "Frontiers in Sports and Active Living",
        "study_type": "systematic-review",
    },
    {
        "filename": "sports-09-00032.pdf",
        "title": "Loading Recommendations for Muscle Strength, Hypertrophy, and Local Endurance: A Re-Examination of the Repetition Continuum",
        "authors": "Schoenfeld et al.",
        "year": 2021,
        "category": "hypertrophy",
        "license": "CC-BY",
        "journal": "Sports",
        "study_type": "review",
    },
    {
        "filename": "sports-08-00125.pdf",
        "title": "Tapering and Peaking Maximal Strength for Powerlifting Performance: A Review",
        "authors": "Travis et al.",
        "year": 2020,
        "category": "strength",
        "license": "CC-BY",
        "journal": "Sports",
        "study_type": "review",
    },
    {
        "filename": "fspor-03-713655.pdf",
        "title": "The Minimum Effective Training Dose Required for 1RM Strength in Powerlifters",
        "authors": "Androulakis-Korakakis et al.",
        "year": 2021,
        "category": "strength",
        "license": "CC-BY",
        "journal": "Frontiers in Sports and Active Living",
        "study_type": "review",
    },
    {
        "filename": "jscr-34-2412.pdf",
        "title": "Long-Term Strength Adaptation: A 15-Year Analysis of Powerlifting Athletes",
        "authors": "Latella et al.",
        "year": 2020,
        "category": "strength",
        "license": "CC-BY",
        "journal": "Journal of Strength and Conditioning Research",
        "study_type": "observational",
    },
    {
        "filename": "40279_2019_Article_1241.pdf",
        "title": "The Effectiveness of Two Methods of Prescribing Load on Maximal Strength Development: A Systematic Review",
        "authors": "Thompson et al.",
        "year": 2020,
        "category": "strength",
        "license": "CC-BY",
        "journal": "Sports Medicine",
        "study_type": "systematic-review",
    },
]


async def main():
    supabase = get_supabase()

    # 1. Delete all existing chunks and papers
    print("Deleting existing chunks...")
    supabase.table("chunks").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    print("Deleting existing papers...")
    supabase.table("papers").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    print("Cleared.\n")

    # 2. Re-ingest all papers
    total_chunks = 0
    for i, entry in enumerate(PAPERS, 1):
        print(f"[{i}/{len(PAPERS)}] {entry['title'][:70]}...")

        metadata = PaperMetadata(
            title=entry["title"],
            authors=entry["authors"],
            year=entry["year"],
            category=entry["category"],
            license=entry["license"],
            journal=entry.get("journal"),
            doi=entry.get("doi"),
            study_type=entry.get("study_type"),
        )

        result = await ingest_paper(f"papers/{entry['filename']}", metadata)
        print(f"  -> {result.total_chunks} chunks")
        total_chunks += result.total_chunks

    print(f"\nDone! {len(PAPERS)} papers, {total_chunks} total chunks.")


if __name__ == "__main__":
    asyncio.run(main())
