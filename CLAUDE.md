# Flame Fitness - Project Context

## Overview
Flame Fitness is an AI-powered form analysis app for the Big 3 lifts (deadlift, squat, bench press). Users upload videos and receive technique scores with identified issues using MMPose/RTMPose pose estimation.

## Tech Stack
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Backend**: Python + FastAPI
- **Database/Auth/Storage**: Supabase (PostgreSQL)
- **ML**: MMPose/RTMPose (ONNX Runtime), OpenCV
- **Monorepo**: pnpm workspaces

## Project Structure

```
flame-fitness/
├── apps/
│   ├── web/                      # React frontend (port 3000)
│   │   └── src/
│   │       ├── features/         # Feature-based modules
│   │       │   ├── auth/         # {components, hooks, screens, services, types}
│   │       │   ├── analysis/     # Results display
│   │       │   ├── upload/       # Video upload flow
│   │       │   └── home/         # Landing page + Flame visualization
│   │       ├── shared/           # Shared UI (Button, Card, Loading, Layout)
│   │       ├── navigation/       # AppRouter, ProtectedRoute
│   │       └── lib/              # supabase.ts, api.ts
│   │
│   └── api/                      # Python backend (port 8000)
│       ├── src/
│       │   ├── api/              # Route handlers (analysis, videos, health)
│       │   ├── core/             # Business logic
│       │   │   ├── pose_estimator.py    # MMPose/RTMPose wrapper (ONNX)
│       │   │   ├── video_processor.py   # Download + frame extraction
│       │   │   ├── angle_calculator.py  # Joint angle math
│       │   │   ├── landmark_postprocessor.py  # Ankle stabilization for deadlifts
│       │   │   └── analyzers/           # DeadliftAnalyzer, SquatAnalyzer, BenchAnalyzer
│       │   ├── schema/           # Pydantic models
│       │   ├── service/          # analysis_service, db_service, storage_service
│       │   ├── utils/            # config, auth, logging
│       │   └── db.py             # Supabase client
│       ├── tests/
│       └── app.py                # FastAPI entry point
│
├── packages/shared/types/        # Shared TypeScript types
└── supabase/migrations/          # Database schema
```

## Key Patterns

### Frontend
- **Feature-based architecture**: Each feature has components/, hooks/, screens/, services/, types/
- **Auth via Supabase**: useAuth hook provides user, session, signIn, signOut
- **API calls**: Use `apiRequest()` from lib/api.ts with JWT token
- **Protected routes**: Wrap with `<ProtectedRoute>` component

### Backend
- **Entry point**: `app.py` (run with `uvicorn app:app`)
- **Auth**: JWT verification via `get_current_user` dependency
- **Analysis flow**:
  1. Download video → `VideoProcessor.download_video()`
  2. Extract landmarks → `PoseEstimator.extract_landmarks(video_path, exercise_type)`
  3. Post-process → `LandmarkPostProcessor.process()` (anchor corrections)
  4. Analyze → `DeadliftAnalyzer/SquatAnalyzer/BenchAnalyzer.analyze()`
- **Analyzers inherit from BaseAnalyzer** with shared `track_bar_path()` method

### Database Tables
- `profiles` - extends Supabase auth.users
- `videos` - uploaded videos (user_id, storage_path, exercise_type)
- `analyses` - results (video_id, technique_score, issues jsonb, bar_path_data jsonb)

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

## Pose Estimation (MMPose/RTMPose)

### Why MMPose over MediaPipe?
- Better occlusion handling (ankles during deadlifts)
- Built-in temporal smoothing (OneEuro filter)
- Faster inference (~50ms CPU vs ~100ms MediaPipe)
- Support for fine-tuning if needed
- Same Apache 2.0 license

### Landmark Indices (MediaPipe-compatible)
Output uses MediaPipe indices for compatibility with analyzers:
- Shoulders: 11, 12
- Elbows: 13, 14
- Wrists: 15, 16 (used for bar path tracking)
- Hips: 23, 24
- Knees: 25, 26
- Ankles: 27, 28

### COCO to MediaPipe Mapping
RTMPose outputs COCO 17-keypoint format, mapped internally:
| Body Part | COCO Index | MediaPipe Index |
|-----------|------------|-----------------|
| Shoulders | 5, 6       | 11, 12          |
| Elbows    | 7, 8       | 13, 14          |
| Wrists    | 9, 10      | 15, 16          |
| Hips      | 11, 12     | 23, 24          |
| Knees     | 13, 14     | 25, 26          |
| Ankles    | 15, 16     | 27, 28          |

**Note**: COCO doesn't provide Z-depth; `z=0.0` for all landmarks.

### Temporal Smoothing (OneEuro Filter)
- Enabled by default to reduce jitter
- Default parameters: `min_cutoff=2.0`, `beta=0.7` (responsive tracking)
- Exercise-specific overrides in `SMOOTHING_OVERRIDES` dict:
  - Deadlift knees (COCO 13, 14): `min_cutoff=0.3`, `beta=0.007` (heavy smoothing for plate occlusion)
- Parameter effects:
  - `min_cutoff`: Lower = more smoothing at rest
  - `beta`: Lower = more lag but smoother tracking
- Can be disabled: `PoseEstimator(use_temporal_smoothing=False)`
- `extract_landmarks(video_path, exercise_type)` accepts exercise type for conditional smoothing

### Model
- **RTMPose-m** (medium): 256x192 input, ~25MB
- Auto-downloaded on first run from OpenMMLab
- Stored at: `apps/api/src/core/rtmpose_m.onnx`

## Analysis Scoring
Each analyzer returns:
- `technique_score`: 0-100 weighted average of component scores
- `issues`: Array of {issue, severity, description, frames?}
- `bar_path`: Array of {x, y, frame} for visualization
- `component_scores`: Individual scores per check

## Current Status
- MVP complete with all three lift analyzers
- Auth flow working with Supabase
- Video upload to Supabase Storage
- Results display with score breakdown and issues list
- **Switched from MediaPipe to MMPose/RTMPose** for better occlusion handling and temporal smoothing
