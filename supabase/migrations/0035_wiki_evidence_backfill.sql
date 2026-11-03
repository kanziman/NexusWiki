-- 기존 본문을 바꾸지 않는 근거 백필. #210, #211, #212
-- 계약: openspec/changes/backfill-wiki-evidence/design.md > D3~D4
begin;

-- 토큰을 DB에서 함께 계산해야 언어별 JSON 직렬화 차이로 정상 검토가 stale이 되지 않는다.
create function public.wiki_evidence_backfill_token(p_row jsonb)
returns text language sql immutable strict set search_path = ''
as $$ select pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(p_row::text, 'UTF8')), 'hex') $$;

-- JSON 한 행 안에 페이지 묶음을 반환해 PostgREST max_rows로 일부 페이지만 잘리지 않게 한다.
create function public.wiki_evidence_backfill_candidates(
  p_workspace_id uuid, p_after_wiki_id uuid default null, p_limit integer default 50
)
returns jsonb language plpgsql stable security invoker set search_path = ''
as $$
declare
  v_pages jsonb;
  v_last uuid;
begin
  if p_workspace_id is null or p_limit is null or p_limit < 1 or p_limit > 50 then
    raise exception 'backfill_invalid_request' using errcode = '22023';
  end if;
  select coalesce(jsonb_agg(item order by id), '[]'::jsonb) into v_pages
  from (
    select w.id, jsonb_build_object(
      'page', to_jsonb(w),
      'page_token', public.wiki_evidence_backfill_token(to_jsonb(w)),
      'chunks', coalesce((
        select jsonb_agg(jsonb_build_object(
          'id', c.id, 'workspace_id', c.workspace_id, 'raw_source_id', c.raw_source_id,
          'chunk_index', c.chunk_index, 'char_start', c.char_start, 'char_end', c.char_end,
          'content', c.content,
          'source_token', public.wiki_evidence_backfill_token(to_jsonb(r)),
          'chunk_token', public.wiki_evidence_backfill_token(jsonb_build_object(
            'id', c.id, 'workspace_id', c.workspace_id, 'raw_source_id', c.raw_source_id,
            'chunk_index', c.chunk_index, 'char_start', c.char_start,
            'char_end', c.char_end, 'content', c.content)),
          'valid_coordinates', coalesce(c.char_start >= 0 and c.char_end > c.char_start
            and c.char_end <= char_length(r.content)
            and substring(r.content from c.char_start + 1 for c.char_end - c.char_start) = c.content, false),
          'already_linked', exists(select 1 from public.wiki_page_evidence e
            where e.workspace_id = p_workspace_id and e.wiki_id = w.id and e.chunk_id = c.id)
        ) order by c.raw_source_id, c.chunk_index, c.id)
        from public.source_chunks c
        join public.raw_sources r on r.id = c.raw_source_id and r.workspace_id = c.workspace_id
        where c.workspace_id = p_workspace_id and w.sources ? c.raw_source_id::text
      ), '[]'::jsonb)
    ) as item
    from public.wiki_pages w
    where w.workspace_id = p_workspace_id and (p_after_wiki_id is null or w.id > p_after_wiki_id)
    order by w.id limit p_limit
  ) pages;
  v_last := (v_pages -> -1 -> 'page' ->> 'id')::uuid;
  return jsonb_build_object('pages', v_pages, 'next_cursor', v_last,
    'has_more', v_last is not null and exists(select 1 from public.wiki_pages w
      where w.workspace_id = p_workspace_id and w.id > v_last));
end;
$$;

create function public.apply_wiki_evidence_backfill(p_workspace_id uuid, p_entries jsonb)
returns jsonb language plpgsql security invoker set search_path = '' set lock_timeout = '5s'
as $$
declare
  v_entry jsonb;
  v_page public.wiki_pages%rowtype;
  v_source public.raw_sources%rowtype;
  v_chunk public.source_chunks%rowtype;
  v_inserted jsonb;
  v_count integer;
begin
  if p_workspace_id is null or jsonb_typeof(p_entries) is distinct from 'array'
    or jsonb_array_length(p_entries) < 1 or jsonb_array_length(p_entries) > 500 then
    raise exception 'backfill_invalid_request' using errcode = '22023';
  end if;
  for v_entry in select value from jsonb_array_elements(p_entries) loop
    if jsonb_typeof(v_entry) is distinct from 'object'
      or coalesce(v_entry ->> 'wiki_id', '') = ''
      or coalesce(v_entry ->> 'raw_source_id', '') = ''
      or coalesce(v_entry ->> 'chunk_id', '') = ''
      or coalesce(v_entry ->> 'page_token', '') !~ '^[0-9a-f]{64}$'
      or coalesce(v_entry ->> 'source_token', '') !~ '^[0-9a-f]{64}$'
      or coalesce(v_entry ->> 'chunk_token', '') !~ '^[0-9a-f]{64}$' then
      raise exception 'backfill_invalid_entry' using errcode = '22023';
    end if;
  end loop;
  select count(distinct ((value ->> 'wiki_id')::uuid, (value ->> 'chunk_id')::uuid)) into v_count
    from jsonb_array_elements(p_entries);
  if v_count <> jsonb_array_length(p_entries) then
    raise exception 'backfill_duplicate_entry' using errcode = '22023';
  end if;

  -- ⚠️ 검증과 삽입이 분리되면 그 사이의 페이지 변경을 놓쳐 낡은 근거를 저장한다.
  -- 원문→페이지→청크, UUID 순서로 잠가 검증부터 INSERT까지 내용과 삭제를 고정한다.
  perform r.id from public.raw_sources r where r.workspace_id = p_workspace_id
    and r.id in (select (value ->> 'raw_source_id')::uuid from jsonb_array_elements(p_entries))
    order by r.id for share;
  perform w.id from public.wiki_pages w where w.workspace_id = p_workspace_id
    and w.id in (select (value ->> 'wiki_id')::uuid from jsonb_array_elements(p_entries))
    order by w.id for share;
  perform c.id from public.source_chunks c where c.workspace_id = p_workspace_id
    and c.id in (select (value ->> 'chunk_id')::uuid from jsonb_array_elements(p_entries))
    order by c.id for share;

  for v_entry in select value from jsonb_array_elements(p_entries) loop
    select * into v_page from public.wiki_pages
      where workspace_id = p_workspace_id and id = (v_entry ->> 'wiki_id')::uuid;
    if not found then
      raise exception 'backfill_scope_or_missing' using errcode = '22023';
    end if;
    select * into v_source from public.raw_sources
      where workspace_id = p_workspace_id and id = (v_entry ->> 'raw_source_id')::uuid;
    if not found then
      raise exception 'backfill_scope_or_missing' using errcode = '22023';
    end if;
    select * into v_chunk from public.source_chunks
      where workspace_id = p_workspace_id and id = (v_entry ->> 'chunk_id')::uuid
        and raw_source_id = v_source.id;
    if not found or not (v_page.sources ? v_source.id::text) then
      raise exception 'backfill_scope_or_missing' using errcode = '22023';
    end if;
    if v_source.content is null or v_chunk.char_start < 0
      or v_chunk.char_end > char_length(v_source.content)
      or substring(v_source.content from v_chunk.char_start + 1
        for v_chunk.char_end - v_chunk.char_start) is distinct from v_chunk.content then
      raise exception 'backfill_invalid_coordinates' using errcode = '22023';
    end if;
    if public.wiki_evidence_backfill_token(to_jsonb(v_page)) <> v_entry ->> 'page_token'
      or public.wiki_evidence_backfill_token(to_jsonb(v_source)) <> v_entry ->> 'source_token'
      or public.wiki_evidence_backfill_token(jsonb_build_object(
        'id', v_chunk.id, 'workspace_id', v_chunk.workspace_id, 'raw_source_id', v_chunk.raw_source_id,
        'chunk_index', v_chunk.chunk_index, 'char_start', v_chunk.char_start,
        'char_end', v_chunk.char_end, 'content', v_chunk.content)) <> v_entry ->> 'chunk_token' then
      raise exception 'backfill_stale' using errcode = '22023';
    end if;
  end loop;

  -- 전체 검증을 통과한 뒤에만 추가한다. 다른 원문의 기존 근거를 DELETE하지 않는다.
  with added as (
    insert into public.wiki_page_evidence(workspace_id, wiki_id, raw_source_id, chunk_id)
    select p_workspace_id, (value ->> 'wiki_id')::uuid,
      (value ->> 'raw_source_id')::uuid, (value ->> 'chunk_id')::uuid
    from jsonb_array_elements(p_entries)
    on conflict (wiki_id, chunk_id) do nothing
    returning wiki_id, raw_source_id, chunk_id
  ) select coalesce(jsonb_agg(to_jsonb(added) order by wiki_id, chunk_id), '[]'::jsonb)
    into v_inserted from added;
  return jsonb_build_object('requested', v_count, 'inserted', jsonb_array_length(v_inserted),
    'existing', v_count - jsonb_array_length(v_inserted), 'inserted_pairs', v_inserted);
exception when invalid_text_representation then
  raise exception 'backfill_invalid_entry' using errcode = '22023';
end;
$$;

revoke all on function public.wiki_evidence_backfill_token(jsonb) from public, anon, authenticated;
revoke all on function public.wiki_evidence_backfill_candidates(uuid, uuid, integer)
  from public, anon, authenticated;
revoke all on function public.apply_wiki_evidence_backfill(uuid, jsonb)
  from public, anon, authenticated;
grant execute on function public.wiki_evidence_backfill_token(jsonb) to service_role;
grant execute on function public.wiki_evidence_backfill_candidates(uuid, uuid, integer) to service_role;
grant execute on function public.apply_wiki_evidence_backfill(uuid, jsonb) to service_role;
notify pgrst, 'reload schema';
commit;
