-- Quantum Studio database schema.
-- Run once in the Supabase dashboard: SQL Editor -> New query -> paste -> Run.
-- Safe to re-run: every statement is idempotent.
--
-- Every table has row-level security (RLS) enabled with policies that only
-- allow a signed-in user to see and change their own rows. The frontend talks
-- to these tables directly with the user's session, so RLS is what keeps one
-- user's data private from another's.

-- ---------------------------------------------------------------------------
-- Profiles: one row per user, created automatically on sign-up.
-- ---------------------------------------------------------------------------
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  experience_level text check (experience_level in ('new', 'some', 'comfortable', 'advanced')),
  goal text check (goal in ('interview', 'coursework', 'research', 'curious')),
  target_role text,
  onboarded boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

drop policy if exists "profiles: read own" on public.profiles;
create policy "profiles: read own" on public.profiles
  for select using (auth.uid() = id);

drop policy if exists "profiles: update own" on public.profiles;
create policy "profiles: update own" on public.profiles
  for update using (auth.uid() = id);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, display_name)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'full_name', split_part(new.email, '@', 1))
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------------
-- Study: which lessons a user has completed.
-- ---------------------------------------------------------------------------
create table if not exists public.lesson_progress (
  user_id uuid not null references auth.users (id) on delete cascade,
  lesson_id text not null,
  completed_at timestamptz not null default now(),
  primary key (user_id, lesson_id)
);

-- ---------------------------------------------------------------------------
-- Interview Prep: every checked practice attempt. The verdict comes from the
-- backend's unitary-equivalence check, never from the LLM.
-- ---------------------------------------------------------------------------
create table if not exists public.practice_attempts (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  challenge_id text not null,
  skill text not null,
  difficulty text not null,
  passed boolean not null,
  gate_count int,
  created_at timestamptz not null default now()
);

create index if not exists practice_attempts_user_idx
  on public.practice_attempts (user_id, created_at desc);

-- ---------------------------------------------------------------------------
-- Jobs: saved listings and where the user is in the process.
-- ---------------------------------------------------------------------------
create table if not exists public.saved_jobs (
  user_id uuid not null references auth.users (id) on delete cascade,
  job_id text not null,
  title text not null,
  company text,
  location text,
  apply_url text,
  description text,
  status text not null default 'saved'
    check (status in ('saved', 'applied', 'interviewing', 'offer', 'closed')),
  notes text,
  saved_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, job_id)
);

-- ---------------------------------------------------------------------------
-- Copilot: one conversation thread per module per user.
-- ---------------------------------------------------------------------------
create table if not exists public.copilot_messages (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  module text not null check (module in ('studio', 'study', 'jobs', 'interview', 'home')),
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamptz not null default now()
);

create index if not exists copilot_messages_thread_idx
  on public.copilot_messages (user_id, module, created_at);

-- ---------------------------------------------------------------------------
-- Owner-only policies for every per-user table above. Written out per table
-- (rather than in a loop) so Supabase's SQL editor can see RLS is enabled.
-- ---------------------------------------------------------------------------
alter table public.lesson_progress enable row level security;
drop policy if exists "lesson_progress: own rows" on public.lesson_progress;
create policy "lesson_progress: own rows" on public.lesson_progress
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

alter table public.practice_attempts enable row level security;
drop policy if exists "practice_attempts: own rows" on public.practice_attempts;
create policy "practice_attempts: own rows" on public.practice_attempts
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

alter table public.saved_jobs enable row level security;
drop policy if exists "saved_jobs: own rows" on public.saved_jobs;
create policy "saved_jobs: own rows" on public.saved_jobs
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

alter table public.copilot_messages enable row level security;
drop policy if exists "copilot_messages: own rows" on public.copilot_messages;
create policy "copilot_messages: own rows" on public.copilot_messages
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- Added for career paths (Oct 2026). Safe to run on an existing project.
-- ---------------------------------------------------------------------------
alter table public.profiles add column if not exists career_path text
  check (career_path in ('software', 'hardware', 'research', 'business'));

-- ---------------------------------------------------------------------------
-- Added for public portfolios (Oct 2026): see migrations/003_portfolio.sql.
-- ---------------------------------------------------------------------------
alter table public.practice_attempts add column if not exists gates jsonb;
alter table public.profiles add column if not exists portfolio_public boolean not null default false;
alter table public.profiles add column if not exists portfolio_slug text unique
  check (portfolio_slug ~ '^[a-z0-9][a-z0-9-]{2,39}$');
drop policy if exists "profiles: public portfolio read" on public.profiles;
create policy "profiles: public portfolio read" on public.profiles
  for select using (portfolio_public);
drop policy if exists "practice_attempts: public portfolio read" on public.practice_attempts;
create policy "practice_attempts: public portfolio read" on public.practice_attempts
  for select using (
    passed and exists (
      select 1 from public.profiles p where p.id = practice_attempts.user_id and p.portfolio_public
    )
  );
