# Flame Fitness App - Development Plan

## Overview

A fitness application centered around a "Flame" visualization that evolves based on user improvement across four pillars: Consistency, Technique, Progress, and Knowledge. Each pillar contributes to a Composite Improvement Score that drives the Flame's visual state.

**MVP Focus:** Technique pillar (form video analyzer) starting with Deadlift, then Squat, then Bench Press.

---

## The Four Pillars

| Pillar | Description | Data Sources | Status |
|--------|-------------|--------------|--------|
| **Technique** | CV-based form analysis from uploaded videos | MMPose/RTMPose pose estimation | ✅ MVP |
| **Consistency** | Workout frequency, streaks, adherence | Logged workouts, wearables | ⏳ Later |
| **Progress** | Strength improvements over time | Workout logs, strength standards | ⏳ Later |
| **Knowledge** | RAG-powered fitness education | EXRX, NSCA, ACSM sources | ⏳ Later |

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
              ┌───────────┴───────────┐
              ▼                       ▼
┌─────────────────────┐    ┌─────────────────────────────┐
│      Supabase       │    │      ML Processing          │
│  - PostgreSQL       │    │  - MMPose/RTMPose (ONNX)    │
│  - Auth             │    │  - OpenCV                   │
│  - Storage          │    │  - Custom analysis logic    │
└─────────────────────┘    └─────────────────────────────┘
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
│       │   ├── analysis.ts
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
├── PLAN.md
└── README.md
```

### Frontend (`apps/web/`)

```
apps/web/
├── src/
│   ├── features/
│   │   ├── auth/
│   │   │   ├── components/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   ├── SignupForm.tsx
│   │   │   │   └── index.ts
│   │   │   ├── hooks/
│   │   │   │   ├── useAuth.ts
│   │   │   │   └── index.ts
│   │   │   ├── screens/
│   │   │   │   ├── LoginScreen.tsx
│   │   │   │   ├── SignupScreen.tsx
│   │   │   │   └── index.ts
│   │   │   ├── services/
│   │   │   │   ├── authService.ts
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── analysis/
│   │   │   ├── components/
│   │   │   │   ├── ResultsDisplay.tsx
│   │   │   │   ├── ScoreCard.tsx
│   │   │   │   ├── IssuesList.tsx
│   │   │   │   ├── PoseOverlay.tsx
│   │   │   │   └── index.ts
│   │   │   ├── hooks/
│   │   │   │   ├── useAnalysis.ts
│   │   │   │   └── index.ts
│   │   │   ├── screens/
│   │   │   │   ├── AnalysisResultScreen.tsx
│   │   │   │   ├── HistoryScreen.tsx
│   │   │   │   └── index.ts
│   │   │   ├── services/
│   │   │   │   ├── analysisService.ts
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── upload/
│   │   │   ├── components/
│   │   │   │   ├── VideoUploader.tsx
│   │   │   │   ├── VideoPreview.tsx
│   │   │   │   ├── ExerciseSelector.tsx
│   │   │   │   ├── UploadProgress.tsx
│   │   │   │   └── index.ts
│   │   │   ├── hooks/
│   │   │   │   ├── useVideoUpload.ts
│   │   │   │   └── index.ts
│   │   │   ├── screens/
│   │   │   │   ├── UploadScreen.tsx
│   │   │   │   └── index.ts
│   │   │   ├── services/
│   │   │   │   ├── uploadService.ts
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── home/
│   │   │   ├── components/
│   │   │   │   ├── FlameVisualization.tsx   # The Flame!
│   │   │   │   ├── QuickActions.tsx
│   │   │   │   └── index.ts
│   │   │   ├── screens/
│   │   │   │   ├── HomeScreen.tsx
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   │
│   │   └── index.ts
│   │
│   ├── shared/
│   │   ├── components/
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Loading.tsx
│   │   │   ├── Layout.tsx
│   │   │   └── index.ts
│   │   ├── hooks/
│   │   │   ├── useSupabase.ts
│   │   │   └── index.ts
│   │   └── utils/
│   │       ├── formatters.ts
│   │       └── index.ts
│   │
│   ├── navigation/
│   │   ├── AppRouter.tsx
│   │   ├── ProtectedRoute.tsx
│   │   └── index.ts
│   │
│   ├── lib/
│   │   ├── supabase.ts            # Supabase client init
│   │   └── api.ts                 # API client for backend
│   │
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
│
├── public/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

### Backend (`apps/api/`)

```
apps/api/
├── src/
│   ├── api/                       # Route handlers
│   │   ├── __init__.py
│   │   ├── analysis.py            # POST /analyze, GET /analysis/{id}
│   │   ├── videos.py              # Video-related endpoints
│   │   ├── health.py              # Health check endpoint
│   │   └── router.py              # Combines all routers
│   │
│   ├── core/                      # Business logic
│   │   ├── __init__.py
│   │   ├── pose_estimator.py      # MMPose/RTMPose wrapper (ONNX)
│   │   ├── video_processor.py     # Frame extraction
│   │   ├── angle_calculator.py    # Joint angle math
│   │   └── analyzers/
│   │       ├── __init__.py
│   │       ├── base.py            # Base analyzer class
│   │       ├── deadlift.py        # Deadlift-specific logic
│   │       ├── squat.py           # Squat-specific logic (later)
│   │       └── bench.py           # Bench-specific logic (later)
│   │
│   ├── schema/                    # Pydantic models
│   │   ├── __init__.py
│   │   ├── analysis.py            # AnalysisRequest, AnalysisResponse
│   │   ├── video.py               # VideoMetadata
│   │   └── common.py              # Shared schemas
│   │
│   ├── service/                   # Service layer
│   │   ├── __init__.py
│   │   ├── analysis_service.py    # Orchestrates analysis flow
│   │   ├── storage_service.py     # Supabase storage interactions
│   │   └── db_service.py          # Database operations
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py              # Environment config
│   │   └── logging.py             # Logging setup
│   │
│   └── __init__.py
│
├── tests/                         # Test files (co-located pattern)
│   ├── __init__.py
│   ├── test_deadlift_analyzer.py
│   ├── test_pose_estimator.py
│   └── conftest.py
│
├── app.py                         # FastAPI app entry point
├── db.py                          # Database connection
├── requirements.txt
├── requirements-dev.txt
└── Dockerfile
```

---

## Database Schema

```sql
-- Users (extends Supabase Auth)
create table profiles (
  id uuid references auth.users primary key,
  username text unique,
  created_at timestamp with time zone default now()
);

-- Uploaded videos
create table videos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  storage_path text not null,
  exercise_type text not null check (exercise_type in ('deadlift', 'squat', 'bench')),
  duration_seconds integer,
  status text default 'uploaded' check (status in ('uploaded', 'processing', 'completed', 'failed')),
  uploaded_at timestamp with time zone default now()
);

-- Analysis results
create table analyses (
  id uuid primary key default gen_random_uuid(),
  video_id uuid references videos(id) on delete cascade,
  technique_score integer check (technique_score >= 0 and technique_score <= 100),
  issues jsonb default '[]',
  bar_path_data jsonb,
  landmarks_data jsonb,
  processed_at timestamp with time zone default now()
);

-- Row Level Security
alter table profiles enable row level security;
alter table videos enable row level security;
alter table analyses enable row level security;

-- Users can only see their own data
create policy "Users can view own profile" on profiles for select using (auth.uid() = id);
create policy "Users can view own videos" on videos for select using (auth.uid() = user_id);
create policy "Users can insert own videos" on videos for insert with check (auth.uid() = user_id);
create policy "Users can view own analyses" on analyses for select
  using (video_id in (select id from videos where user_id = auth.uid()));
```

---

## Development Phases

### Phase 0: Learning & Exploration ✅
- [x] Understand pose estimation (switched from MediaPipe to MMPose/RTMPose)
- [x] Understand landmark coordinates and angles
- [x] Learn bar path tracking via wrist positions

### Phase 1: Project Setup
- [ ] Initialize monorepo with pnpm workspaces
- [ ] Set up React frontend (Vite + TypeScript + Tailwind)
- [ ] Set up Python backend (FastAPI)
- [ ] Create Supabase project
- [ ] Configure environment variables
- [ ] Set up basic CI (lint, type check)

### Phase 2: Auth & Upload
- [ ] Implement Supabase auth in frontend
- [ ] Build auth screens (login, signup)
- [ ] Build video upload flow
- [ ] Store videos in Supabase Storage

### Phase 3: Deadlift Analyzer
- [x] Integrate MMPose/RTMPose in backend (replaced MediaPipe)
- [ ] Build video processing pipeline
- [ ] Implement deadlift form analysis:
  - Bar path tracking
  - Back angle analysis
  - Hip hinge pattern
  - Lockout detection
- [ ] Build results display UI
- [ ] Test with real deadlift videos

### Phase 4: Squat & Bench
- [ ] Add squat analyzer (depth, knee tracking)
- [ ] Add bench analyzer (bar path J-curve)
- [ ] Unified results UI for all lifts

### Phase 5: Polish
- [ ] Analysis history view
- [ ] Score trending over time
- [ ] Basic Flame visualization
- [ ] Error handling & edge cases

---

## Key Technical Details

### Pose Landmarks for Deadlift (MediaPipe-compatible indices)
Uses MMPose/RTMPose with COCO→MediaPipe index mapping:
- Shoulders (11, 12) - back angle
- Hips (23, 24) - hip hinge tracking
- Knees (25, 26) - knee angle
- Ankles (27, 28) - leg angle
- Wrists (15, 16) - **bar path tracking**

### Bar Path Tracking
Track wrist midpoint across frames as proxy for bar position:
```python
bar_x = (left_wrist.x + right_wrist.x) / 2
bar_y = (left_wrist.y + right_wrist.y) / 2
```

### Angle Calculation
```python
def calculate_angle(a, b, c):
    """Angle at point B given points A, B, C."""
    ba = (a['x'] - b['x'], a['y'] - b['y'])
    bc = (c['x'] - b['x'], c['y'] - b['y'])
    dot = ba[0]*bc[0] + ba[1]*bc[1]
    mag_ba = math.sqrt(ba[0]**2 + ba[1]**2)
    mag_bc = math.sqrt(bc[0]**2 + bc[1]**2)
    cos_angle = max(-1, min(1, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_angle))
```

### Video Requirements
- Format: MP4, MOV
- Max duration: 30 seconds
- Max size: 100MB
- **Camera angle: Side view (sagittal plane)**

---

## Deployment

| Service | Platform | Notes |
|---------|----------|-------|
| Frontend | Vercel | Auto-deploy from main branch |
| Backend | Railway or Render | Python + long-running processes |
| Database | Supabase | PostgreSQL + Auth + Storage |

---

## Next Steps

1. **Initialize the monorepo structure**
2. **Set up pnpm workspaces**
3. **Scaffold React frontend with Vite**
4. **Scaffold FastAPI backend**
5. **Create Supabase project and run migrations**
