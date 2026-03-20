"""Seed muscle_groups, exercises, and exercise_muscles tables.

Idempotent — uses upsert (ON CONFLICT DO UPDATE) for muscle_groups and exercises,
and replaces exercise_muscles on each run.

Usage:
    cd apps/api
    source venv/bin/activate
    python -m scripts.seed_exercises
"""

import json
import logging
from pathlib import Path

from src.db import get_supabase

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_json(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    with open(path) as f:
        return json.load(f)


def seed_muscle_groups(supabase) -> dict[str, str]:
    """Upsert muscle groups and return {name: id} mapping."""
    data = load_json("muscle_groups.json")
    logger.info(f"Seeding {len(data)} muscle groups...")

    # Upsert all muscle groups
    response = (
        supabase.table("muscle_groups")
        .upsert(data, on_conflict="name")
        .execute()
    )

    # Build name -> id mapping
    all_rows = supabase.table("muscle_groups").select("id, name").execute()
    mapping = {row["name"]: row["id"] for row in all_rows.data}
    logger.info(f"  {len(mapping)} muscle groups in DB")
    return mapping


def seed_exercises(supabase) -> dict[str, str]:
    """Seed global exercises (idempotent: skip existing by name)."""
    data = load_json("exercises.json")
    logger.info(f"Seeding {len(data)} exercises...")

    # Check which global exercises already exist
    existing = (
        supabase.table("exercises")
        .select("name")
        .eq("is_global", True)
        .execute()
    )
    existing_names = {row["name"].lower() for row in existing.data}

    # Filter to only new exercises
    new_exercises = []
    for ex in data:
        if ex["name"].lower() not in existing_names:
            ex["is_global"] = True
            ex["created_by"] = None
            new_exercises.append(ex)

    if new_exercises:
        logger.info(f"  Inserting {len(new_exercises)} new exercises ({len(existing_names)} already exist)...")
        BATCH_SIZE = 50
        for i in range(0, len(new_exercises), BATCH_SIZE):
            batch = new_exercises[i : i + BATCH_SIZE]
            supabase.table("exercises").insert(batch).execute()
    else:
        logger.info(f"  All {len(existing_names)} exercises already exist, nothing to insert")

    # Build name -> id mapping for global exercises
    all_rows = (
        supabase.table("exercises")
        .select("id, name")
        .eq("is_global", True)
        .execute()
    )
    mapping = {row["name"]: row["id"] for row in all_rows.data}
    logger.info(f"  {len(mapping)} global exercises in DB")
    return mapping


def seed_exercise_muscles(
    supabase,
    exercise_map: dict[str, str],
    muscle_map: dict[str, str],
) -> None:
    """Replace exercise_muscles for all global exercises."""
    data = load_json("exercise_muscles.json")
    logger.info(f"Processing {len(data)} exercise-muscle mappings...")

    # Resolve names to IDs
    rows = []
    skipped = 0
    for entry in data:
        ex_id = exercise_map.get(entry["exercise_name"])
        mg_id = muscle_map.get(entry["muscle_group_name"])
        if not ex_id or not mg_id:
            skipped += 1
            if not ex_id:
                logger.warning(f"  Exercise not found: {entry['exercise_name']}")
            if not mg_id:
                logger.warning(f"  Muscle group not found: {entry['muscle_group_name']}")
            continue
        rows.append({
            "exercise_id": ex_id,
            "muscle_group_id": mg_id,
            "activation_level": entry["activation_level"],
        })

    if skipped:
        logger.warning(f"  Skipped {skipped} mappings due to missing references")

    # Delete existing mappings for global exercises, then re-insert
    global_exercise_ids = list(exercise_map.values())
    # Delete in batches to avoid URL length limits
    BATCH_SIZE = 50
    for i in range(0, len(global_exercise_ids), BATCH_SIZE):
        batch_ids = global_exercise_ids[i : i + BATCH_SIZE]
        supabase.table("exercise_muscles").delete().in_(
            "exercise_id", batch_ids
        ).execute()

    # Insert new mappings in batches
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        supabase.table("exercise_muscles").insert(batch).execute()

    logger.info(f"  Inserted {len(rows)} exercise-muscle mappings")


def main():
    supabase = get_supabase()

    muscle_map = seed_muscle_groups(supabase)
    exercise_map = seed_exercises(supabase)
    seed_exercise_muscles(supabase, exercise_map, muscle_map)

    logger.info("Seed complete!")


if __name__ == "__main__":
    main()
