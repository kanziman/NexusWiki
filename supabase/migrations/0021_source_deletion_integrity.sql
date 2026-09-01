-- =============================================================================
-- NexusWiki 0021: 원문 삭제 무결성과 Storage 정리 잡
--
-- 관련 OpenSpec: deletion-integrity-hardening
--
-- ⚠️ 0020은 병렬 진행 중인 workspace BYOK 변경이 예약했다. 번호 충돌을 피하려고
-- 이 변경은 0021을 사용하며, 병합 전 0020이 먼저 main에 들어왔는지 확인해야 한다.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Storage 경로의 원문 UUID 파서
-- -----------------------------------------------------------------------------
create or replace function public.storage_path_source(p_name text)
returns uuid
language sql
immutable
set search_path = public
as $$
  select case
    when p_name ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/[^/]+$'
      then split_part(p_name, '/', 2)::uuid
    else null
  end;
$$;

comment on function public.storage_path_source(text) is
  'UUID/UUID/파일명 경로에서 원문 UUID를 안전하게 반환. Storage 정책 전용.';

grant execute on function public.storage_path_source(text) to authenticated;


-- -----------------------------------------------------------------------------
-- 2. DB 삭제 직후부터 원본 객체 읽기 차단
--
-- Storage 객체는 Postgres FK의 cascade 대상이 아니다. 삭제 RPC가 정리 잡을 남긴 뒤
-- 객체가 잠시 남더라도 대응하는 raw_sources 행이 없으면 멤버가 읽을 수 없어야 한다.
-- INSERT 정책에는 이 조건을 넣지 않는다. 파일 수집은 객체를 먼저 올린 다음 DB 행을
-- 만들기 때문에 넣는 순간 정상 업로드가 전부 거부된다.
-- -----------------------------------------------------------------------------
drop policy if exists sources_objects_select_member on storage.objects;
create policy sources_objects_select_member on storage.objects
  for select to authenticated
  using (
    bucket_id = 'sources'
    and public.is_workspace_member(public.storage_path_workspace(name))
    and exists (
      select 1
      from public.raw_sources r
      where r.workspace_id = public.storage_path_workspace(name)
        and r.id = public.storage_path_source(name)
        and r.storage_path = name
    )
  );


-- -----------------------------------------------------------------------------
-- 3. 원문별 참조 직렬화
--
-- JSONB 참조에는 FK를 직접 걸 수 없다. 삭제와 참조 생산자가 같은 원문별 advisory
-- lock을 먼저 잡고, 생산자는 잠금을 얻은 뒤 원문 존재를 다시 확인한다. 참조가 먼저면
-- 삭제가 기다렸다 409가 되고, 삭제가 먼저면 생산자가 기다렸다 FK와 같은 23503으로
-- 실패한다. 테이블 잠금과 달리 다른 원문·테넌트의 쓰기를 막지 않는다.
-- -----------------------------------------------------------------------------
create or replace function public.lock_raw_source_reference(
  p_workspace_id uuid,
  p_source_id text
)
returns void
language plpgsql
security definer
volatile
set search_path = public
as $fn$
begin
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(p_workspace_id::text || ':' || p_source_id, 0)
  );
end;
$fn$;

create or replace function public.assert_raw_source_reference(
  p_workspace_id uuid,
  p_source_id text
)
returns void
language plpgsql
security definer
volatile
set search_path = public
as $fn$
begin
  -- security definer 조회가 RLS보다 먼저 실행되므로, 사용자 JWT가 있으면 원문을
  -- 보기 전에 멤버십부터 확인한다. 이 순서가 뒤집히면 외부 원문의 존재 여부를
  -- 23503과 뒤이은 RLS 42501의 차이로 열거할 수 있다. service_role과 마이그레이션은
  -- auth.uid()가 없고 BYPASSRLS를 유지하므로 워커 경로는 이 게이트를 건너뛴다.
  if (select auth.uid()) is not null
    and not public.is_workspace_member(p_workspace_id) then
    raise exception '참조할 원문이 존재하지 않는다' using errcode = '23503';
  end if;

  perform public.lock_raw_source_reference(p_workspace_id, p_source_id);
  if not exists (
    select 1
    from public.raw_sources r
    where r.workspace_id = p_workspace_id
      and r.id::text = p_source_id
  ) then
    raise exception '참조할 원문이 존재하지 않는다' using errcode = '23503';
  end if;
end;
$fn$;

create or replace function public.enforce_wiki_source_references()
returns trigger
language plpgsql
security definer
set search_path = public
as $fn$
declare
  v_source_id text;
begin
  if jsonb_typeof(new.sources) <> 'array' then
    raise exception 'wiki_pages.sources는 배열이어야 한다' using errcode = '23514';
  end if;
  for v_source_id in
    select distinct value
    from jsonb_array_elements_text(new.sources) source(value)
    order by value
  loop
    perform public.assert_raw_source_reference(new.workspace_id, v_source_id);
  end loop;
  return new;
end;
$fn$;

drop trigger if exists wiki_pages_source_reference_guard on public.wiki_pages;
create trigger wiki_pages_source_reference_guard
  before insert or update of sources, workspace_id on public.wiki_pages
  for each row execute function public.enforce_wiki_source_references();

create or replace function public.enforce_publication_source_references()
returns trigger
language plpgsql
security definer
set search_path = public
as $fn$
declare
  v_source_id text;
begin
  if jsonb_typeof(new.published_citations) <> 'array' then
    raise exception 'published_citations는 배열이어야 한다' using errcode = '23514';
  end if;
  for v_source_id in
    select distinct citation ->> 'anchor'
    from jsonb_array_elements(new.published_citations) citation
    where citation ->> 'anchor' is not null
    order by citation ->> 'anchor'
  loop
    perform public.assert_raw_source_reference(new.workspace_id, v_source_id);
  end loop;
  return new;
end;
$fn$;

drop trigger if exists wiki_publications_source_reference_guard
  on public.wiki_page_publications;
create trigger wiki_publications_source_reference_guard
  before insert or update of published_citations, workspace_id
  on public.wiki_page_publications
  for each row execute function public.enforce_publication_source_references();

create or replace function public.enforce_ask_source_references()
returns trigger
language plpgsql
security definer
set search_path = public
as $fn$
declare
  v_missing_chunk boolean;
  v_source_id text;
  v_source_ids text[];
begin
  -- BEFORE trigger는 ask_messages의 RLS with check보다 먼저 실행된다. 청크 조회보다
  -- 멤버십 검사를 앞세워 외부 청크와 없는 청크가 같은 오류로 귀결되게 한다.
  if (select auth.uid()) is not null
    and not public.is_workspace_member(new.workspace_id) then
    raise exception '참조할 원문 청크가 존재하지 않는다' using errcode = '23503';
  end if;

  with source_citations as (
    select citation ->> 'id' as chunk_id
    from jsonb_array_elements(
      case
        when jsonb_typeof(new.citations -> 'resolved') = 'array'
          then new.citations -> 'resolved'
        else '[]'::jsonb
      end
    ) citation
    where citation ->> 'kind' = 'source'
  )
  select
    coalesce(bool_or(c.id is null), false),
    coalesce(
      array_agg(distinct c.raw_source_id::text order by c.raw_source_id::text)
        filter (where c.id is not null),
      array[]::text[]
    )
  into v_missing_chunk, v_source_ids
  from source_citations citation
  left join public.source_chunks c
    on c.id::text = citation.chunk_id
    and c.workspace_id = new.workspace_id;

  if v_missing_chunk then
    raise exception '참조할 원문 청크가 존재하지 않는다' using errcode = '23503';
  end if;

  -- 첫 snapshot에서 찾은 원문 집합을 보존해야 한다. 여기서 청크를 다시 조회해
  -- 순회 대상을 만들면 그 사이 삭제가 커밋될 때 반복문이 0회가 되어 잠금과
  -- 재검증을 모두 건너뛴다.
  foreach v_source_id in array v_source_ids
  loop
    perform public.lock_raw_source_reference(new.workspace_id, v_source_id);
  end loop;

  -- 잠금 대기 중 삭제가 먼저 커밋했을 수 있으므로 새 snapshot에서 청크와 원문을
  -- 모두 다시 확인한다. 청크가 다른 원문으로 바뀐 경우도 잠그지 않은 원문을
  -- 참조하게 되므로 실패시킨다.
  with source_citations as (
    select citation ->> 'id' as chunk_id
    from jsonb_array_elements(
      case
        when jsonb_typeof(new.citations -> 'resolved') = 'array'
          then new.citations -> 'resolved'
        else '[]'::jsonb
      end
    ) citation
    where citation ->> 'kind' = 'source'
  )
  select exists (
    select 1
    from source_citations citation
    left join public.source_chunks c
      on c.id::text = citation.chunk_id
      and c.workspace_id = new.workspace_id
    left join public.raw_sources r
      on r.id = c.raw_source_id
      and r.workspace_id = new.workspace_id
    where c.id is null
      or not (c.raw_source_id::text = any(v_source_ids))
      or r.id is null
  ) into v_missing_chunk;

  if v_missing_chunk then
    raise exception '참조할 원문 청크가 존재하지 않는다' using errcode = '23503';
  end if;

  return new;
end;
$fn$;

drop trigger if exists ask_messages_source_reference_guard on public.ask_messages;
create trigger ask_messages_source_reference_guard
  before insert or update of citations, workspace_id on public.ask_messages
  for each row execute function public.enforce_ask_source_references();

create or replace function public.enforce_job_source_reference()
returns trigger
language plpgsql
security definer
set search_path = public
as $fn$
declare
  v_source_id text;
begin
  v_source_id := new.payload ->> 'raw_source_id';
  if v_source_id is not null then
    perform public.assert_raw_source_reference(new.workspace_id, v_source_id);
  end if;
  return new;
end;
$fn$;

drop trigger if exists jobs_source_reference_guard on public.jobs;
create trigger jobs_source_reference_guard
  before insert on public.jobs
  for each row execute function public.enforce_job_source_reference();

revoke all on function public.lock_raw_source_reference(uuid, text)
  from public, anon, authenticated;
revoke all on function public.assert_raw_source_reference(uuid, text)
  from public, anon, authenticated;
revoke all on function public.enforce_wiki_source_references()
  from public, anon, authenticated;
revoke all on function public.enforce_publication_source_references()
  from public, anon, authenticated;
revoke all on function public.enforce_ask_source_references()
  from public, anon, authenticated;
revoke all on function public.enforce_job_source_reference()
  from public, anon, authenticated;


-- -----------------------------------------------------------------------------
-- 4. 참조 보호 + 삭제 + Storage 정리 잡 원자화
--
-- security definer인 이유는 raw_sources 삭제와 jobs 삽입을 한 트랜잭션으로 묶어야
-- 하지만 authenticated에는 jobs INSERT 권한이 없기 때문이다. 따라서 함수 첫머리에서
-- 요청자 역할을 명시적으로 확인하고, 없는 행과 다른 테넌트 행도 같은 42501로 감춘다.
-- -----------------------------------------------------------------------------
create or replace function public.delete_raw_source(
  p_workspace_id uuid,
  p_source_id uuid
)
returns table (
  id uuid,
  workspace_id uuid,
  title text,
  cleanup_queued boolean
)
language plpgsql
security definer
volatile
set search_path = public
as $fn$
declare
  v_source public.raw_sources;
begin
  if not public.has_workspace_role(p_workspace_id, 'owner') then
    raise exception '원문을 삭제할 권한이 없다' using errcode = '42501';
  end if;

  perform public.lock_raw_source_reference(p_workspace_id, p_source_id::text);

  select r.*
  into v_source
  from public.raw_sources r
  where r.id = p_source_id
    and r.workspace_id = p_workspace_id
  for update;

  if not found then
    raise exception '원문을 삭제할 권한이 없다' using errcode = '42501';
  end if;

  -- wiki_pages.sources는 원문 UUID 문자열 배열이다. 여기서 목록을 조용히 줄이면
  -- 검증·공개된 문서가 근거 없이 남으므로 삭제 요청을 거부한다.
  if exists (
    select 1
    from public.wiki_pages w
    where w.workspace_id = p_workspace_id
      and w.sources @> jsonb_build_array(p_source_id::text)
  ) or exists (
    select 1
    from public.wiki_page_publications p
    cross join lateral jsonb_array_elements(
      case
        when jsonb_typeof(p.published_citations) = 'array' then p.published_citations
        else '[]'::jsonb
      end
    ) citation
    where p.workspace_id = p_workspace_id
      and citation ->> 'anchor' = p_source_id::text
  ) or exists (
    select 1
    from public.ask_messages m
    cross join lateral jsonb_array_elements(
      case
        when jsonb_typeof(m.citations -> 'resolved') = 'array'
          then m.citations -> 'resolved'
        else '[]'::jsonb
      end
    ) citation
    where m.workspace_id = p_workspace_id
      and citation ->> 'kind' = 'source'
      and exists (
        select 1
        from public.source_chunks c
        where c.raw_source_id = p_source_id
          and c.workspace_id = p_workspace_id
          and c.id::text = citation ->> 'id'
      )
  ) or exists (
    select 1
    from public.jobs j
    where j.workspace_id = p_workspace_id
      and j.type in ('parse', 'compile', 'link_sync', 'embed', 'conflict_check')
      and j.status in ('queued', 'running', 'failed')
      and coalesce(j.payload ->> 'raw_source_id', j.payload ->> 'target_id') = p_source_id::text
  ) then
    raise exception '원문이 아직 참조되고 있다' using errcode = 'NW409';
  end if;

  if v_source.storage_path is not null then
    if public.storage_path_workspace(v_source.storage_path) is distinct from p_workspace_id
      or public.storage_path_source(v_source.storage_path) is distinct from p_source_id then
      raise exception '원문 Storage 경로가 대상과 일치하지 않는다' using errcode = '22023';
    end if;

    insert into public.jobs (workspace_id, type, payload)
    values (
      p_workspace_id,
      'delete_source_storage',
      jsonb_build_object(
        'target_id', p_source_id::text,
        'raw_source_id', p_source_id::text,
        'storage_path', v_source.storage_path
      )
    )
    on conflict do nothing;
  end if;

  delete from public.raw_sources r
  where r.id = p_source_id
    and r.workspace_id = p_workspace_id;

  return query
  select
    v_source.id,
    v_source.workspace_id,
    v_source.title,
    v_source.storage_path is not null;
end;
$fn$;

comment on function public.delete_raw_source(uuid, uuid) is
  'owner 전용 원문 삭제. 참조나 활성 잡이 있으면 NW409, 아니면 Storage 정리 잡과 DB 삭제를 원자적으로 확정한다.';

revoke all on function public.delete_raw_source(uuid, uuid) from public, anon, service_role;
grant execute on function public.delete_raw_source(uuid, uuid) to authenticated;

notify pgrst, 'reload schema';
