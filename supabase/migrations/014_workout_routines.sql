-- Workout Routines (Templates)
-- Creates routines, routine_exercises, routine_sets tables with indexes and RLS.

-- =============================================================================
-- 1. Routines — reusable workout templates
-- =============================================================================
CREATE TABLE routines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    last_used_at TIMESTAMPTZ,
    use_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX routines_user_recency_idx ON routines(user_id, last_used_at DESC NULLS LAST);

-- =============================================================================
-- 2. Routine Exercises — exercises within a routine template
-- =============================================================================
CREATE TABLE routine_exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    routine_id UUID NOT NULL REFERENCES routines(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES exercises(id),
    sort_order INTEGER NOT NULL,
    rest_timer_seconds INTEGER,
    notes TEXT
);

CREATE INDEX routine_exercises_routine_idx ON routine_exercises(routine_id);

-- =============================================================================
-- 3. Routine Sets — target sets within a routine exercise
-- =============================================================================
CREATE TABLE routine_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    routine_exercise_id UUID NOT NULL REFERENCES routine_exercises(id) ON DELETE CASCADE,
    set_number INTEGER NOT NULL,
    target_reps INTEGER,
    set_type TEXT DEFAULT 'normal' CHECK (
        set_type IN ('normal', 'warmup', 'dropset', 'failure')
    )
);

CREATE INDEX routine_sets_exercise_idx ON routine_sets(routine_exercise_id);

-- =============================================================================
-- 4. RLS Policies
-- =============================================================================

-- Routines: full CRUD where user_id = auth.uid()
ALTER TABLE routines ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read their own routines"
    ON routines FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own routines"
    ON routines FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own routines"
    ON routines FOR UPDATE TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own routines"
    ON routines FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- Routine Exercises: CRUD via parent routine ownership
ALTER TABLE routine_exercises ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read exercises in their routines"
    ON routine_exercises FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM routines
        WHERE routines.id = routine_exercises.routine_id
        AND routines.user_id = auth.uid()
    ));

CREATE POLICY "Users can add exercises to their routines"
    ON routine_exercises FOR INSERT TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM routines
        WHERE routines.id = routine_exercises.routine_id
        AND routines.user_id = auth.uid()
    ));

CREATE POLICY "Users can update exercises in their routines"
    ON routine_exercises FOR UPDATE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM routines
        WHERE routines.id = routine_exercises.routine_id
        AND routines.user_id = auth.uid()
    ));

CREATE POLICY "Users can delete exercises from their routines"
    ON routine_exercises FOR DELETE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM routines
        WHERE routines.id = routine_exercises.routine_id
        AND routines.user_id = auth.uid()
    ));

-- Routine Sets: CRUD via grandparent routine ownership
ALTER TABLE routine_sets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read sets in their routines"
    ON routine_sets FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM routine_exercises re
        JOIN routines r ON r.id = re.routine_id
        WHERE re.id = routine_sets.routine_exercise_id
        AND r.user_id = auth.uid()
    ));

CREATE POLICY "Users can add sets to their routines"
    ON routine_sets FOR INSERT TO authenticated
    WITH CHECK (EXISTS (
        SELECT 1 FROM routine_exercises re
        JOIN routines r ON r.id = re.routine_id
        WHERE re.id = routine_sets.routine_exercise_id
        AND r.user_id = auth.uid()
    ));

CREATE POLICY "Users can update sets in their routines"
    ON routine_sets FOR UPDATE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM routine_exercises re
        JOIN routines r ON r.id = re.routine_id
        WHERE re.id = routine_sets.routine_exercise_id
        AND r.user_id = auth.uid()
    ));

CREATE POLICY "Users can delete sets from their routines"
    ON routine_sets FOR DELETE TO authenticated
    USING (EXISTS (
        SELECT 1 FROM routine_exercises re
        JOIN routines r ON r.id = re.routine_id
        WHERE re.id = routine_sets.routine_exercise_id
        AND r.user_id = auth.uid()
    ));
