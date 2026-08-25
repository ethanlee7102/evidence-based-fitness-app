-- Global daily usage ceiling for the public chat demo.
--
-- A single counter row per UTC day. bump_daily_chat_usage() atomically increments
-- it and reports whether we're still under the cap, so one scripted flood can't
-- run up the LLM/embedding bill no matter how many anonymous identities it rotates
-- through (the per-IP throttle is best-effort; THIS is the hard, un-bypassable cap).

create table public.api_usage_daily (
    day date primary key default current_date,
    chat_requests integer not null default 0
);

-- RLS on, no policies: only the service-role backend (which bypasses RLS) touches
-- this table. anon/authenticated get deny-all (defense in depth).
alter table public.api_usage_daily enable row level security;

-- Atomically bump today's counter IFF still under p_limit. Returns true when the
-- request is allowed (counter incremented), false when the cap is already hit.
-- The ON CONFLICT row lock serializes concurrent callers so exactly p_limit
-- requests succeed per day (race-free). When the WHERE guard blocks the update no
-- row is returned, so the outer COALESCE turns that into an explicit false.
create or replace function public.bump_daily_chat_usage(p_limit integer)
returns boolean
language sql
security definer
set search_path = ''
as $$
    with bumped as (
        insert into public.api_usage_daily (day, chat_requests)
        values (current_date, 1)
        on conflict (day) do update
            set chat_requests = public.api_usage_daily.chat_requests + 1
            where public.api_usage_daily.chat_requests < p_limit
        returning true as allowed
    )
    select coalesce((select allowed from bumped), false);
$$;

-- Only the backend (service_role) should call this.
revoke execute on function public.bump_daily_chat_usage(integer)
    from public, anon, authenticated;
-- ...and keep it explicitly callable by the backend's service role, rather than
-- relying on the default PUBLIC grant that the revoke above removes.
grant execute on function public.bump_daily_chat_usage(integer) to service_role;
