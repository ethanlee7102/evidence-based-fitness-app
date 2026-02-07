# Flame Fitness App - Development Plan

## Overview

A workout logging app with AI-powered trend analysis. Users log workouts, track progress, and receive insights to optimize their training. The "Flame" visualization evolves based on consistency and progress.

---

## Core Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Workout Logging** | Log exercises, sets, reps, weight | ⏳ Next |
| **Progress Tracking** | Visualize strength improvements | ⏳ Planned |
| **AI Insights** | Trend analysis and recommendations | ⏳ Planned |
| **Consistency** | Workout frequency, streaks | ⏳ Planned |
---

## Technical Stack

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│         React + TypeScript + Tailwind CSS               │
│                  Deployed on Vercel                     │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      Backend                            │
│                  Python + FastAPI                       │
│              Deployed on Railway/Render                 │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      Supabase                           │
│         PostgreSQL + Auth + Storage                     │
└─────────────────────────────────────────────────────────┘
```

---

## Folder Structure

### Root (Monorepo)

```
flame-fitness/
├── apps/
│   ├── web/                      # React frontend
│   └── api/                      # Python backend
│
├── packages/
│   └── shared/                   # Shared TypeScript types
│       ├── types/
│       │   ├── user.ts
│       │   └── index.ts
│       └── package.json
│
├── supabase/
│   └── migrations/               # Database migrations
│
├── .gitignore
├── package.json                  # Root pnpm workspace config
├── pnpm-workspace.yaml
├── CLAUDE.md
├── PLAN.md
└── README.md
```

### Frontend (`apps/web/`)

```
apps/web/
├── src/
│   ├── features/
│   │   ├── auth/                 # Authentication
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── screens/
│   │   │   ├── services/
│   │   │   └── index.ts
│   │   │
│   │   ├── home/                 # Landing page
│   │   │   ├── components/
│   │   │   │   ├── FlameVisualization.tsx
│   │   │   │   ├── QuickActions.tsx
│   │   │   │   └── index.ts
│   │   │   ├── screens/
│   │   │   │   └── HomeScreen.tsx
│   │   │   └── index.ts
│   │   │
│   │   ├── workouts/             # TODO: Workout logging
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── screens/
│   │   │   └── index.ts
│   │   │
│   │   └── index.ts
│   │
│   ├── shared/
│   │   ├── components/           # Button, Card, Loading, Layout
│   │   └── hooks/
│   │
│   ├── navigation/
│   │   ├── AppRouter.tsx
│   │   ├── ProtectedRoute.tsx
│   │   └── index.ts
│   │
│   └── lib/
│       ├── supabase.ts
│       └── api.ts
│
├── public/
├── package.json
└── vite.config.ts
```

### Backend (`apps/api/`)

```
apps/api/
├── src/
│   ├── api/                       # Route handlers
│   │   ├── health.py              # Health check endpoint
│   │   └── router.py              # Combines all routers
│   │
│   ├── core/                      # Business logic (empty, ready)
│   │
│   ├── schema/                    # Pydantic models
│   │
│   ├── service/
│   │   ├── db_service.py          # Database operations
│   │   └── storage_service.py     # Supabase storage
│   │
│   └── utils/
│       ├── config.py
│       ├── auth.py
│       └── logging.py
│
├── tests/
│   └── conftest.py
│
├── app.py                         # FastAPI entry point
├── db.py                          # Database connection
└── requirements.txt
```

---

## Database Schema

### Current (Active)

```sql
-- Users (extends Supabase Auth)
create table profiles (
  id uuid references auth.users primary key,
  username text unique,
  created_at timestamp with time zone default now()
);
```

### Planned (Workout Logger)

```sql
-- Exercises library
create table exercises (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  muscle_group text,
  created_at timestamp with time zone default now()
);

-- Workout sessions
create table workouts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  date date not null default current_date,
  notes text,
  created_at timestamp with time zone default now()
);

-- Individual sets within a workout
create table workout_sets (
  id uuid primary key default gen_random_uuid(),
  workout_id uuid references workouts(id) on delete cascade,
  exercise_id uuid references exercises(id),
  set_number integer not null,
  reps integer,
  weight numeric,
  created_at timestamp with time zone default now()
);

-- Row Level Security
alter table workouts enable row level security;
alter table workout_sets enable row level security;

create policy "Users can manage own workouts" on workouts
  for all using (auth.uid() = user_id);
create policy "Users can manage own sets" on workout_sets
  for all using (workout_id in (select id from workouts where user_id = auth.uid()));
```

---

## Development Phases

### Phase 1: Project Setup ✅
- [x] Initialize monorepo with pnpm workspaces
- [x] Set up React frontend (Vite + TypeScript + Tailwind)
- [x] Set up Python backend (FastAPI)
- [x] Create Supabase project
- [x] Configure environment variables
- [x] Implement Supabase auth

### Phase 2: CV Analyzer (REMOVED) ~~✅~~
- ~~Pose estimation with MMPose/RTMPose~~
- ~~Deadlift, Squat, Bench analyzers~~
- **Removed** - Pivoted to workout logger

### Phase 3: Workout Logging ⏳ CURRENT
- [ ] Create database schema (exercises, workouts, workout_sets)
- [ ] Build workout logging API endpoints
- [ ] Create Dashboard screen (`/dashboard`)
- [ ] Build workout logging UI
- [ ] Add exercise selection
- [ ] Log sets with reps/weight

### Phase 4: Progress Tracking
- [ ] Historical workout view
- [ ] Exercise-specific progress charts
- [ ] Personal records tracking
- [ ] Volume over time

### Phase 5: AI Insights
- [ ] Integrate AI for trend analysis
- [ ] Training recommendations
- [ ] Recovery insights
- [ ] Consistency scoring

### Phase 6: Polish
- [ ] Flame visualization based on consistency
- [ ] Streak tracking
- [ ] Mobile-responsive improvements
- [ ] Error handling & edge cases

---

## Deployment

| Service | Platform | Notes |
|---------|----------|-------|
| Frontend | Vercel | Auto-deploy from main branch |
| Backend | Railway or Render | Python FastAPI |
| Database | Supabase | PostgreSQL + Auth + Storage |

---

## Next Steps

1. **Create workout database migration**
2. **Build workout logging API endpoints**
3. **Create Dashboard screen with workout form**
4. **Implement workout history view**
