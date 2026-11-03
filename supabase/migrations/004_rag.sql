-- Retrieval index for the copilot (see backend/rag.py and backend/ingest_rag.py).
-- Run once in the Supabase dashboard: SQL Editor -> New query -> paste -> Run.
-- Safe to re-run.
--
-- Only the backend reads or writes this table, using the service-role key.
-- RLS is enabled with no policies, so the anon and authenticated roles used by
-- the frontend have no access.

create extension if not exists vector with schema extensions;

create table if not exists public.rag_chunks (
  id text primary key,                         -- "<source>:<doc_id>:<n>"
  source text not null check (source in ('lesson', 'qiskit_docs', 'arxiv')),
  doc_id text not null,
  title text not null,
  section text,
  url text,
  content text not null,
  content_hash text not null,                  -- skip re-embedding unchanged chunks
  embedding extensions.vector(768) not null,   -- gemini-embedding-001 at 768 dimensions
  fts tsvector generated always as (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(section, '')), 'B') ||
    setweight(to_tsvector('english', content), 'C')
  ) stored,
  updated_at timestamptz not null default now()
);

create index if not exists rag_chunks_embedding_idx on public.rag_chunks
  using hnsw (embedding extensions.vector_cosine_ops);
create index if not exists rag_chunks_fts_idx on public.rag_chunks using gin (fts);
create index if not exists rag_chunks_source_idx on public.rag_chunks (source);

alter table public.rag_chunks enable row level security;

-- Hybrid search: rank by cosine similarity and by full-text rank separately,
-- then merge with reciprocal rank fusion (score = sum of 1 / (rrf_k + rank)).
create or replace function public.match_rag_chunks(
  query_embedding extensions.vector(768),
  query_text text,
  match_count int default 6,
  source_filter text[] default null,
  rrf_k int default 60
)
returns table (id text, source text, doc_id text, title text, section text, url text, content text, score double precision)
language sql
stable
set search_path = public, extensions
as $$
  with query as (
    select websearch_to_tsquery('english', coalesce(query_text, '')) as tsq
  ),
  semantic as (
    select c.id, row_number() over (order by c.embedding <=> query_embedding) as rank
    from public.rag_chunks c
    where source_filter is null or c.source = any (source_filter)
    order by c.embedding <=> query_embedding
    limit match_count * 4
  ),
  keyword as (
    select c.id, row_number() over (order by ts_rank_cd(c.fts, q.tsq) desc) as rank
    from public.rag_chunks c, query q
    where c.fts @@ q.tsq and (source_filter is null or c.source = any (source_filter))
    order by ts_rank_cd(c.fts, q.tsq) desc
    limit match_count * 4
  ),
  fused as (
    select coalesce(s.id, k.id) as id,
           coalesce(1.0 / (rrf_k + s.rank), 0) + coalesce(1.0 / (rrf_k + k.rank), 0) as score
    from semantic s
    full outer join keyword k on s.id = k.id
  )
  select c.id, c.source, c.doc_id, c.title, c.section, c.url, c.content, f.score
  from fused f
  join public.rag_chunks c on c.id = f.id
  order by f.score desc
  limit match_count;
$$;

revoke execute on function public.match_rag_chunks(extensions.vector, text, int, text[], int) from public, anon, authenticated;
grant execute on function public.match_rag_chunks(extensions.vector, text, int, text[], int) to service_role;
