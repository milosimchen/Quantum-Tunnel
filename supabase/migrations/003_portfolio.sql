-- Run once in Supabase: SQL Editor -> New query -> paste -> Run.
-- Public "proof of work" portfolios.

-- The circuit each attempt submitted, so a solution can be re-verified later.
alter table public.practice_attempts add column if not exists gates jsonb;

-- Opt-in public portfolio with a chosen address (quantumtunnel.../u/<slug>).
alter table public.profiles add column if not exists portfolio_public boolean not null default false;
alter table public.profiles add column if not exists portfolio_slug text unique
  check (portfolio_slug ~ '^[a-z0-9][a-z0-9-]{2,39}$');

-- Anyone may read a profile that its owner made public...
drop policy if exists "profiles: public portfolio read" on public.profiles;
create policy "profiles: public portfolio read" on public.profiles
  for select using (portfolio_public);

-- ...and that user's passed attempts. The site never trusts these rows as
-- proof: the public page re-runs every circuit through the grader.
drop policy if exists "practice_attempts: public portfolio read" on public.practice_attempts;
create policy "practice_attempts: public portfolio read" on public.practice_attempts
  for select using (
    passed and exists (
      select 1 from public.profiles p where p.id = practice_attempts.user_id and p.portfolio_public
    )
  );
