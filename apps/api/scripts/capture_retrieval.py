"""Capture retrieval results (top-20 per case) over the full eval dataset — NO LLM.

A retrieval-only snapshot for qualitative before/after inspection of the reranker.
Distinct from capture_rag_fixture.py, which runs the full pipeline (incl. Gemini
generation). This one only embeds + retrieves (+ reranks), so it's fast and free, and
covers ALL 100 cases — not just the 12 verified-target cases that measure_target_chunks
scores. That lets us spot regressions the 12-case aggregate hides (e.g. a case where the
per-paper cap chops a legitimately-concentrated paper's correct chunk).

Each chunk is tagged with a status so one ordered list per case shows the full picture:
  kept           -> made the final top-5 (what production would surface)
  cap_suppressed -> ranked high enough for the top-5 but dropped by the per-paper cap
                    (rerank mode only — this is the "what got chopped" signal)
  below_cutoff   -> simply ranked below the top-5

Usage:
    # before (vector-only) and after (rerank) — diff the two files:
    python -m scripts.capture_retrieval --output results/retrieval_before.json
    python -m scripts.capture_retrieval --rerank --output results/retrieval_after.json
    python -m scripts.capture_retrieval --rerank --ids NUT-016 GEN-004   # subset
"""

import argparse
import asyncio
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from src.core.reranker import rerank as rerank_chunks
from src.core.retrieval import retrieve_chunks
from src.schema.rag import ChunkResponse
from src.utils.config import config

DATASET = Path("tests/eval/test_dataset.json")
SNIPPET_CHARS = 160


def _surname(authors: str) -> str:
    """First-author surname (handles 'Smith et al.' / 'Smith, J.')."""
    if not authors:
        return "?"
    return authors.replace(",", " ").split()[0]


def _load_cases() -> list[dict]:
    ds = json.loads(DATASET.read_text())
    cases = ds["test_cases"] if isinstance(ds, dict) and "test_cases" in ds else ds
    return cases


def _tag_statuses(chunks: list[ChunkResponse], cap: int, top_n: int) -> list[str]:
    """Walk chunks in priority order, simulating the per-paper cap filling top_n slots.

    A chunk is `cap_suppressed` when a top-5 slot is still open but its paper already
    hit the cap — i.e. it would have made the top-5 by rank, but the cap displaced it.
    For the vector-only path, pass cap >= top_n so the cap never bites (rank-only tags).
    """
    per_paper: Counter[str] = Counter()
    kept = 0
    statuses: list[str] = []
    for c in chunks:
        if kept < top_n and per_paper[c.paper_id] < cap:
            statuses.append("kept")
            per_paper[c.paper_id] += 1
            kept += 1
        elif kept < top_n:
            statuses.append("cap_suppressed")
        else:
            statuses.append("below_cutoff")
    return statuses


async def _capture_case(question: str, use_rerank: bool, depth: int) -> tuple[list[ChunkResponse], list[str]]:
    if use_rerank:
        # Mirror retrieve_reranked's stages 1-2, but keep the UNcapped reranked order
        # so we can show (and tag) what the cap chops. -1.0 = no similarity floor.
        fetch = await retrieve_chunks(
            question,
            top_k=config.RERANK_FETCH_DEPTH,
            similarity_threshold=-1.0,
            ef_search=config.RERANK_EF_SEARCH,
        )
        ordered = (await rerank_chunks(question, fetch.chunks))[:depth]
        statuses = _tag_statuses(ordered, cap=config.RERANK_PER_PAPER_CAP, top_n=config.RERANK_TOP_N)
    else:
        res = await retrieve_chunks(question, top_k=depth)
        ordered = res.chunks
        # No cap on the vector path: cap >= top_n disables suppression tagging.
        statuses = _tag_statuses(ordered, cap=depth + 1, top_n=config.RAG_TOP_K)
    return ordered, statuses


def _chunk_row(rank: int, status: str, c: ChunkResponse) -> dict:
    return {
        "rank": rank,
        "status": status,
        "paper": f"{_surname(c.authors)} {c.year}",
        "chunk_index": c.chunk_index,
        "chunk_id": c.chunk_id,
        "section": c.section,
        "similarity": round(c.similarity, 4),
        "rerank_score": round(c.rerank_score, 4) if c.rerank_score is not None else None,
        "snippet": c.chunk_text[:SNIPPET_CHARS].replace("\n", " ").strip(),
    }


async def main() -> None:
    ap = argparse.ArgumentParser(description="Capture retrieval-only top-N per case (no LLM)")
    ap.add_argument("--rerank", action="store_true",
                    help="Deep fetch + cross-encoder rerank (else vector-only)")
    ap.add_argument("--depth", type=int, default=20, help="Chunks to save per case")
    ap.add_argument("--ids", nargs="*", help="Subset of case IDs (default: all)")
    ap.add_argument("--output", type=str, required=True, help="Save JSON to this path")
    args = ap.parse_args()

    cases = _load_cases()
    if args.ids:
        wanted = set(args.ids)
        cases = [c for c in cases if c["id"] in wanted]

    cases_out = []
    for i, case in enumerate(cases, 1):
        ordered, statuses = await _capture_case(case["question"], args.rerank, args.depth)
        rows = [_chunk_row(r, s, c) for r, (c, s) in enumerate(zip(ordered, statuses), 1)]
        cases_out.append({
            "id": case["id"],
            "category": case.get("category"),
            "question": case["question"],
            "top5_papers": dict(Counter(row["paper"] for row in rows if row["status"] == "kept")),
            "chunks": rows,
        })
        print(f"[{i}/{len(cases)}] {case['id']}: {len(rows)} chunks")

    report = {
        "mode": "rerank" if args.rerank else "vector",
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "depth": args.depth,
        "total_cases": len(cases_out),
        "config": {
            "fetch_depth": config.RERANK_FETCH_DEPTH,
            "ef_search": config.RERANK_EF_SEARCH,
            "per_paper_cap": config.RERANK_PER_PAPER_CAP,
            "top_n": config.RERANK_TOP_N,
            "model": config.RERANK_MODEL,
            "max_length": config.RERANK_MAX_LENGTH,
        } if args.rerank else {"top_n": config.RAG_TOP_K, "similarity_threshold": config.RAG_SIMILARITY_THRESHOLD},
        "cases": cases_out,
    }
    Path(args.output).write_text(json.dumps(report, indent=2))
    print(f"\nSaved {len(cases_out)} cases ({report['mode']}) to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
