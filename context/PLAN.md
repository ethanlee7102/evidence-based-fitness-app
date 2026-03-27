# Flame Fitness App - Development Plan

## Overview

A workout logging app with AI-powered trend analysis. Users log workouts, track progress, and receive insights to optimize their training. The "Flame" visualization evolves based on consistency and progress.

---

## Core Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Auth & Onboarding** | Supabase auth, 4-step profile setup | ✅ Complete |
| **Workout Logging** | Log exercises, sets, reps, weight, RPE | ✅ Complete |
| **Exercise Library** | 386 exercises, EMG-backed muscle mappings | ✅ Complete |
| **RAG Chatbot** | Exercise science Q&A with cited research (195 papers) | ✅ Complete |
| **Progress Tracking** | Volume per muscle, PRs, strength curves | ⏳ Phase 4 |
| **AI Insights** | Agentic RAG v2 — workout data + literature router | ⏳ Phase 5 |
| **Polish** | Flame visualization, streaks, mobile improvements | ⏳ Phase 6 |
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
│   │   ├── home/                 # Landing page + Dashboard home
│   │   │   ├── components/
│   │   │   │   ├── FlameVisualization.tsx
│   │   │   │   ├── QuickActions.tsx
│   │   │   │   └── index.ts
│   │   │   ├── screens/
│   │   │   │   ├── HomeScreen.tsx        # Landing page (/)
│   │   │   │   └── HomeDashboardScreen.tsx # Dashboard home (/dashboard/home)
│   │   │   └── index.ts
│   │   │
│   │   ├── dashboard/            # Layout shell for dashboard
│   │   │   ├── components/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── DashboardLayout.tsx
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts      # NAV_ITEMS definition
│   │   │   └── index.ts
│   │   │
│   │   ├── workouts/             # Workout logging + history
│   │   │   ├── components/
│   │   │   ├── screens/
│   │   │   │   └── WorkoutsScreen.tsx
│   │   │   └── index.ts
│   │   │
│   │   ├── analysis/             # AI trends, charts
│   │   │   ├── components/
│   │   │   ├── screens/
│   │   │   │   └── AnalysisScreen.tsx
│   │   │   └── index.ts
│   │   │
│   │   ├── chat/                 # AI assistant
│   │   │   ├── components/
│   │   │   ├── screens/
│   │   │   │   └── ChatScreen.tsx
│   │   │   └── index.ts
│   │   │
│   │   ├── profile/              # User settings
│   │   │   ├── components/
│   │   │   ├── screens/
│   │   │   │   └── ProfileScreen.tsx
│   │   │   └── index.ts
│   │   │
│   │   └── index.ts
│   │
│   ├── shared/
│   │   ├── components/           # Button, Card, Loading, Layout
│   │   └── hooks/
│   │
│   ├── navigation/
│   │   ├── AppRouter.tsx         # Nested routes for dashboard
│   │   ├── ProtectedRoute.tsx
│   │   ├── OnboardingRoute.tsx
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

### Phase 3: Dashboard & Workout Logging ✅
- [x] Create Dashboard with 5-tab sidebar navigation
- [x] Create feature folders (workouts, analysis, chat, profile)
- [x] Create database schema (exercises, workouts, workout_sets) — Migration 011
- [x] Build workout logging API endpoints — 20 endpoints on `/workouts`
- [x] Build workout logging UI in WorkoutsScreen
- [x] Add exercise selection (search + recent exercises + custom creation)
- [x] Log sets with reps/weight/RPE
- [x] Phase 3 Polish: tap PREV to auto-populate, RPE input, workout detail view, recent exercises in search, rest timer with auto-start, per-card resume, pause-aware timer

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

## Dashboard Navigation

```
/dashboard                → redirects to /dashboard/home
/dashboard/home           → HomeDashboardScreen (welcome, quick stats)
/dashboard/workouts       → WorkoutsScreen (logging + history)
/dashboard/analysis       → AnalysisScreen (AI trends, charts)
/dashboard/chat           → ChatScreen (AI assistant)
/dashboard/profile        → ProfileScreen (user settings)
```

**Sidebar navigation** with lucide-react icons:
- Home, Workouts, Analysis, Chat, Profile
- Sign out button at bottom

---
