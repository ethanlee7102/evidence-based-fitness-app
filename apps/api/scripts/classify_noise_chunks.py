"""Read-only classifier for noise chunks in the RAG corpus.

Phase 2 noise-cleanup, step 1: identify bibliography / boilerplate chunks that
pollute retrieval WITHOUT deleting anything. Deep fetch + reranking surfaced a
failure mode vector-only search hid: the cross-encoder promotes reference-list
chunks because citation *titles* are dense keyword matches for the query (e.g.
CVD-001 has two bibliography chunks at rank 2-3). See RERANK_EVAL_REPORT.md.

Design decision: classify by chunk TEXT, not section label. A section-label
filter is wrong because chunk-boundary spill mislabels real prose — NUT-014's
rank-1 chunk has section="References" but the text is genuine content that
deserves to rank first. Content signal is primary; the section label is only a
secondary vote for the unambiguous boilerplate sections.

This script deletes NOTHING. It prints a report and dumps every flagged chunk's
full text to JSON so the flagged set can be audited by hand before any DELETE.

Usage:
    python -m scripts.classify_noise_chunks
    python -m scripts.classify_noise_chunks --output results/noise_audit.json
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from src.core.noise_filter import biblio_detail, is_noise
from src.db import get_supabase


def classify(chunk: dict) -> dict:
    """Classify one chunk for the audit. Verdict comes from the shared
    src.core.noise_filter (same rule ingestion uses); biblio_detail adds the
    diagnostic columns for human review of the dump.
    """
    text = chunk.get("text") or ""
    section = chunk.get("section") or ""
    noise, reason = is_noise(text, section, chunk.get("chunk_index") or 0)
    bib = biblio_detail(text)
    return {**chunk, "noise": noise, "reason": reason, **bib}


def fetch_all_chunks() -> list[dict]:
    """Page through the chunks table (Supabase caps at 1000 rows/response)."""
    sb = get_supabase()
    rows: list[dict] = []
    page = 0
    size = 1000
    while True:
        resp = (
            sb.table("chunks")
            .select("id, paper_id, chunk_index, section, text, token_count")
            .range(page * size, page * size + size - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < size:
            break
        page += 1
    return rows


def fetch_paper_titles() -> dict:
    sb = get_supabase()
    resp = sb.table("papers").select("id, title, category").execute()
    return {p["id"]: p for p in (resp.data or [])}


def main():
    ap = argparse.ArgumentParser(description="Read-only noise-chunk classifier (deletes nothing)")
    ap.add_argument("--output", type=str, default=None, help="Dump flagged chunks to JSON for audit")
    args = ap.parse_args()

    print("Fetching all chunks ...")
    chunks = fetch_all_chunks()
    papers = fetch_paper_titles()
    print(f"  {len(chunks)} chunks across {len(papers)} papers\n")

    classified = [classify(c) for c in chunks]
    flagged = [c for c in classified if c["noise"]]

    # --- Summary ---
    print("=" * 72)
    print(f"FLAGGED AS NOISE: {len(flagged)} / {len(chunks)} chunks "
          f"({100*len(flagged)/max(1,len(chunks)):.1f}%)")
    print("=" * 72)

    by_reason = Counter(c["reason"] for c in flagged)
    print("\nBy reason:")
    for r, n in by_reason.most_common():
        print(f"  {n:5}  {r}")

    print("\nBy section label (top 15):")
    for sec, n in Counter((c.get("section") or "(none)")[:40] for c in flagged).most_common(15):
        print(f"  {n:5}  {sec}")

    print("\nMost-affected papers (top 15):")
    by_paper = Counter(c["paper_id"] for c in flagged)
    for pid, n in by_paper.most_common(15):
        title = (papers.get(pid, {}).get("title") or "?")[:50]
        total = sum(1 for c in classified if c["paper_id"] == pid)
        print(f"  {n:3}/{total:<3}  {title}")

    # --- Audit dump ---
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        audit = []
        for c in sorted(flagged, key=lambda x: (x["paper_id"], x["chunk_index"])):
            audit.append({
                "id": c["id"],
                "paper_id": c["paper_id"],
                "paper_title": papers.get(c["paper_id"], {}).get("title"),
                "chunk_index": c["chunk_index"],
                "section": c.get("section"),
                "reason": c["reason"],
                "doi": c["doi"], "repo": c["repo"],
                "author_init": c["author_init"], "prose_ratio": c["prose_ratio"],
                "token_count": c.get("token_count"),
                "text": c.get("text"),
            })
        json.dump({
            "total_chunks": len(chunks),
            "flagged_count": len(flagged),
            "flagged": audit,
        }, open(out, "w"), indent=2)
        print(f"\nAudit dump written to {out} ({len(audit)} chunks, full text)")


if __name__ == "__main__":
    main()
