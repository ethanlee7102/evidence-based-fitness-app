-- Lock the is_demo flag against user writes.
--
-- The demo SELECT policy (017) exposes any workout with is_demo = true to every
-- anonymous guest. The original workouts INSERT/UPDATE policies (011) only check
-- user_id, so a guest could hit PostgREST directly (with the public anon key +
-- their JWT, bypassing the backend) and insert/flag an is_demo = true workout -
-- which would then appear in every other guest's demo view (content injection /
-- pollution). Only the service-role seed script (which bypasses RLS) may set
-- is_demo. Mirrors how exercises already forbids user-set is_global = true.
--
-- Fix: require is_demo = false in the WITH CHECK of both policies. Normal writes
-- are unaffected (is_demo defaults to false); flipping it to true is refused.

drop policy if exists "Users can create their own workouts" on workouts;
create policy "Users can create their own workouts"
    on workouts for insert
    to authenticated
    with check (auth.uid() = user_id and is_demo = false);

drop policy if exists "Users can update their own workouts" on workouts;
create policy "Users can update their own workouts"
    on workouts for update
    to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id and is_demo = false);
