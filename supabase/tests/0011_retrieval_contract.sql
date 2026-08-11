-- Transactional retrieval primitive contract. Run only against the local stack.
begin;

do $contract$
declare
  v_name text;
  v_oid oid;
  v_vol "char";
  v_secdef boolean;
  v_config text[];
begin
  foreach v_name in array array[
    'search_chunks', 'search_wiki_embeddings', 'search_wiki_lexical',
    'search_source_lexical', 'expand_wiki_graph'
  ] loop
    select p.oid, p.provolatile, p.prosecdef, coalesce(p.proconfig, array[]::text[])
      into v_oid, v_vol, v_secdef, v_config
      from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public' and p.proname = v_name;
    if v_oid is null or v_vol <> 's' or v_secdef then
      raise exception '% must be SECURITY INVOKER STABLE', v_name;
    end if;
    if not has_function_privilege('authenticated', v_oid, 'execute')
       or has_function_privilege('anon', v_oid, 'execute')
       or has_function_privilege('service_role', v_oid, 'execute') then
      raise exception '% ACL must be authenticated-only', v_name;
    end if;
    if not (v_config @> array['search_path=public']) then
      raise exception '% must pin search_path', v_name;
    end if;
    if v_name in ('search_chunks', 'search_wiki_embeddings')
       and not (v_config @> array[
         'hnsw.iterative_scan=strict_order', 'hnsw.ef_search=200',
         'hnsw.max_scan_tuples=40000'
       ]) then
      raise exception '% lacks HNSW settings', v_name;
    end if;
  end loop;

  foreach v_name in array array['index_source_chunk_lexical', 'index_wiki_page_lexical'] loop
    select p.oid, p.provolatile, p.prosecdef, coalesce(p.proconfig, array[]::text[])
      into v_oid, v_vol, v_secdef, v_config
      from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public' and p.proname = v_name;
    if v_oid is null or v_vol <> 'v' or v_secdef then
      raise exception '% must be SECURITY INVOKER VOLATILE', v_name;
    end if;
    if not has_function_privilege('service_role', v_oid, 'execute')
       or has_function_privilege('authenticated', v_oid, 'execute')
       or has_function_privilege('anon', v_oid, 'execute') then
      raise exception '% ACL must be service-role-only', v_name;
    end if;
  end loop;
end
$contract$;

-- Boundary-plus-one requests fail before graph traversal; no fixture rows needed.
do $bounds$
declare
  rejected boolean;
  seeds uuid[];
begin
  select array_agg(gen_random_uuid()) into seeds from generate_series(1, 11);
  begin perform * from public.expand_wiki_graph(gen_random_uuid(), seeds, 5, 50); exception when sqlstate '22023' then rejected := true; end;
  if not rejected then raise exception '11 graph seeds were accepted'; end if;
  rejected := false;
  begin perform * from public.expand_wiki_graph(gen_random_uuid(), array[]::uuid[], 6, 50); exception when sqlstate '22023' then rejected := true; end;
  if not rejected then raise exception 'fan-out 6 was accepted'; end if;
  rejected := false;
  begin perform * from public.expand_wiki_graph(gen_random_uuid(), array[]::uuid[], 5, 51); exception when sqlstate '22023' then rejected := true; end;
  if not rejected then raise exception 'total 51 was accepted'; end if;
end
$bounds$;

do $source$
declare v_source text;
begin
  select p.prosrc into v_source from pg_proc p join pg_namespace n on n.oid = p.pronamespace
   where n.nspname = 'public' and p.proname = 'expand_wiki_graph';
  if v_source not like '%walk.depth < 2%'
     or v_source not like '%l.resolved%'
     or v_source not like '%not edge.to_wiki_id = any(walk.path)%' then
    raise exception 'graph recursion safety clauses missing';
  end if;
end
$source$;

select 'retrieval_contract: ok';
rollback;
