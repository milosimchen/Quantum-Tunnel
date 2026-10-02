-- Run once in Supabase: SQL Editor -> New query -> paste -> Run.
-- Adds the career path a user picks on the "Your path" page.
alter table public.profiles add column if not exists career_path text
  check (career_path in ('software', 'hardware', 'research', 'business'));
