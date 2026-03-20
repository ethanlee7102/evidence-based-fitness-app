-- Workout Logging Tables
-- Creates muscle_groups, exercises, exercise_muscles, workouts,
-- workout_exercises, and workout_sets tables with indexes and RLS.

-- =============================================================================
-- 1. Muscle Groups — reference table (23 rows, seeded via script)
-- =============================================================================
CREATE TABLE muscle_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    display_order INTEGER NOT NULL
);

-- =============================================================================
-- 2. Exercises — global library + user-created custom exercises
-- =============================================================================
CREATE TABLE exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    aliases TEXT[] DEFAULT '{}',
    equipment TEXT CHECK (equipment IN (
        'barbell', 'dumbbell', 'cable', 'machine', 'bodyweight',
        'band', 'kettlebell', 'other'
    )),
    movement_pattern TEXT CHECK (movement_pattern IN (
        'push', 'pull', 'squat', 'hinge', 'carry', 'isolation', 'other'
    )),
    force_type TEXT CHECK (force_type IN ('push', 'pull', 'static')),
    body_region TEXT CHECK (body_region IN ('upper', 'lower', 'full')),
    laterality TEXT DEFAULT 'bilateral' CHECK (laterality IN ('bilateral', 'unilateral')),
    is_compound BOOLEAN DEFAULT true,
    instructions TEXT[] DEFAULT '{}',
    video_url TEXT,
    is_global BOOLEAN NOT NULL DEFAULT false,
    created_by UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Global exercises: name must be unique
CREATE UNIQUE INDEX exercises_global_name_idx ON exercises (lower(name)) WHERE is_global = true;
-- User exercises: name must be unique per user
CREATE UNIQUE INDEX exercises_user_name_idx ON exercises (created_by, lower(name)) WHERE is_global = false;

-- =============================================================================
-- 3. Exercise Muscles — junction table (composite PK)
-- =============================================================================
CREATE TABLE exercise_muscles (
    exercise_id UUID NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    muscle_group_id UUID NOT NULL REFERENCES muscle_groups(id) ON DELETE CASCADE,
    activation_level TEXT NOT NULL DEFAULT 'medium' CHECK (
        activation_level IN ('maximum', 'high', 'medium', 'partial')
    ),
    PRIMARY KEY (exercise_id, muscle_group_id)
);

-- =============================================================================
-- 4. Workouts — one row per workout session
-- =============================================================================
CREATE TABLE workouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    body_weight_kg NUMERIC,
    rating SMALLINT CHECK (rating >= 1 AND rating <= 5),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX workouts_user_started_idx ON workouts(user_id, started_at DESC);

-- =============================================================================
-- 5. Workout Exercises — orders exercises within a workout
-- =============================================================================
CREATE TABLE workout_exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workout_id UUID NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES exercises(id),
    sort_order INTEGER NOT NULL,
    superset_group INTEGER,
    rest_timer_seconds INTEGER,
    notes TEXT
);

CREATE INDEX workout_exercises_workout_idx ON workout_exercises(workout_id);

-- =============================================================================
-- 6. Workout Sets — individual sets within a workout exercise
-- =============================================================================
CREATE TABLE workout_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workout_exercise_id UUID NOT NULL REFERENCES workout_exercises(id) ON DELETE CASCADE,
    set_number INTEGER NOT NULL,
    weight_kg NUMERIC,
    reps INTEGER,
    rpe NUMERIC CHECK (rpe >= 1 AND rpe <= 10),
    set_type TEXT DEFAULT 'normal' CHECK (
        set_type IN ('normal', 'warmup', 'dropset', 'failure')
    ),
    duration_seconds INTEGER,
    rest_seconds INTEGER,
    is_to_failure BOOLEAN DEFAULT false,
    completed BOOLEAN DEFAULT false,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX workout_sets_exercise_idx ON workout_sets(workout_exercise_id);

-- =============================================================================
-- 7. RLS Policies
-- =============================================================================

-- Muscle Groups: public read for authenticated users
ALTER TABLE muscle_groups ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Muscle groups are readable by all authenticated users"
    ON muscle_groups FOR SELECT
    TO authenticated
    USING (true);

-- Exercises: read global + own; write only own non-global
ALTER TABLE exercises ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read global and own exercises"
    ON exercises FOR SELECT
    TO authenticated
    USING (is_global = true OR created_by = auth.uid());

CREATE POLICY "Users can create their own exercises"
    ON exercises FOR INSERT
    TO authenticated
    WITH CHECK (is_global = false AND created_by = auth.uid());

CREATE POLICY "Users can update their own exercises"
    ON exercises FOR UPDATE
    TO authenticated
    USING (is_global = false AND created_by = auth.uid());

CREATE POLICY "Users can delete their own exercises"
    ON exercises FOR DELETE
    TO authenticated
    USING (is_global = false AND created_by = auth.uid());

-- Exercise Muscles: public read (same as exercises)
ALTER TABLE exercise_muscles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Exercise muscles are readable by all authenticated users"
    ON exercise_muscles FOR SELECT
    TO authenticated
    USING (true);

-- Workouts: full CRUD where user_id = auth.uid()
ALTER TABLE workouts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read their own workouts"
    ON workouts FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own workouts"
    ON workouts FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own workouts"
    ON workouts FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own workouts"
    ON workouts FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- Workout Exercises: CRUD via parent workout ownership
ALTER TABLE workout_exercises ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read exercises in their workouts"
    ON workout_exercises FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM workouts
            WHERE workouts.id = workout_exercises.workout_id
            AND workouts.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can add exercises to their workouts"
    ON workout_exercises FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM workouts
            WHERE workouts.id = workout_exercises.workout_id
            AND workouts.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update exercises in their workouts"
    ON workout_exercises FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM workouts
            WHERE workouts.id = workout_exercises.workout_id
            AND workouts.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete exercises from their workouts"
    ON workout_exercises FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM workouts
            WHERE workouts.id = workout_exercises.workout_id
            AND workouts.user_id = auth.uid()
        )
    );

-- Workout Sets: CRUD via grandparent workout ownership
ALTER TABLE workout_sets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read sets in their workouts"
    ON workout_sets FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM workout_exercises we
            JOIN workouts w ON w.id = we.workout_id
            WHERE we.id = workout_sets.workout_exercise_id
            AND w.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can add sets to their workouts"
    ON workout_sets FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM workout_exercises we
            JOIN workouts w ON w.id = we.workout_id
            WHERE we.id = workout_sets.workout_exercise_id
            AND w.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update sets in their workouts"
    ON workout_sets FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM workout_exercises we
            JOIN workouts w ON w.id = we.workout_id
            WHERE we.id = workout_sets.workout_exercise_id
            AND w.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete sets from their workouts"
    ON workout_sets FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM workout_exercises we
            JOIN workouts w ON w.id = we.workout_id
            WHERE we.id = workout_sets.workout_exercise_id
            AND w.user_id = auth.uid()
        )
    );
