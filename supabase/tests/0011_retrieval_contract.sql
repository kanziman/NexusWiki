-- Transactional retrieval contract. Run only against a reset local Supabase stack.
--
-- This is deliberately a direct-query EXPLAIN contract. PostgreSQL may show a
-- Function Scan for EXPLAIN SELECT * FROM a public RPC, which cannot prove the
-- function's internal HNSW plan. The direct queries below instead reproduce the
-- deployed RPCs' authenticated/RLS context, workspace/non-null predicates,
-- <=> ordering, clamped limit, and function-local HNSW settings.
--
-- The 25,000 target + 25,000 foreign rows per relation are intentionally much
-- larger than the representative corpus: the workspace predicate is selective
-- enough to make the local pgvector cost model choose the deployed HNSW index
-- without disabling sequential scans or forcing any planner path. All fixtures,
-- roles, and SET LOCAL values disappear at rollback.
\if :{?retrieval_contract_preflight_only}
  \set retrieval_contract_fixture false
\else
  \set retrieval_contract_fixture true
\endif

begin;

create or replace function pg_temp.walk_plan_has_index(p_plan jsonb, p_index text)
returns boolean language sql immutable as $$
  with recursive nodes(node) as (
    select p_plan -> 0 -> 'Plan'
    union all
    select child.value
      from nodes
      cross join lateral jsonb_array_elements(coalesce(nodes.node -> 'Plans', '[]'::jsonb)) child
  )
  select exists (
    select 1 from nodes
     where node ->> 'Index Name' = p_index
       and node ->> 'Node Type' in ('Index Scan', 'Index Only Scan', 'Bitmap Index Scan')
  );
$$;

-- Plan 07 loads its own deterministic labelled-plus-decoy data, then sources
-- this file in the same psql session and calls this preflight before every arm.
-- It creates no rows and never rolls data back; it only verifies that the caller
-- supplied the exact manifest identity and relation cardinalities.
create or replace function pg_temp.retrieval_contract_preflight(
  p_workspace_id uuid,
  p_manifest_identity text,
  p_expected_source_rows integer,
  p_expected_wiki_rows integer
) returns void language plpgsql as $preflight$
declare
  v_source_rows integer;
  v_wiki_rows integer;
  v_source_plan jsonb;
  v_wiki_plan jsonb;
  v_query text;
  v_expected_source_index text := 'source_chunks_embedding_idx';
  v_expected_wiki_index text := 'wiki_embeddings_embedding_idx';
begin
  select count(*) into v_source_rows from public.source_chunks where workspace_id = p_workspace_id;
  select count(*) into v_wiki_rows from public.wiki_embeddings where workspace_id = p_workspace_id;
  if v_source_rows <> p_expected_source_rows or v_wiki_rows <> p_expected_wiki_rows then
    raise exception 'retrieval preflight manifest % expected source/wiki %/%, observed %/%',
      p_manifest_identity, p_expected_source_rows, p_expected_wiki_rows, v_source_rows, v_wiki_rows;
  end if;
  if not exists (
    select 1 from public.raw_sources
     where workspace_id = p_workspace_id and content_hash = p_manifest_identity
  ) then
    raise exception 'retrieval preflight missing manifest identity % in workspace %', p_manifest_identity, p_workspace_id;
  end if;

  set local hnsw.iterative_scan = 'strict_order';
  set local hnsw.ef_search = '200';
  set local hnsw.max_scan_tuples = '40000';

  v_query := format(
    'explain (format json) select c.id from public.source_chunks c where c.workspace_id = %L::uuid and c.embedding is not null order by c.embedding operator(extensions.<=>) %L::extensions.vector(1024) limit least(greatest(%s, 1), 100)',
    p_workspace_id, '[' || repeat('0.001,', 1023) || '0.001]', 20
  );
  execute v_query into v_source_plan;
  if not pg_temp.walk_plan_has_index(v_source_plan, v_expected_source_index) then
    raise exception 'missing HNSW index %; observed source plan: %', v_expected_source_index, v_source_plan;
  end if;

  v_query := format(
    'explain (format json) select e.id from public.wiki_embeddings e where e.workspace_id = %L::uuid and e.embedding is not null order by e.embedding operator(extensions.<=>) %L::extensions.vector(1024) limit least(greatest(%s, 1), 100)',
    p_workspace_id, '[' || repeat('0.001,', 1023) || '0.001]', 20
  );
  execute v_query into v_wiki_plan;
  if not pg_temp.walk_plan_has_index(v_wiki_plan, v_expected_wiki_index) then
    raise exception 'missing HNSW index %; observed wiki plan: %', v_expected_wiki_index, v_wiki_plan;
  end if;
end
$preflight$;

do $catalog$
declare
  v_name text;
  v_oid oid;
  v_vol "char";
  v_secdef boolean;
  v_config text[];
  v_source text;
begin
  foreach v_name in array array['search_chunks', 'search_wiki_embeddings'] loop
    select p.oid, p.provolatile, p.prosecdef, coalesce(p.proconfig, array[]::text[]), p.prosrc
      into v_oid, v_vol, v_secdef, v_config, v_source
      from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public' and p.proname = v_name;
    if v_oid is null or v_vol <> 's' or v_secdef
       or not has_function_privilege('authenticated', v_oid, 'execute')
       or has_function_privilege('anon', v_oid, 'execute')
       or has_function_privilege('service_role', v_oid, 'execute')
       or not (v_config @> array['search_path=public', 'hnsw.iterative_scan=strict_order', 'hnsw.ef_search=200', 'hnsw.max_scan_tuples=40000']) then
      raise exception '% must be authenticated-only SECURITY INVOKER STABLE with deployed HNSW GUCs', v_name;
    end if;
    if v_source not like '%workspace_id = p_workspace_id%'
       or v_source not like '%embedding is not null%'
       or v_source not like '%operator(extensions.<=>)%'
       or v_source not like '%least(greatest(p_k, 1), 100)%' then
      raise exception '% body no longer matches direct-plan predicate/order/limit contract', v_name;
    end if;
  end loop;
end
$catalog$;

\if :retrieval_contract_fixture
-- Fixed UUIDs make failures reproducible. A dedicated member is inserted before
-- SET LOCAL ROLE so the actual observation executes under authenticated + JWT
-- claims and therefore RLS, never as postgres/service_role.
insert into auth.users (id, email) values
  ('10000000-0000-0000-0000-000000000116', 'retrieval-plan@example.test'),
  ('10000000-0000-0000-0000-000000000117', 'retrieval-decoy@example.test');
insert into public.workspaces (id, name, owner_id) values
  ('20000000-0000-0000-0000-000000000116', 'retrieval HNSW fixture', '10000000-0000-0000-0000-000000000116'),
  ('20000000-0000-0000-0000-000000000117', 'retrieval HNSW decoy', '10000000-0000-0000-0000-000000000117');
insert into public.raw_sources (id, workspace_id, created_by, title, source_type, content, content_hash) values
  ('40000000-0000-0000-0000-000000000116', '20000000-0000-0000-0000-000000000116', '10000000-0000-0000-0000-000000000116', 'fixture', 'text', 'fixture', 'retrieval-contract-v1'),
  ('40000000-0000-0000-0000-000000000117', '20000000-0000-0000-0000-000000000117', '10000000-0000-0000-0000-000000000117', 'decoy', 'text', 'decoy', 'retrieval-contract-decoy-v1');
insert into public.wiki_pages (id, workspace_id, created_by, slug, title, category, content) values
  ('50000000-0000-0000-0000-000000000116', '20000000-0000-0000-0000-000000000116', '10000000-0000-0000-0000-000000000116', 'fixture', 'fixture', 'concepts', 'fixture'),
  ('50000000-0000-0000-0000-000000000117', '20000000-0000-0000-0000-000000000117', '10000000-0000-0000-0000-000000000117', 'decoy', 'decoy', 'concepts', 'decoy');

-- Deterministic valid 1024-dimensional vectors. 25k rows in each target and
-- decoy relation give 50k rows per vector table while keeping fixtures local.
insert into public.source_chunks (raw_source_id, workspace_id, chunk_index, content, char_start, char_end, embedding)
with deterministic_vector as (
  select ('[' || repeat('0.001,', 1023) || '0.001]')::extensions.vector(1024) as embedding
)
select case when n < 25000 then '40000000-0000-0000-0000-000000000116'::uuid else '40000000-0000-0000-0000-000000000117'::uuid end,
       case when n < 25000 then '20000000-0000-0000-0000-000000000116'::uuid else '20000000-0000-0000-0000-000000000117'::uuid end,
       n % 25000, 'chunk ' || n, n, n + 1,
       deterministic_vector.embedding
  from generate_series(0, 49999) g(n) cross join deterministic_vector;
insert into public.wiki_embeddings (wiki_id, workspace_id, chunk_index, chunk_content, embedding)
with deterministic_vector as (
  select ('[' || repeat('0.002,', 1023) || '0.002]')::extensions.vector(1024) as embedding
)
select case when n < 25000 then '50000000-0000-0000-0000-000000000116'::uuid else '50000000-0000-0000-0000-000000000117'::uuid end,
       case when n < 25000 then '20000000-0000-0000-0000-000000000116'::uuid else '20000000-0000-0000-0000-000000000117'::uuid end,
       n % 25000, 'wiki ' || n,
       deterministic_vector.embedding
  from generate_series(0, 49999) g(n) cross join deterministic_vector;
analyze public.source_chunks;
analyze public.wiki_embeddings;

set local role authenticated;
set local request.jwt.claims = '{"sub":"10000000-0000-0000-0000-000000000116","role":"authenticated"}';
select pg_temp.retrieval_contract_preflight(
  '20000000-0000-0000-0000-000000000116', 'retrieval-contract-v1', 25000, 25000
);
reset role;

select 'retrieval_contract: ok';
rollback;
\else
-- Preflight mode is for an already-loaded caller dataset. It deliberately does
-- not seed or roll back that dataset; caller owns its surrounding transaction.
select 'retrieval_contract: preflight loaded';
\endif
