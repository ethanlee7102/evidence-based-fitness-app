-- Hourly cleanup of stale anonymous (guest) users.
--
-- Deleting from auth.users cascades to the guest's profile, workouts, chat
-- sessions, and traces (all FK ON DELETE CASCADE), so a guest's ephemeral data is
-- reaped ~72h after creation. The seeded demo athlete is a NON-anonymous user, so
-- it is never matched. Requires the pg_cron extension (enable in the dashboard:
-- Database -> Extensions -> pg_cron). Schedule from the SQL editor as the postgres
-- role so the job has delete rights on auth.users.

select cron.schedule(
    'cleanup-anon-users',
    '0 * * * *',
    $$
      delete from auth.users
      where is_anonymous = true
        and created_at < now() - interval '72 hours'
    $$
);
