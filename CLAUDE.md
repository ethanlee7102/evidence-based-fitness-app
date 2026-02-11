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
│   │       │   ├── dashboard/    # Layout shell (Sidebar, DashboardLayout)
│   │       │   ├── home/         # Landing page + HomeDashboardScreen
│   │       │   ├── workouts/     # Workout logging + history
│   │       │   ├── analysis/     # AI trends, charts
│   │       │   ├── chat/         # AI assistant
│   │       │   ├── profile/      # User settings
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
- Dashboard with 5-tab sidebar navigation (Home, Workouts, Analysis, Chat, Profile)
- Core infrastructure in place

## Onboarding Flow
- **Route**: `/onboarding` (after login, before dashboard access)
- **Steps**: Basic Info → Physical Stats → Fitness Profile → Schedule
- **Route Guard**: `<OnboardingRoute>` redirects incomplete profiles to onboarding
- **API**: `GET /profile/me`, `POST /profile/onboarding`

## Dashboard Navigation
- **Layout**: `DashboardLayout` with sidebar (desktop) containing 5 tabs
- **Routes**: Nested under `/dashboard` with `<Outlet />`
  - `/dashboard` → redirects to `/dashboard/home`
  - `/dashboard/home` → HomeDashboardScreen (welcome, quick stats)
  - `/dashboard/workouts` → WorkoutsScreen (logging + history)
  - `/dashboard/analysis` → AnalysisScreen (AI trends, charts)
  - `/dashboard/chat` → ChatScreen (AI assistant)
  - `/dashboard/profile` → ProfileScreen (user settings)
- **Icons**: Using `lucide-react` (Home, Dumbbell, BarChart3, MessageCircle, User)

## Next Steps (Workout Logger)
Features to implement:
1. **Workout logging** - Log exercises, sets, reps, weight
2. **Progress tracking** - Historical data visualization
3. **AI insights** - Trend analysis and recommendations

Database tables needed:
- `workouts` - workout sessions (user_id, date, notes)
- `exercises` - exercise definitions (name, muscle_group)
- `workout_sets` - individual sets (workout_id, exercise_id, reps, weight)


## AI Chatbot (Exercise Science RAG)
                                                                                                                                                                                                                   
  ### Claude Instructions for AI Features
  - Act as a teacher, explain concepts at beginner level
  - Point out weaknesses and anti-patterns
  - Connect concepts back to this specific project
  - Reference the Kruiz codebase (pet travel chatbot at ~/Desktop/kruiz/data:ai/) as a learning example when relevant

  ### Goal
  The `/dashboard/chat` route will be an AI chatbot that:
  - v1: Answers exercise science questions with cited research literature (Simple RAG)
  - v2: Also analyzes user workout data from this app (volume, PRs, trends) using Agentic RAG with a router

  ### Architecture Decisions
  - v1: Simple RAG — papers only, no agents needed
  - v2: Agentic RAG with router (literature path + workout data path)
  - Categories (nutrition, hypertrophy, strength) handled via metadata tags, not separate agents
  - Vector search naturally handles topic matching; metadata enables filtering + citations

  ### Learning Progress
  - [x] Big picture overview of RAG
  - [x] Ingestion pipeline walkthrough (with code snippets from Kruiz)
  - [x] Weaknesses in Kruiz codebase identified (9 major ones)
  - [x] Simple RAG vs Agentic RAG distinction
  - [ ] Video study plan provided (9 videos) — watching videos 1-3 first
  - [ ] Embeddings & vector search deep dive
  - [ ] Chunking strategies advanced
  - [ ] Retrieval & re-ranking
  - [ ] Prompt engineering for citations
  - [ ] RAG evaluation
  - [ ] Agents & routing

  ### Video Study Plan
  1. Text embeddings explained visually (15-30m)
  2. Cosine similarity & vector search (15-25m)
  3. RAG end-to-end overview (20-40m)
  4. Chunking strategies compared (15-30m)
  5. Vector databases comparison (15-25m)
  6. Retrieval & re-ranking / hybrid search (15-30m)
  7. Prompt engineering for RAG citations (20-30m)
  8. RAG evaluation with RAGAS (20-30m)
  9. LangGraph agents tutorial (30-45m)

  ### Key Kruiz Weaknesses to Avoid
  1. No chunking strategy — need RecursiveCharacterTextSplitter with overlap
  2. Missing embedding pipeline — build end-to-end: chunk → embed → store
  3. Metadata discarded at retrieval — keep full metadata for citations
  4. No re-ranking — add cross-encoder for v2
  5. Silent error handling — raise errors, don't return empty strings
  6. Raw SQL everywhere — use ORM or vector DB like ChromaDB
  7. Synchronous embedding calls — use async
  8. No embedding versioning — track model version
  9. Delete-and-reinsert pattern — use upserts