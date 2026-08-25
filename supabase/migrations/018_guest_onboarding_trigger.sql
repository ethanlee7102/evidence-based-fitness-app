-- Guest onboarding bypass.
--
-- The handle_new_user trigger (initial schema) creates a profiles row for every
-- new auth user with onboarding_completed = false, which would trap an anonymous
-- guest in the 4-step onboarding form. This extends it: anonymous users get a
-- profile that's already complete, with demo-friendly defaults (values chosen to
-- satisfy the 004 CHECK constraints, or the whole guest sign-in transaction would
-- fail). The registered-user branch is unchanged.
--
-- search_path = '' hardens the SECURITY DEFINER function against search-path
-- hijacking; all references are schema-qualified.

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.is_anonymous then
    insert into public.profiles (
      id, display_name, experience_level, goal,
      onboarding_completed, onboarding_completed_at
    )
    values (
      new.id, 'Guest Lifter', 'intermediate', 'build_muscle',
      true, now()
    );
  else
    insert into public.profiles (id)
    values (new.id);
  end if;
  return new;
end;
$$;
