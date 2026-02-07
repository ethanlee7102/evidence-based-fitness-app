# Flame Fitness - Project Context

## Overview
Flame Fitness is a workout logging app with AI-powered trend analysis. Users log workouts, track progress, and receive insights to optimize their training.

## Tech Stack
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Backend**: Python + FastAPI
- **Database/Auth/Storage**: Supabase (PostgreSQL)
- **Monorepo**: pnpm workspaces

## Project Structure

```
flame-fitness/
├── apps/
│   ├── web/                      # React frontend (port 3000)
│   │   └── src/
│   │       ├── features/         # Feature-based modules
│   │       │   ├── auth/         # {components, hooks, screens, services, types}
│   │       │   ├── dashboard/    # Main app dashboard after onboarding
│   │       │   ├── home/         # Landing page + Flame visualization
│   │       │   └── onboarding/   # Multi-step user onboarding
│   │       ├── shared/           # Shared UI (Button, Card, Loading, Layout)
│   │       ├── navigation/       # AppRouter, ProtectedRoute, OnboardingRoute
│   │       └── lib/              # supabase.ts, api.ts
│   │
│   └── api/                      # Python backend (port 8000)
│       ├── src/
│       │   ├── api/              # Route handlers (health, profile)
│       │   ├── core/             # Business logic (empty, ready for workout features)
│       │   ├── schema/           # Pydantic models (profile.py)
│       │   ├── service/          # db_service, storage_service
│       │   ├── utils/            # config, auth, logging
│       │   └── db.py             # Supabase client
│       ├── tests/
│       └── app.py                # FastAPI entry point
│
├── packages/shared/types/        # Shared TypeScript types (profile.ts, user.ts)
└── supabase/migrations/          # Database schema
```

## Key Patterns

### Frontend
- **Feature-based architecture**: Each feature has components/, hooks/, screens/, services/, types/
- **Auth via Supabase**: useAuth hook provides user, session, signIn, signOut
- **API calls**: Use `apiRequest()` from lib/api.ts with JWT token
- **Protected routes**: Wrap with `<ProtectedRoute>` component
- **Onboarding required routes**: Wrap with `<OnboardingRoute>` for routes that require completed profile

### Backend
- **Entry point**: `app.py` (run with `uvicorn app:app`)
- **Auth**: JWT verification via `get_current_user` dependency

### Database Tables
- `profiles` - extends Supabase auth.users with onboarding fields:
  - `display_name`, `birthday`, `gender`, `height_cm`, `weight_kg`
  - `units_preference`, `experience_level`, `goal`
  - `workout_days_per_week`, `preferred_days`, `injuries_limitations`
  - `onboarding_completed`, `onboarding_completed_at`

## Commands

```bash
# Install dependencies
pnpm install

# Run both frontend and backend
pnpm dev

# Run individually
pnpm dev:web    # Frontend
pnpm dev:api    # Backend (needs venv activated)

# Backend setup
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
cd apps/api && pytest tests/ -v
```

## Environment Variables

**Frontend (`apps/web/.env`):**
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`
- `VITE_API_URL` (default: http://localhost:8000)

**Backend (`apps/api/.env`):**
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`

## Current Status
- Auth flow working with Supabase
- Onboarding flow implemented (4-step profile setup)
- Dashboard placeholder ready for workout logging
- Core infrastructure in place

## Onboarding Flow
- **Route**: `/onboarding` (after login, before dashboard access)
- **Steps**: Basic Info → Physical Stats → Fitness Profile → Schedule
- **Route Guard**: `<OnboardingRoute>` redirects incomplete profiles to onboarding
- **API**: `GET /profile/me`, `POST /profile/onboarding`

## Next Steps (Workout Logger)
Features to implement:
1. **Workout logging** - Log exercises, sets, reps, weight
2. **Progress tracking** - Historical data visualization
3. **AI insights** - Trend analysis and recommendations

Database tables needed:
- `workouts` - workout sessions (user_id, date, notes)
- `exercises` - exercise definitions (name, muscle_group)
- `workout_sets` - individual sets (workout_id, exercise_id, reps, weight)
