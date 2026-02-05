-- Flame Fitness Initial Schema
-- Run this in Supabase SQL Editor

-- Profiles table (extends Supabase Auth users)
create table if not exists profiles (
  id uuid references auth.users on delete cascade primary key,
  username text unique,
  created_at timestamp with time zone default now()
);

-- Enable RLS on profiles
alter table profiles enable row level security;

-- Users can read/update their own profile
create policy "Users can view own profile"
  on profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on profiles for update
  using (auth.uid() = id);

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id)
  values (new.id);
  return new;
end;
$$ language plpgsql security definer;

create or replace trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Videos table
create table if not exists videos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade not null,
  storage_path text not null,
  exercise_type text not null check (exercise_type in ('squat', 'bench', 'deadlift')),
  duration_seconds integer,
  uploaded_at timestamp with time zone default now()
);

-- Enable RLS on videos
alter table videos enable row level security;

-- Users can only access their own videos
create policy "Users can view own videos"
  on videos for select
  using (auth.uid() = user_id);

create policy "Users can insert own videos"
  on videos for insert
  with check (auth.uid() = user_id);

create policy "Users can delete own videos"
  on videos for delete
  using (auth.uid() = user_id);

-- Analyses table
create table if not exists analyses (
  id uuid primary key default gen_random_uuid(),
  video_id uuid references videos(id) on delete cascade not null,
  technique_score integer check (technique_score >= 0 and technique_score <= 100),
  issues jsonb default '[]'::jsonb,
  bar_path_data jsonb,
  landmarks_data jsonb,
  processed_at timestamp with time zone default now()
);

-- Enable RLS on analyses
alter table analyses enable row level security;

-- Users can only access analyses for their own videos
create policy "Users can view own analyses"
  on analyses for select
  using (
    exists (
      select 1 from videos
      where videos.id = analyses.video_id
      and videos.user_id = auth.uid()
    )
  );

create policy "Users can insert analyses for own videos"
  on analyses for insert
  with check (
    exists (
      select 1 from videos
      where videos.id = analyses.video_id
      and videos.user_id = auth.uid()
    )
  );

-- Create storage bucket for videos
insert into storage.buckets (id, name, public)
values ('videos', 'videos', true)
on conflict (id) do nothing;

-- Storage policies for videos bucket
create policy "Users can upload videos"
  on storage.objects for insert
  with check (
    bucket_id = 'videos'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

create policy "Users can view own videos"
  on storage.objects for select
  using (
    bucket_id = 'videos'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

create policy "Public can view videos"
  on storage.objects for select
  using (bucket_id = 'videos');

create policy "Users can delete own videos"
  on storage.objects for delete
  using (
    bucket_id = 'videos'
    and auth.uid()::text = (storage.foldername(name))[1]
  );
