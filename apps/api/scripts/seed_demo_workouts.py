"""Seed a shared, read-only "demo athlete" training history.

Guests (anonymous users) see this history so the app is populated on first load,
and it gives the future v2 workout-analysis chatbot real trends to talk about.

Design notes:
- The demo athlete is a NON-anonymous auth user, so the hourly anon-cleanup cron
  (migration 020) never reaps it. Its workouts are flagged is_demo = true; the
  migration-017 RLS policies expose those rows to anonymous viewers only.
- Deterministic (no randomness) so re-runs are reproducible. Idempotent: existing
  is_demo workouts for the demo user are deleted (cascading to exercises/sets),
  then re-inserted, dated relative to "now" so the demo always looks recent.
- Progression is intentionally *tellable*: bench climbs linearly, squat plateaus
  at 100 kg for three weeks then breaks through to 112.5, and week 6 is a deload
  (a visible dip in volume). Uses the service-role admin client (bypasses RLS).

Run:  cd apps/api && source venv/bin/activate && python -m scripts.seed_demo_workouts
Requires migration 017 (is_demo column) to be applied first.
"""

from datetime import datetime, timedelta, timezone

from src.db import get_admin_supabase

DEMO_EMAIL = "demo-athlete@evidence-fitness.internal"
WEEKS = 12
DELOAD_WEEK = 6  # 0-indexed

# Weekly barbell weights (kg) for the two showcase lifts - arcs already include
# the week-6 deload dip. Bench: steady climb. Squat: plateau at 100 (wk 3-5),
# deload, then break through.
BENCH_ARC = [60, 62.5, 65, 67.5, 70, 72.5, 62.5, 75, 77.5, 80, 82.5, 85]
SQUAT_ARC = [90, 95, 97.5, 100, 100, 100, 85, 102.5, 105, 107.5, 110, 112.5]

# Each exercise: (name, sets, base_weight, weekly_increment, reps). Compounds
# with an *_ARC above pass base=None. Bodyweight moves (Pull-Up) use weight 0.
UPPER_A = [
    ("Barbell Bench Press", 4, None, None, 5),
    ("Barbell Row", 4, 55, 1.5, 8),
    ("Overhead Press", 3, 40, 1.0, 8),
    ("Lat Pulldown", 3, 50, 1.0, 10),
    ("Barbell Curl", 3, 25, 0.5, 10),
    ("Tricep Pushdown", 3, 25, 0.5, 12),
]
LOWER_A = [
    ("Barbell Back Squat", 4, None, None, 5),
    ("Romanian Deadlift", 3, 70, 2.0, 8),
    ("Leg Press", 3, 120, 5.0, 10),
    ("Standing Calf Raise", 4, 60, 2.0, 12),
]
UPPER_B = [
    ("Incline Barbell Bench Press", 4, 50, 1.25, 6),
    ("Pull-Up", 4, 0, 0.0, 8),
    ("Seated Cable Row", 3, 50, 1.0, 10),
    ("Lateral Raise", 3, 10, 0.25, 15),
    ("Hammer Curl", 3, 12, 0.25, 12),
    ("Overhead Tricep Extension", 3, 25, 0.5, 12),
]
LOWER_B = [
    ("Deadlift", 3, 100, 2.5, 5),
    ("Front Squat", 3, 60, 1.5, 6),
    ("Walking Lunge", 3, 20, 1.0, 12),
    ("Seated Calf Raise", 4, 40, 1.5, 15),
]

# (weekday, template) - a 4-day upper/lower split (Mon/Tue/Thu/Fri).
SPLIT = [(0, UPPER_A), (1, LOWER_A), (3, UPPER_B), (4, LOWER_B)]


def _round25(w: float) -> float:
    """Round to the nearest 2.5 kg (realistic barbell loading)."""
    return round(w / 2.5) * 2.5


def weight_for(name: str, base, inc, week: int) -> float | None:
    if name == "Barbell Bench Press":
        return BENCH_ARC[week]
    if name == "Barbell Back Squat":
        return SQUAT_ARC[week]
    if base is None or base == 0:
        return 0.0 if base == 0 else None
    w = base + inc * week
    if week == DELOAD_WEEK:
        w *= 0.85
    return _round25(w) if w >= 20 else round(w, 1)


def get_or_create_demo_user(admin) -> str:
    """Return the demo athlete's user id, creating a non-anonymous user if needed."""
    page = 1
    while True:
        users = admin.auth.admin.list_users(page=page, per_page=1000)
        if not users:
            break
        for u in users:
            if getattr(u, "email", None) == DEMO_EMAIL:
                print(f"Found existing demo athlete: {u.id}")
                return u.id
        if len(users) < 1000:
            break
        page += 1
    res = admin.auth.admin.create_user(
        {
            "email": DEMO_EMAIL,
            "password": "demo-athlete-not-for-login-8f3a1c",
            "email_confirm": True,
        }
    )
    uid = res.user.id
    print(f"Created demo athlete: {uid}")
    return uid


def exercise_map(admin) -> dict[str, str]:
    rows = admin.table("exercises").select("id, name").eq("is_global", True).execute().data
    return {r["name"]: r["id"] for r in rows}


def main() -> None:
    admin = get_admin_supabase()
    demo_id = get_or_create_demo_user(admin)
    ex_ids = exercise_map(admin)

    # Validate every programmed exercise resolves before writing anything.
    missing = {
        name
        for _, template in SPLIT
        for (name, *_rest) in template
        if name not in ex_ids
    }
    if missing:
        raise SystemExit(f"Exercises not found in global library: {sorted(missing)}")

    # Idempotent reset: drop prior demo workouts (cascades to exercises + sets).
    admin.table("workouts").delete().eq("user_id", demo_id).eq("is_demo", True).execute()
    print("Cleared prior demo workouts.")

    start = datetime.now(timezone.utc) - timedelta(weeks=WEEKS)
    start = start.replace(hour=18, minute=0, second=0, microsecond=0)
    # Align to Monday of that week.
    start -= timedelta(days=start.weekday())

    n_workouts = n_sets = 0
    body_weight = 82.0

    for week in range(WEEKS):
        for weekday, template in SPLIT:
            started = start + timedelta(weeks=week, days=weekday)
            duration = 55 * 60 + (week % 3) * 5 * 60  # ~55-65 min
            completed = started + timedelta(seconds=duration)
            rating = 5 if week >= 8 else (3 if week == DELOAD_WEEK else 4)

            workout = (
                admin.table("workouts")
                .insert(
                    {
                        "user_id": demo_id,
                        "is_demo": True,
                        "started_at": started.isoformat(),
                        "completed_at": completed.isoformat(),
                        "duration_seconds": duration,
                        "body_weight_kg": round(body_weight, 1),
                        "rating": rating,
                    }
                )
                .execute()
                .data[0]
            )
            n_workouts += 1

            for sort_order, (name, sets, base, inc, reps) in enumerate(template):
                we = (
                    admin.table("workout_exercises")
                    .insert(
                        {
                            "workout_id": workout["id"],
                            "exercise_id": ex_ids[name],
                            "sort_order": sort_order,
                            "rest_timer_seconds": 120,
                        }
                    )
                    .execute()
                    .data[0]
                )
                w = weight_for(name, base, inc, week)
                is_deload = week == DELOAD_WEEK
                n = sets - 1 if is_deload else sets  # one fewer set on the deload

                set_rows = []
                for s in range(n):
                    # Last working set drops a rep (fatigue); RPE rises across sets.
                    set_reps = reps - 1 if s == n - 1 and reps > 5 else reps
                    set_rows.append(
                        {
                            "workout_exercise_id": we["id"],
                            "set_number": s + 1,
                            "weight_kg": w,
                            "reps": set_reps,
                            "rpe": min(9, 7 + s * 0.5),
                            "set_type": "normal",
                            "completed": True,
                            "completed_at": completed.isoformat(),
                        }
                    )
                admin.table("workout_sets").insert(set_rows).execute()
                n_sets += len(set_rows)

        body_weight -= 0.15  # slow recomp over the block

    print(f"Seeded {n_workouts} workouts / {n_sets} sets for the demo athlete.")


if __name__ == "__main__":
    main()
