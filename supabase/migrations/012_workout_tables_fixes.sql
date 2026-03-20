-- Workout tables fixes from code review
-- Adds CHECK constraint on exercises and INSERT policy on exercise_muscles

-- Ensure user exercises always have created_by set
ALTER TABLE exercises ADD CONSTRAINT exercises_created_by_check
    CHECK (is_global = true OR created_by IS NOT NULL);

-- Allow users to add muscle mappings for their own exercises
CREATE POLICY "Users can add muscles to their own exercises"
    ON exercise_muscles FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM exercises
            WHERE exercises.id = exercise_muscles.exercise_id
            AND exercises.created_by = auth.uid()
        )
    );
