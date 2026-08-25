-- Demo workout data exposure.
--
-- A shared, read-only "demo athlete" training history lets anonymous (guest)
-- visitors see a populated app on first load. The seed rows live under a real
-- (non-anonymous) demo user and are flagged is_demo = true. These SELECT policies
-- expose those rows to ANONYMOUS viewers only, on top of the existing own-rows
-- policies (Postgres ORs policies together). Registered users never match the
-- is_anonymous clause, so they never see demo data. Guests can read the seed but
-- cannot write it (no demo INSERT/UPDATE/DELETE policies -> writes still require
-- ownership), which is exactly "add your own, but don't edit the sample."

ALTER TABLE workouts ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT false;

-- Partial index: demo rows are a tiny minority; keeps demo-visibility lookups
-- cheap without bloating the main (user_id, started_at) index.
CREATE INDEX workouts_is_demo_idx ON workouts (is_demo) WHERE is_demo;

-- (select auth.jwt()) is wrapped so it evaluates once per query, not per row.
CREATE POLICY "Anonymous users can read demo workouts"
    ON workouts FOR SELECT
    TO authenticated
    USING (
        is_demo = true
        AND ((select auth.jwt()) ->> 'is_anonymous')::boolean IS TRUE
    );

CREATE POLICY "Anonymous users can read exercises in demo workouts"
    ON workout_exercises FOR SELECT
    TO authenticated
    USING (
        ((select auth.jwt()) ->> 'is_anonymous')::boolean IS TRUE
        AND EXISTS (
            SELECT 1 FROM workouts
            WHERE workouts.id = workout_exercises.workout_id
            AND workouts.is_demo = true
        )
    );

CREATE POLICY "Anonymous users can read sets in demo workouts"
    ON workout_sets FOR SELECT
    TO authenticated
    USING (
        ((select auth.jwt()) ->> 'is_anonymous')::boolean IS TRUE
        AND EXISTS (
            SELECT 1 FROM workout_exercises we
            JOIN workouts w ON w.id = we.workout_id
            WHERE we.id = workout_sets.workout_exercise_id
            AND w.is_demo = true
        )
    );
