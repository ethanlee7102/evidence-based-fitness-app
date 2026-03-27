# Exercise Muscle Activation Research (EMG-Backed)

Status: **COMPLETE** — 386 exercises fully researched and seeded (2026-03-20). All mappings EMG-backed from PMC, ACE, ExRx, and published research.

Final DB state: 36 muscle groups, 386 exercises, 2,890 activation mappings, avg 7.5 muscles per exercise. All 36 muscle groups used. Zero unmapped exercises.

Activation levels: maximum (primary mover), high (major synergist), medium (contributes but not primary), partial (stabilizer/minimal)

Muscle groups: 36 across 14 categories in `muscle_groups.json`. Added via migration 013: Hip Adductors, Neck, Rotator Cuff.

Research files (full EMG detail): `apps/api/data/research/`
- `chest.md` — chest exercises
- `back.md` — back exercises
- `shoulders.md` — shoulder/neck/rotator cuff exercises
- `arms.md` — bicep/tricep/forearm exercises
- `quads_calves.md` — quad/calf exercises
- `hams_glutes.md` — hamstring/glute/adductor exercises
- `core.md` — core exercises
- `fullbody_misc.md` — full body/kettlebell/plyo/cardio/stretching/band exercises
