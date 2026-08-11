-- =============================================================================
-- NexusWiki 0011: Hybrid retrieval primitive boundary
--
-- Writers are service-role-only and VOLATILE. Every user retrieval primitive is
-- SECURITY INVOKER/STABLE so the caller JWT and RLS remain the tenant boundary.
-- =============================================================================

begin;

-- Load pgvector before assigning HNSW GUCs in functions below.
select '[1,2,3]'::extensions.vector as pgvector_warmup;

-- -----------------------------------------------------------------------------
-- Lexical materialization. The explicit workspace predicate is required even for
-- service_role: it makes a mismatched caller argument a no-op instead of a write
-- across tenants. These functions are deliberately separate from user searches.
-- -----------------------------------------------------------------------------
create or replace function public.index_source_chunk_lexical(
  p_workspace_id uuid,
  p_source_chunk_id uuid,
  p_bigrams text,
  p_tokenizer_version text
)
returns void
language plpgsql
security invoker
volatile
set search_path = public
as $$
begin
  update public.source_chunks
     set search_tsv = to_tsvector('simple', p_bigrams),
         tsv_tokenizer_version = p_tokenizer_version
   where id = p_source_chunk_id
     and workspace_id = p_workspace_id;
end;
$$;

create or replace function public.index_wiki_page_lexical(
  p_workspace_id uuid,
  p_wiki_id uuid,
  p_bigrams text,
  p_tokenizer_version text
)
returns void
language plpgsql
security invoker
volatile
set search_path = public
as $$
begin
  update public.wiki_pages
     set search_tsv = to_tsvector('simple', p_bigrams),
         tsv_tokenizer_version = p_tokenizer_version
   where id = p_wiki_id
     and workspace_id = p_workspace_id;
end;
$$;

-- -----------------------------------------------------------------------------
-- Authenticated retrieval primitives. p_workspace_id is a query constraint,
-- while RLS decides whether the requesting JWT can observe the rows at all.
-- -----------------------------------------------------------------------------
create or replace function public.search_wiki_embeddings(
  p_workspace_id uuid,
  p_query extensions.vector(1024),
  p_k int default 20
)
returns table (
  id uuid, wiki_id uuid, chunk_index int, chunk_content text, distance double precision
)
language sql
security invoker
stable
set search_path = public
set hnsw.iterative_scan = 'strict_order'
set hnsw.ef_search = '200'
set hnsw.max_scan_tuples = '40000'
as $$
  select e.id, e.wiki_id, e.chunk_index, e.chunk_content,
         (e.embedding operator(extensions.<=>) p_query)::double precision
    from public.wiki_embeddings e
   where e.workspace_id = p_workspace_id
     and e.embedding is not null
   order by e.embedding operator(extensions.<=>) p_query
   limit least(greatest(p_k, 1), 100);
$$;

create or replace function public.search_wiki_lexical(
  p_workspace_id uuid,
  p_bigrams text,
  p_tokenizer_version text,
  p_k int default 20
)
returns table (id uuid, slug text, title text, content text, rank real)
language sql
security invoker
stable
set search_path = public
as $$
  select w.id, w.slug, w.title, w.content,
         ts_rank_cd(w.search_tsv, phraseto_tsquery('simple', p_bigrams)) as rank
    from public.wiki_pages w
   where w.workspace_id = p_workspace_id
     and w.tsv_tokenizer_version = p_tokenizer_version
     and w.search_tsv @@ phraseto_tsquery('simple', p_bigrams)
   order by rank desc, w.id
   limit least(greatest(p_k, 1), 100);
$$;

create or replace function public.search_source_lexical(
  p_workspace_id uuid,
  p_bigrams text,
  p_tokenizer_version text,
  p_k int default 20
)
returns table (id uuid, raw_source_id uuid, chunk_index int, content text, rank real)
language sql
security invoker
stable
set search_path = public
as $$
  select c.id, c.raw_source_id, c.chunk_index, c.content,
         ts_rank_cd(c.search_tsv, phraseto_tsquery('simple', p_bigrams)) as rank
    from public.source_chunks c
   where c.workspace_id = p_workspace_id
     and c.tsv_tokenizer_version = p_tokenizer_version
     and c.search_tsv @@ phraseto_tsquery('simple', p_bigrams)
   order by rank desc, c.id
   limit least(greatest(p_k, 1), 100);
$$;

-- Preserve the previously applied source-vector name while reinstating all
-- retrieval invariants in the final migration that owns the primitive set.
create or replace function public.search_chunks(
  p_workspace_id uuid,
  p_query extensions.vector(1024),
  p_k int default 20
)
returns table (
  id uuid, raw_source_id uuid, chunk_index int, content text, distance double precision
)
language sql
security invoker
stable
set search_path = public
set hnsw.iterative_scan = 'strict_order'
set hnsw.ef_search = '200'
set hnsw.max_scan_tuples = '40000'
as $$
  select c.id, c.raw_source_id, c.chunk_index, c.content,
         (c.embedding operator(extensions.<=>) p_query)::double precision
    from public.source_chunks c
   where c.workspace_id = p_workspace_id
     and c.embedding is not null
   order by c.embedding operator(extensions.<=>) p_query
   limit least(greatest(p_k, 1), 100);
$$;

-- Only fused wiki IDs are accepted as seeds; the graph never turns unresolved
-- slugs into nodes. Recursive expansion is fixed at two hops and each frontier
-- takes at most p_fanout resolved links. The UUID path rejects cycles.
create or replace function public.expand_wiki_graph(
  p_workspace_id uuid,
  p_seed_wiki_ids uuid[],
  p_fanout int default 5,
  p_total_limit int default 50
)
returns table (wiki_id uuid, depth int)
language plpgsql
security invoker
stable
set search_path = public
as $$
begin
  if coalesce(cardinality(p_seed_wiki_ids), 0) > 10 then
    raise exception 'expand_wiki_graph accepts at most 10 seeds' using errcode = '22023';
  end if;
  if p_fanout < 1 or p_fanout > 5 then
    raise exception 'expand_wiki_graph fan-out must be 1..5' using errcode = '22023';
  end if;
  if p_total_limit < 1 or p_total_limit > 50 then
    raise exception 'expand_wiki_graph total limit must be 1..50' using errcode = '22023';
  end if;

  return query
  with recursive seed as (
    select distinct s.wiki_id, 0 as depth, array[s.wiki_id]::uuid[] as path
      from unnest(p_seed_wiki_ids) as s(wiki_id)
      join public.wiki_pages w on w.id = s.wiki_id and w.workspace_id = p_workspace_id
  ), walk as (
    select * from seed
    union all
    select edge.to_wiki_id, walk.depth + 1, walk.path || edge.to_wiki_id
      from walk
      cross join lateral (
        select l.to_wiki_id
          from public.wiki_links l
         where l.workspace_id = p_workspace_id
           and l.from_wiki_id = walk.wiki_id
           and l.resolved
           and l.to_wiki_id is not null
         order by l.to_wiki_id
         limit p_fanout
      ) edge
     where walk.depth < 2
       and not edge.to_wiki_id = any(walk.path)
  )
  select walk.wiki_id, min(walk.depth)::int
    from walk
   group by walk.wiki_id
   order by min(walk.depth), walk.wiki_id
   limit p_total_limit;
end;
$$;

-- Function ACLs are explicit in both directions; pg_default_acl differs between
-- local and cloud projects, so relying on a revoke from public alone is unsafe.
revoke all on function public.index_source_chunk_lexical(uuid, uuid, text, text)
  from public, anon, authenticated;
revoke all on function public.index_wiki_page_lexical(uuid, uuid, text, text)
  from public, anon, authenticated;
grant execute on function public.index_source_chunk_lexical(uuid, uuid, text, text) to service_role;
grant execute on function public.index_wiki_page_lexical(uuid, uuid, text, text) to service_role;

revoke all on function public.search_chunks(uuid, extensions.vector, int)
  from public, anon, service_role;
revoke all on function public.search_wiki_embeddings(uuid, extensions.vector, int)
  from public, anon, service_role;
revoke all on function public.search_wiki_lexical(uuid, text, text, int)
  from public, anon, service_role;
revoke all on function public.search_source_lexical(uuid, text, text, int)
  from public, anon, service_role;
revoke all on function public.expand_wiki_graph(uuid, uuid[], int, int)
  from public, anon, service_role;
grant execute on function public.search_chunks(uuid, extensions.vector, int) to authenticated;
grant execute on function public.search_wiki_embeddings(uuid, extensions.vector, int) to authenticated;
grant execute on function public.search_wiki_lexical(uuid, text, text, int) to authenticated;
grant execute on function public.search_source_lexical(uuid, text, text, int) to authenticated;
grant execute on function public.expand_wiki_graph(uuid, uuid[], int, int) to authenticated;

notify pgrst, 'reload schema';

commit;
