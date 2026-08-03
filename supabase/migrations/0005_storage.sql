-- =============================================================================
-- NexusWiki 0005: Storage 버킷 및 경로 강제 정책
--
-- 관련 태스크: P1-STO-01 (소비자는 P2-ING-01 수집 API)
-- 설계 근거:  checklists.json > decisions.original_file_retention
--             01-CONTEXT.md > D-05 · D-06 · D-07 · D-08
--
-- 전제
--   - 0004의 세 멤버십 헬퍼는 authenticated에 grant execute되어 있으므로
--     여기서는 같은 역할 판정 계약을 그대로 호출합니다.
--   - 0001:108이 주석으로만 문서화한 경로 규약을 이 파일이 정책으로 강제합니다.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. 경로 파서 헬퍼
--
-- ⚠️ 첫 세그먼트를 곧바로 uuid로 캐스팅하면 잘못된 입력이 22P02를 던져
--    "거부"가 아니라 "에러"가 되고 사용자는 403 대신 500을 보게 됩니다.
--    상세한 설계 근거는 01-CONTEXT.md > D-05를 따릅니다.
-- -----------------------------------------------------------------------------
create or replace function public.storage_path_workspace(p_name text)
returns uuid
language sql
immutable
set search_path = public
as $$
  select case
    when p_name ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/[^/]+$'
      then split_part(p_name, '/', 1)::uuid
    else null
  end;
$$;

comment on function public.storage_path_workspace(text) is
  'UUID/UUID/파일명 경로에서 워크스페이스 UUID를 안전하게 반환. Storage 정책 전용.';

grant execute on function public.storage_path_workspace(text) to authenticated;


-- -----------------------------------------------------------------------------
-- 2. 비공개 원본 버킷
--
-- 아래 바이트 제한은 config.toml의 50MiB 제한과 같습니다. MIME 검증은
-- Phase 3 애플리케이션 계층이 맡아 새 파일 형식 추가가 마이그레이션을 요구하지 않습니다.
-- -----------------------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit)
values ('sources', 'sources', false, 52428800)
on conflict (id) do nothing;


-- -----------------------------------------------------------------------------
-- 3. sources 객체 정책
--
-- 파서가 null을 반환하면 멤버십 헬퍼도 false를 반환합니다. 따라서 정확한
-- 3세그먼트가 아닌 경로는 역할과 무관하게 자동으로 거부됩니다.
-- -----------------------------------------------------------------------------
drop policy if exists sources_objects_select_member on storage.objects;
create policy sources_objects_select_member on storage.objects
  for select to authenticated
  using (
    bucket_id = 'sources'
    and public.is_workspace_member(public.storage_path_workspace(name))
  );

drop policy if exists sources_objects_insert_editor on storage.objects;
create policy sources_objects_insert_editor on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'sources'
    and public.has_workspace_role(public.storage_path_workspace(name), 'editor')
  );

drop policy if exists sources_objects_delete_owner on storage.objects;
create policy sources_objects_delete_owner on storage.objects
  for delete to authenticated
  using (
    bucket_id = 'sources'
    and public.has_workspace_role(public.storage_path_workspace(name), 'owner')
  );


-- -----------------------------------------------------------------------------
-- 4. 원본 불변성
--
-- 변경 정책이 없는 것은 의도입니다. "불변 원본 보존"이 제품의 약속이고
-- (decisions.original_file_retention), 원본 재처리는 워커
-- (service_role, BYPASSRLS) 경로이므로 사용자 변경 경로는 필요 없습니다.
-- 상세한 설계 근거는 01-CONTEXT.md > D-07을 따릅니다.
-- -----------------------------------------------------------------------------


-- -----------------------------------------------------------------------------
-- 5. 역참조
--
-- 0001_core_schema.sql:107-110이 문서화만 하던 경로 규칙을 이제 이 파일이 강제합니다.
-- -----------------------------------------------------------------------------
