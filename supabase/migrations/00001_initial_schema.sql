-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Profiles table (extends Supabase auth.users)
create table profiles (
  id uuid references auth.users on delete cascade primary key,
  username text unique,
  created_at timestamp with time zone default now() not null
);

-- Enable Row Level Security
alter table profiles enable row level security;

-- Profiles policies
create policy "Users can view own profile"
  on profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on profiles for update
  using (auth.uid() = id);

-- Trigger to create profile on user signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id)
  values (new.id);
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Videos table
create table videos (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references profiles(id) on delete cascade not null,
  storage_path text not null,
  exercise_type text not null check (exercise_type in ('squat', 'bench', 'deadlift')),
  duration_seconds integer,
  uploaded_at timestamp with time zone default now() not null
);

-- Enable Row Level Security
alter table videos enable row level security;

-- Videos policies
create policy "Users can view own videos"
  on videos for select
  using (auth.uid() = user_id);

create policy "Users can insert own videos"
  on videos for insert
  with check (auth.uid() = user_id);

create policy "Users can delete own videos"
  on videos for delete
  using (auth.uid() = user_id);

-- Create index for faster queries
create index idx_videos_user_id on videos(user_id);
create index idx_videos_uploaded_at on videos(uploaded_at desc);

-- Analyses table
create table analyses (
  id uuid primary key default uuid_generate_v4(),
  video_id uuid references videos(id) on delete cascade not null,
  technique_score integer not null check (technique_score >= 0 and technique_score <= 100),
  issues jsonb not null default '[]',
  bar_path jsonb,
  landmarks_data jsonb,
  processed_at timestamp with time zone default now() not null
);

-- Enable Row Level Security
alter table analyses enable row level security;

-- Analyses policies (users can view analyses for their own videos)
create policy "Users can view own analyses"
  on analyses for select
  using (
    exists (
      select 1 from videos
      where videos.id = analyses.video_id
      and videos.user_id = auth.uid()
    )
  );

create policy "Service role can insert analyses"
  on analyses for insert
  with check (true);

-- Create index for faster queries
create index idx_analyses_video_id on analyses(video_id);
create index idx_analyses_processed_at on analyses(processed_at desc);

-- Storage bucket for videos (run this in Supabase dashboard or via API)
-- insert into storage.buckets (id, name, public)
-- values ('videos', 'videos', true);

-- Storage policies would be set up in Supabase dashboard
