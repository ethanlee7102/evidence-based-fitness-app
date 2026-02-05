# Flame Fitness

AI-powered form analysis for the Big 3 lifts (squat, bench, deadlift). Upload your videos, get instant feedback on your technique, and track your improvement over time.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│         React + TypeScript + Tailwind CSS               │
│              Deployed on Vercel                         │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                      Backend                            │
│              Python + FastAPI                           │
│          Deployed on Railway/Render                     │
└─────────────────────┬───────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌─────────────────┐    ┌─────────────────────────────────┐
│    Supabase     │    │       ML Processing             │
│  - PostgreSQL   │    │  - MediaPipe Pose Estimation    │
│  - Auth         │    │  - OpenCV video processing      │
│  - Storage      │    │  - Custom form analysis logic   │
└─────────────────┘    └─────────────────────────────────┘
```

## Project Structure

```
flame-fitness/
├── apps/
│   ├── web/                      # React frontend
│   │   └── src/
│   │       ├── features/         # Feature-based modules
│   │       │   ├── auth/         # Authentication
│   │       │   ├── analysis/     # Analysis results
│   │       │   ├── upload/       # Video upload
│   │       │   └── home/         # Home screen
│   │       ├── shared/           # Shared components/hooks
│   │       ├── navigation/       # Routing
│   │       └── lib/              # API client, Supabase
│   │
│   └── api/                      # Python backend
│       ├── src/
│       │   ├── api/              # Route handlers
│       │   ├── core/             # Business logic
│       │   │   └── analyzers/    # Exercise analyzers
│       │   ├── schema/           # Pydantic models
│       │   ├── service/          # Service layer
│       │   └── utils/            # Config, auth, logging
│       ├── tests/                # Test files
│       ├── app.py                # FastAPI entry point
│       └── db.py                 # Database connection
│
├── packages/
│   └── shared/                   # Shared TypeScript types
│       └── types/
│
└── supabase/
    └── migrations/               # Database schema
```

## Prerequisites

- Node.js 18+
- pnpm 9+
- Python 3.11+
- Supabase account

## Setup

### 1. Clone and install dependencies

```bash
# Install pnpm if you don't have it
npm install -g pnpm

# Install Node dependencies
pnpm install

# Set up Python environment
cd apps/api
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### 2. Set up Supabase

1. Create a new Supabase project at https://supabase.com
2. Run the migration in `supabase/migrations/00001_initial_schema.sql`
3. Create a storage bucket called `videos` (set to public)
4. Configure storage policies for the videos bucket

### 3. Configure environment variables

**Frontend (`apps/web/.env`):**
```
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxx
VITE_API_URL=http://localhost:8000
```

**Backend (`apps/api/.env`):**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=sb_secret_xxx
```

### 4. Run development servers

```bash
# From root directory - runs both frontend and backend
pnpm dev

# Or run individually:
pnpm dev:web    # Frontend on http://localhost:3000
pnpm dev:api    # Backend on http://localhost:8000 (requires venv activated)
```

## Form Analysis

The app analyzes form for three lifts:

### Deadlift
- **Bar path tracking** - Should be vertical and close to body
- **Back angle** - Maintain neutral spine
- **Hip hinge pattern** - Proper hip/knee coordination
- **Lockout position** - Full hip extension at top

### Squat
- **Depth** - Hip crease below knee
- **Knee tracking** - Over toes, not caving
- **Back angle** - Consistent throughout
- **Bar path** - Vertical over midfoot

### Bench Press
- **Bar path** - Slight J-curve pattern
- **Elbow angle** - 45-75 degrees from torso
- **Wrist alignment** - Stacked over elbows
- **Symmetry** - Left/right balance

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| Database | PostgreSQL (Supabase) |
| Auth | Supabase Auth |
| Storage | Supabase Storage |
| ML | MediaPipe Pose Estimation, OpenCV |
| Monorepo | pnpm workspaces |

## Deployment

### Frontend (Vercel)
1. Connect your repository to Vercel
2. Set root directory to `apps/web`
3. Add environment variables

### Backend (Railway/Render)
1. Create a new Python service
2. Set root directory to `apps/api`
3. Set start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Add environment variables
