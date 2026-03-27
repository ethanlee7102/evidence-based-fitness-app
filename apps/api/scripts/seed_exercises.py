"""Seed muscle_groups, exercises, and exercise_muscles tables.

Idempotent — checks existing by name before insert. Replaces all
exercise_muscles on each run.

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
BATCH_SIZE = 50


def load_json(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    with open(path) as f:
        return json.load(f)


def fetch_all(supabase, table: str, select: str, **filters) -> list[dict]:
    """Fetch all rows, paginating past Supabase's 1000-row default limit."""
    query = supabase.table(table).select(select)
    for k, v in filters.items():
        query = query.eq(k, v)
    rows = []
    offset = 0
    while True:
        batch = query.range(offset, offset + 999).execute()
        rows.extend(batch.data)
        if len(batch.data) < 1000:
            break
        offset += 1000
    return rows


def seed_muscle_groups(supabase) -> dict[str, str]:
    """Upsert muscle groups and return {name: id} mapping."""
    data = load_json("muscle_groups.json")
    logger.info(f"Seeding {len(data)} muscle groups...")

    supabase.table("muscle_groups").upsert(data, on_conflict="name").execute()

    all_rows = fetch_all(supabase, "muscle_groups", "id, name")
    mapping = {row["name"]: row["id"] for row in all_rows}
    logger.info(f"  {len(mapping)} muscle groups in DB")
    return mapping


def seed_exercises(supabase) -> dict[str, str]:
    """Seed global exercises (idempotent: skip existing by name)."""
    data = load_json("exercises.json")
    logger.info(f"Seeding {len(data)} exercises...")

    existing = fetch_all(supabase, "exercises", "name", is_global=True)
    existing_names = {row["name"].lower() for row in existing}

    new_exercises = []
    for ex in data:
        if ex["name"].lower() not in existing_names:
            ex["is_global"] = True
            ex["created_by"] = None
            new_exercises.append(ex)

    if new_exercises:
        logger.info(f"  Inserting {len(new_exercises)} new exercises ({len(existing_names)} already exist)...")
        for i in range(0, len(new_exercises), BATCH_SIZE):
            batch = new_exercises[i : i + BATCH_SIZE]
            supabase.table("exercises").insert(batch).execute()
    else:
        logger.info(f"  All {len(existing_names)} exercises already exist, nothing to insert")

    all_rows = fetch_all(supabase, "exercises", "id, name", is_global=True)
    mapping = {row["name"]: row["id"] for row in all_rows}
    logger.info(f"  {len(mapping)} global exercises in DB")
    return mapping


def seed_exercise_muscles(
    supabase,
    exercise_map: dict[str, str],
    muscle_map: dict[str, str],
) -> None:
    """Replace exercise_muscles for all global exercises.

    exercise_muscles.json format:
    [{"exercise": "Name", "muscles": [{"muscle_group": "X", "activation_level": "Y"}, ...]}, ...]
    """
    data = load_json("exercise_muscles.json")
    logger.info(f"Processing muscle mappings for {len(data)} exercises...")

    # Flatten nested format into rows with IDs
    rows = []
    skipped_exercises = []
    skipped_muscles = []
    for entry in data:
        ex_id = exercise_map.get(entry["exercise"])
        if not ex_id:
            skipped_exercises.append(entry["exercise"])
            continue
        for muscle in entry["muscles"]:
            mg_id = muscle_map.get(muscle["muscle_group"])
            if not mg_id:
                skipped_muscles.append(muscle["muscle_group"])
                continue
            rows.append({
                "exercise_id": ex_id,
                "muscle_group_id": mg_id,
                "activation_level": muscle["activation_level"],
            })

    if skipped_exercises:
        logger.warning(f"  Exercises not found in DB ({len(skipped_exercises)}): {skipped_exercises[:5]}...")
    if skipped_muscles:
        unique_skipped = list(set(skipped_muscles))
        logger.warning(f"  Muscle groups not found in DB ({len(unique_skipped)}): {unique_skipped[:5]}...")

    # Delete existing mappings for global exercises, then re-insert
    global_exercise_ids = list(exercise_map.values())
    for i in range(0, len(global_exercise_ids), BATCH_SIZE):
        batch_ids = global_exercise_ids[i : i + BATCH_SIZE]
        supabase.table("exercise_muscles").delete().in_(
            "exercise_id", batch_ids
        ).execute()

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
