-- =============================================================================
-- NexusWiki 0004: 멀티테넌트 RLS 정책
--
-- 관련 태스크: P1-SEC-01
-- 설계 근거:  checklists.json > decisions.tenancy (team-first)
--             checklists.json > decisions.db_access (hybrid)
--
-- 0001~0003은 9개 테이블에 RLS를 "정책 없이" 켜 뒀습니다(= 전면 거부).
-- 이 파일이 그 위에 실제 정책을 부여합니다.
--
-- 전제
--   - anon/authenticated는 public 스키마 테이블에 이미 전권 GRANT를 가집니다
--     (Supabase 기본값). 즉 격리를 강제하는 것은 GRANT가 아니라 RLS 정책뿐입니다.
--   - 모든 정책을 `to authenticated`로 한정합니다. anon에는 어떤 정책도 없으므로
--     로그인하지 않은 요청은 계속 전면 거부입니다.
--   - service_role은 BYPASSRLS라 워커/마이그레이션은 이 파일의 영향을 받지 않습니다.
--     ⚠️ 그래서 워커 코드에는 workspace_id 필터를 반드시 명시해야 합니다 (P4-SEC-01).
--
-- 역할 등급:  owner(3) > editor(2) > viewer(1)
--   SELECT          멤버 전원
--   INSERT/UPDATE   editor 이상
--   DELETE          owner
-- 아래 "등급 규칙에서 벗어난 곳" 주석이 붙은 세 군데는 예외이며 이유를 적어 뒀습니다.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. 헬퍼 함수 (SECURITY DEFINER)
--
-- ⚠️ 이 함수들이 없으면 workspace_members의 정책이 "내가 이 워크스페이스
--    멤버인가"를 확인하려고 workspace_members를 다시 조회하면서 무한 재귀
--    (42P17 infinite recursion detected in policy)로 죽습니다.
--    SECURITY DEFINER는 함수 본문을 소유자(postgres) 권한으로 실행시켜
--    RLS를 우회시키므로 그 고리를 끊습니다.
--
-- stable          — 빠뜨리면 행마다 재평가되어 정책이 O(n) 함수 호출이 됩니다.
-- set search_path — 빠뜨리면 호출자가 search_path를 조작해 동명의 가짜 테이블을
--                   심을 수 있습니다(SECURITY DEFINER에서는 곧 권한 상승).
--
-- 노출 범위: 이 함수들은 호출자 자신의 멤버십만 알려줍니다(auth.uid() 고정).
--            남의 멤버십은 조회할 수 없으므로 authenticated에 열어도 안전합니다.
-- -----------------------------------------------------------------------------

create or replace function public.is_workspace_member(ws_id uuid)
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (
    select 1 from public.workspace_members m
    where m.workspace_id = ws_id
      and m.user_id = (select auth.uid())
  );
$$;

create or replace function public.workspace_role(ws_id uuid)
returns text
language sql
security definer
stable
set search_path = public
as $$
  select m.role from public.workspace_members m
  where m.workspace_id = ws_id
    and m.user_id = (select auth.uid());
$$;

-- 등급 비교. 멤버가 아니면 0등급이므로 항상 false.
create or replace function public.has_workspace_role(ws_id uuid, min_role text)
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select coalesce(
    (case public.workspace_role(ws_id)
       when 'owner' then 3 when 'editor' then 2 when 'viewer' then 1 else 0 end)
    >=
    (case min_role
       when 'owner' then 3 when 'editor' then 2 when 'viewer' then 1 end),
    false
  );
$$;

comment on function public.is_workspace_member(uuid) is
  '호출자가 해당 워크스페이스 멤버인지. RLS 정책 전용 — 재귀 차단용 SECURITY DEFINER.';
comment on function public.has_workspace_role(uuid, text) is
  '호출자의 역할이 min_role 이상인지. owner>editor>viewer.';

grant execute on function public.is_workspace_member(uuid)     to authenticated;
grant execute on function public.workspace_role(uuid)          to authenticated;
grant execute on function public.has_workspace_role(uuid, text) to authenticated;


-- -----------------------------------------------------------------------------
-- 2. 소유자 멤버십 보호 트리거
--
-- 0001은 "멤버 0명 워크스페이스는 RLS 하에서 영구 접근 불가"를 소유자 자동
-- 등록 트리거로 막았습니다. 그런데 등록된 뒤에 소유자가 자기 멤버십 행을
-- 지우거나 viewer로 낮추면 같은 상태로 되돌아갑니다 — workspaces.owner_id는
-- 그대로인데 정작 그 사람이 워크스페이스를 관리할 수 없게 됩니다.
--
-- 소유권 이전은 workspaces.owner_id를 바꾸는 경로로만 하도록 강제합니다.
-- -----------------------------------------------------------------------------
create or replace function public.protect_owner_membership()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_owner_id uuid;
  v_row      public.workspace_members;
begin
  v_row := case when tg_op = 'DELETE' then old else new end;

  select w.owner_id into v_owner_id
  from public.workspaces w where w.id = v_row.workspace_id;

  -- 워크스페이스가 통째로 지워지는 중이면(cascade) 간섭하지 않습니다.
  if v_owner_id is null then
    return v_row;
  end if;

  if old.user_id = v_owner_id then
    if tg_op = 'DELETE' then
      raise exception '워크스페이스 소유자의 멤버십은 삭제할 수 없습니다. workspaces.owner_id를 먼저 이전하세요.'
        using errcode = 'raise_exception';
    elsif new.user_id <> old.user_id then
      -- user_id를 바꾸는 것은 소유자 행을 다른 사람 행으로 갈아치우는 것과 같습니다.
      raise exception '워크스페이스 소유자의 멤버십 행에서 user_id를 바꿀 수 없습니다.'
        using errcode = 'raise_exception';
    elsif new.role <> 'owner' then
      raise exception '워크스페이스 소유자의 역할은 낮출 수 없습니다 (요청 역할: %). workspaces.owner_id를 먼저 이전하세요.', new.role
        using errcode = 'raise_exception';
    end if;
  end if;

  return v_row;
end;
$$;

create trigger workspace_members_protect_owner
  before update or delete on public.workspace_members
  for each row execute function public.protect_owner_membership();


-- -----------------------------------------------------------------------------
-- 3. workspaces
--
-- 등급 규칙에서 벗어난 곳 (1/3): UPDATE를 editor가 아니라 owner로 제한합니다.
--   workspaces 행의 UPDATE는 곧 이름 변경과 owner_id 이전(= 소유권 양도)입니다.
--   editor에게 열면 editor가 스스로를 소유자로 만들 수 있습니다.
-- -----------------------------------------------------------------------------

-- owner_id 조건이 함께 있는 이유:
-- `insert into workspaces ... returning *`의 RETURNING은 SELECT 정책을 통과해야
-- 하는데, 소유자를 멤버로 넣는 0001의 트리거는 AFTER 트리거라 그 시점엔 아직
-- 멤버십 행이 없습니다. 멤버십만으로 판정하면 워크스페이스 생성이 실패합니다.
create policy workspaces_select_member on public.workspaces
  for select to authenticated
  using (public.is_workspace_member(id) or owner_id = (select auth.uid()));

create policy workspaces_insert_self_owned on public.workspaces
  for insert to authenticated
  with check (owner_id = (select auth.uid()));

create policy workspaces_update_owner on public.workspaces
  for update to authenticated
  using (public.has_workspace_role(id, 'owner'))
  with check (public.has_workspace_role(id, 'owner'));

create policy workspaces_delete_owner on public.workspaces
  for delete to authenticated
  using (public.has_workspace_role(id, 'owner'));


-- -----------------------------------------------------------------------------
-- 4. workspace_members
--
-- 등급 규칙에서 벗어난 곳 (2/3): 멤버 관리를 editor가 아니라 owner로 제한합니다.
--   editor에게 INSERT를 열면 editor가 자신을 owner 역할로 한 행을 추가해
--   즉시 권한을 상승시킬 수 있습니다. 멤버 관리는 소유자 행위입니다.
-- -----------------------------------------------------------------------------
create policy workspace_members_select_member on public.workspace_members
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

create policy workspace_members_insert_owner on public.workspace_members
  for insert to authenticated
  with check (public.has_workspace_role(workspace_id, 'owner'));

create policy workspace_members_update_owner on public.workspace_members
  for update to authenticated
  using (public.has_workspace_role(workspace_id, 'owner'))
  with check (public.has_workspace_role(workspace_id, 'owner'));

create policy workspace_members_delete_owner on public.workspace_members
  for delete to authenticated
  using (public.has_workspace_role(workspace_id, 'owner'));


-- -----------------------------------------------------------------------------
-- 5. raw_sources — Layer 1 원문
--
-- UPDATE 정책이 없는 것은 의도입니다. "불변 원본 보존"이 제품의 약속이고
-- (decisions.original_file_retention), 파서 개선 시 재처리는 워커
-- (service_role, BYPASSRLS) 경로이므로 사용자 UPDATE는 필요 없습니다.
-- -----------------------------------------------------------------------------
create policy raw_sources_select_member on public.raw_sources
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

create policy raw_sources_insert_editor on public.raw_sources
  for insert to authenticated
  with check (public.has_workspace_role(workspace_id, 'editor'));

create policy raw_sources_delete_owner on public.raw_sources
  for delete to authenticated
  using (public.has_workspace_role(workspace_id, 'owner'));


-- -----------------------------------------------------------------------------
-- 6. wiki_pages — Layer 2 컴파일 산출물
--
-- UPDATE는 P2-QC-01의 PATCH /api/wiki/{id}/verify가 씁니다
-- (explored / verification_status 전이). 그래서 editor에게 엽니다.
-- -----------------------------------------------------------------------------
create policy wiki_pages_select_member on public.wiki_pages
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

create policy wiki_pages_insert_editor on public.wiki_pages
  for insert to authenticated
  with check (public.has_workspace_role(workspace_id, 'editor'));

create policy wiki_pages_update_editor on public.wiki_pages
  for update to authenticated
  using (public.has_workspace_role(workspace_id, 'editor'))
  -- with check에도 같은 조건: 편집자가 workspace_id를 남의 워크스페이스로
  -- 바꿔치기해 페이지를 옮기는 것을 막습니다.
  with check (public.has_workspace_role(workspace_id, 'editor'));

create policy wiki_pages_delete_owner on public.wiki_pages
  for delete to authenticated
  using (public.has_workspace_role(workspace_id, 'owner'));


-- -----------------------------------------------------------------------------
-- 7. 파생 데이터 3종: source_chunks / wiki_embeddings / wiki_links
--
-- 등급 규칙에서 벗어난 곳 (3/3): 사용자 경로에서는 읽기 전용입니다.
--   셋 다 파서·임베더·컴파일러(전부 워커)가 만드는 파생 데이터이고,
--   계획서 어디에도 사용자가 직접 쓰는 경로가 없습니다.
--   특히 source_chunks에 INSERT를 열면 editor가 원문에 없는 청크를 심어
--   "이중 Citation의 원문 측" 인용을 위조할 수 있습니다. 제품의 신뢰
--   근거를 사용자 입력에 노출시킬 이유가 없습니다.
--   워커는 service_role(BYPASSRLS)이므로 아무 영향도 받지 않습니다.
--
-- 세 테이블 모두 workspace_id를 직접 들고 있어(0002에서 비정규화) 정책에
-- 조인이 필요 없습니다.
-- -----------------------------------------------------------------------------
create policy source_chunks_select_member on public.source_chunks
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

create policy wiki_embeddings_select_member on public.wiki_embeddings
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

create policy wiki_links_select_member on public.wiki_links
  for select to authenticated
  using (public.is_workspace_member(workspace_id));


-- -----------------------------------------------------------------------------
-- 8. prompt_templates
--
-- workspace_id IS NULL = 전역 기본 템플릿(P1-SEED-01). 모든 로그인 사용자가
-- 읽을 수 있어야 합니다 — 이 조건을 빠뜨리면 시드한 기본 템플릿이 아무에게도
-- 보이지 않아 "질문하기" 화면이 빈 채로 뜹니다.
-- 쓰기는 워크스페이스 소속 템플릿으로만 한정합니다(전역 템플릿 생성/수정 불가).
-- -----------------------------------------------------------------------------
create policy prompt_templates_select_global_or_member on public.prompt_templates
  for select to authenticated
  using (workspace_id is null or public.is_workspace_member(workspace_id));

create policy prompt_templates_insert_editor on public.prompt_templates
  for insert to authenticated
  with check (workspace_id is not null and public.has_workspace_role(workspace_id, 'editor'));

create policy prompt_templates_update_editor on public.prompt_templates
  for update to authenticated
  using (workspace_id is not null and public.has_workspace_role(workspace_id, 'editor'))
  with check (workspace_id is not null and public.has_workspace_role(workspace_id, 'editor'));

create policy prompt_templates_delete_owner on public.prompt_templates
  for delete to authenticated
  using (workspace_id is not null and public.has_workspace_role(workspace_id, 'owner'));


-- -----------------------------------------------------------------------------
-- 9. jobs
--
-- SELECT만 엽니다. 잡 생성(P2-ING-01)과 상태 전이(P2-JOB-01)는 전부
-- service_role 경로이고, 0003의 큐 조작 함수도 service_role 전용입니다.
-- 사용자에게 필요한 건 P3-UI-01의 진행 상태 폴링, 즉 읽기뿐입니다.
-- -----------------------------------------------------------------------------
create policy jobs_select_member on public.jobs
  for select to authenticated
  using (public.is_workspace_member(workspace_id));
