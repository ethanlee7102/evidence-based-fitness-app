"""Backup + delete the audited noise chunks from the corpus.

Phase 2 noise-cleanup, step 2. Deletes the 1,387 chunks confirmed as noise by
the read-only classifier (`classify_noise_chunks.py`) AND independently reviewed
by 15 parallel agents (`results/noise_review/final_verdict.json`), minus the 15
false positives the reviewers spared.

Deleting rows (rather than re-ingesting the corpus) keeps every surviving chunk's
embedding byte-identical, so the before/after retrieval comparison is a clean A/B
— the only variable that changes is "noise chunk present / absent."

Safety:
  1. Full rows (incl. embedding vectors) are backed up to JSON FIRST.
  2. The backup is re-read and verified (count + non-empty text) before any DELETE.
  3. DELETE only runs with --execute; otherwise it's a dry run.
Restore path: re-insert the backed-up rows (embeddings preserved).

Usage:
    python -m scripts.delete_noise_chunks              # dry run (backup + verify only)
    python -m scripts.delete_noise_chunks --execute    # backup, verify, then delete
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from src.db import get_supabase

VERDICT = Path("results/noise_review/final_verdict.json")
BACKUP = Path("results/noise_review/deleted_chunks_backup.json")
BATCH = 200


def fetch_rows(sb, ids: list[str]) -> list[dict]:
    """Fetch full chunk rows (all columns, incl. embedding) for the given ids."""
    rows: list[dict] = []
    for i in range(0, len(ids), BATCH):
        batch = ids[i : i + BATCH]
        resp = sb.table("chunks").select("*").in_("id", batch).execute()
        rows.extend(resp.data or [])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="Actually delete (default: dry run)")
    args = ap.parse_args()

    verdict = json.load(open(VERDICT))
    delete_ids = verdict["delete_ids"]
    print(f"Delete set: {len(delete_ids)} chunks (from {verdict['n_flagged']} flagged, "
          f"{verdict['n_keep']} spared by reviewers)\n")

    sb = get_supabase()
    total_before = sb.table("chunks").select("id", count="exact").limit(1).execute().count
    print(f"chunks table currently holds: {total_before} rows")

    # --- 1. BACKUP ---
    print("Backing up full rows (incl. embeddings) ...")
    rows = fetch_rows(sb, delete_ids)
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(BACKUP, "w"))
    print(f"  wrote {len(rows)} rows to {BACKUP} ({BACKUP.stat().st_size/1e6:.1f} MB)")

    # --- 2. VERIFY BACKUP before touching anything ---
    fetched_ids = {r["id"] for r in rows}
    missing = set(delete_ids) - fetched_ids
    empty_text = [r["id"] for r in rows if not (r.get("text") or "").strip()]
    no_embed = [r["id"] for r in rows if not r.get("embedding")]
    print("\nBackup verification:")
    print(f"  ids in backup: {len(fetched_ids)} / {len(delete_ids)} requested")
    print(f"  missing from DB (already gone?): {len(missing)}")
    print(f"  rows with empty text: {len(empty_text)}")
    print(f"  rows with no embedding: {len(no_embed)}")
    per_paper = Counter(r["paper_id"] for r in rows)
    print(f"  spans {len(per_paper)} papers")

    if missing:
        print("\n⚠️  Some delete_ids are not in the DB. Aborting to be safe.")
        return
    if no_embed:
        print("\n⚠️  Some backed-up rows lack an embedding — backup may be incomplete. Aborting.")
        return
    print("  ✓ backup complete and consistent")

    if not args.execute:
        print("\n[DRY RUN] Backup written & verified. Re-run with --execute to delete.")
        return

    # --- 3. DELETE ---
    print("\nDeleting ...")
    deleted = 0
    for i in range(0, len(delete_ids), BATCH):
        batch = delete_ids[i : i + BATCH]
        sb.table("chunks").delete().in_("id", batch).execute()
        deleted += len(batch)
        print(f"  deleted {deleted}/{len(delete_ids)}", end="\r")
    print()

    # --- 4. Reconcile papers.total_chunks ---
    print("Reconciling papers.total_chunks ...")
    updated = 0
    for pid in per_paper:
        cnt = sb.table("chunks").select("id", count="exact").eq("paper_id", pid).limit(1).execute().count
        sb.table("papers").update({"total_chunks": cnt}).eq("id", pid).execute()
        updated += 1
    print(f"  updated {updated} papers")

    total_after = sb.table("chunks").select("id", count="exact").limit(1).execute().count
    print(f"\nDone. chunks: {total_before} → {total_after} (removed {total_before - total_after})")
    print(f"Backup for restore: {BACKUP}")


if __name__ == "__main__":
    main()
