-- =============================================================================
-- NexusWiki 0014: 워크스페이스 멤버 로스터 + 이메일 초대 RPC
--
-- 관련 태스크: 06-03-PLAN.md (Task 1) — 06-03-PLAN.md 상단 <objective>가 이
--   마이그레이션이 필요한 이유(이메일→user_id 해석 경로가 어디에도 없음)를
--   전부 적어 뒀다. 여기서 다시 설명하지 않는다.
--
-- 새 테이블·RLS 정책 변경 없음. `add_owner_as_member()`(0001)가 세운
-- SECURITY DEFINER 관례를 그대로 잇는 함수 두 개만 더한다 — 요청자 JWT로는
-- 절대 조회할 수 없는 `auth.users`(schemas = ["public","graphql_public"]에
-- 없음, supabase/config.toml)를 정의자 권한으로 건너는 통로다.
-- =============================================================================

begin;

-- -----------------------------------------------------------------------------
-- 1. workspace_members_list — 멤버 로스터 (이메일 포함)
--
-- RLS 정책 대신 함수 본문 안에서 is_workspace_member로 접근을 판정한다
-- (0004의 is_workspace_member/has_workspace_role 헬퍼와 같은 패턴). 멤버가
-- 아닌 호출자에게는 0행을 돌려준다 — T-06-11.
-- -----------------------------------------------------------------------------
create or replace function public.workspace_members_list(p_workspace_id uuid)
returns table (
  user_id    uuid,
  email      text,
  role       text,
  created_at timestamptz
)
language sql
stable
security definer
set search_path = public
as $$
  select m.user_id, u.email, m.role, m.created_at
  from public.workspace_members m
  join auth.users u on u.id = m.user_id
  where public.is_workspace_member(p_workspace_id)
    and m.workspace_id = p_workspace_id
  order by m.created_at asc;
$$;

comment on function public.workspace_members_list(uuid) is
  '호출자가 멤버인 워크스페이스의 로스터(이메일 포함)를 반환한다. 멤버가 아니면 0행. authenticated 전용 — auth.users는 PostgREST에 노출되지 않아 SECURITY DEFINER로만 조회 가능하다.';

revoke all on function public.workspace_members_list(uuid) from public, anon;
grant execute on function public.workspace_members_list(uuid) to authenticated;


-- -----------------------------------------------------------------------------
-- 2. invite_workspace_member — 이메일로 기존 사용자를 초대
--
-- owner만 호출 가능(T-06-08). 요청 역할은 서버에서 다시 검증한다(T-06-09) —
-- 클라이언트 Select가 3값만 보여주는 것과 무관하게, 함수는 그 입력을
-- 신뢰하지 않는다. 이미 멤버인 이메일은 조용히 role만 바꾸지 않고 NW409로
-- 명시적으로 거부한다(UI-SPEC "이미 워크스페이스 멤버입니다." 요구).
-- 미가입 이메일은 NW404 — owner 전용 표면에서의 이메일 등록 여부 노출은
-- 06-03-PLAN.md must_haves.prohibitions에서 판단·수용된 트레이드오프다.
-- -----------------------------------------------------------------------------
create or replace function public.invite_workspace_member(
  p_workspace_id uuid,
  p_email        text,
  p_role         text default 'viewer'
)
returns table (
  user_id uuid,
  email   text,
  role    text
)
language plpgsql
volatile
security definer
set search_path = public
as $fn$
declare
  v_user_id uuid;
begin
  if not public.has_workspace_role(p_workspace_id, 'owner') then
    raise exception '워크스페이스 소유자만 멤버를 초대할 수 있습니다'
      using errcode = '42501';
  end if;

  if p_role not in ('owner', 'editor', 'viewer') then
    raise exception '알 수 없는 역할입니다: %', p_role
      using errcode = '22023';
  end if;

  -- `u` 별칭이 필요하다: RETURNS TABLE의 출력 컬럼 `email`이 plpgsql 본문
  -- 안에서 암묵적 변수로 스코프에 들어와, 별칭 없는 `email`은 그 변수와
  -- auth.users.email 사이에서 "column reference is ambiguous"로 죽는다
  -- (로컬 db reset 실행 중 실측).
  select u.id into v_user_id
  from auth.users u
  where lower(u.email) = lower(btrim(p_email))
  limit 1;

  if v_user_id is null then
    raise exception '가입된 사용자를 찾을 수 없습니다'
      using errcode = 'NW404';
  end if;

  -- `on conflict on constraint`을 쓰는 이유: `on conflict (workspace_id,
  -- user_id)`처럼 컬럼명을 나열하면 plpgsql이 RETURNS TABLE 출력 컬럼과
  -- 이름이 같은 `user_id`를 로컬 변수로 오인해 "column reference is
  -- ambiguous"로 죽는다(위 auth.users 조회와 같은 클래스의 문제, 로컬
  -- db reset 실행 중 실측). 제약 이름으로 지정하면 이 경로를 완전히 피한다.
  insert into public.workspace_members (workspace_id, user_id, role)
  values (p_workspace_id, v_user_id, p_role)
  on conflict on constraint workspace_members_pkey do nothing;

  if not found then
    raise exception '이미 워크스페이스 멤버입니다'
      using errcode = 'NW409';
  end if;

  return query select v_user_id, p_email, p_role;
end
$fn$;

comment on function public.invite_workspace_member(uuid, text, text) is
  '워크스페이스 owner가 이미 가입된 이메일을 멤버로 추가한다. 비-owner는 42501, 미가입 이메일은 NW404, 이미 멤버면 NW409. authenticated 전용 — service_role에는 EXECUTE를 주지 않는다(사용자 경로이지 워커 경로가 아니다).';

revoke all on function public.invite_workspace_member(uuid, text, text) from public, anon;
grant execute on function public.invite_workspace_member(uuid, text, text) to authenticated;

commit;
