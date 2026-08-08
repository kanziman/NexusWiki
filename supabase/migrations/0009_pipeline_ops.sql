-- =============================================================================
-- NexusWiki 0009: 파이프라인 운영 표면 — 데드레터 · 취소 · 인큐 · 비용 상한
--
-- 관련 태스크: P2-JOB-01(섹션 1·4·5) · P2-ING-01(섹션 6) · P4-OPS-01(섹션 2·3)
--             COMP-02(섹션 7) · P4-SEC-01(섹션 8)
-- 설계 근거:  03-CONTEXT.md > D-03                  (섹션 4의 시그니처와 권한 방향)
--             03-02-PLAN.md > D-P1                  (섹션 6의 definer RPC 선택)
--             03-02-PLAN.md > D-P2                  (섹션 2·3의 micro-dollar 정수 단위)
--             03-02-PLAN.md > D-P3                  (섹션 1·5·6의 협조적 취소)
--             checklists.json > decisions.job_queue  (큐 계약 전반)
--             checklists.json > decisions.db_access  (섹션 8의 롤 분리)
--
-- 상태 전이 (0007의 그림에 취소 화살표 두 개가 추가됩니다)
--
--   queued ──claim──> running ──complete──> succeeded
--     ^  ^               │
--     │  │               ├──fail (attempts < max)──> failed ──run_after 경과──┐
--     │  │               ├──fail (attempts >= max)──> dead ──retry_dead_job──┐│
--     │  │               ├──dead_letter (락 소유자)──> dead                  ││
--     │  │               └──cancel_job (락 소유자)───> canceled              ││
--     │  └───────────────── reap (락 타임아웃, attempts 유지) ────────────────┘│
--     └──────────────────── release (attempts −1, 자발적 반납) ────────────────┘
--
--   queued/failed ──request_job_cancel──> canceled          (즉시 전이)
--   running       ──request_job_cancel──> running + cancel_requested_at
--                                          (협조적 — 워커가 다음 단계 경계에서 본다)
--
-- 'canceled'는 'dead'와 다릅니다. dead는 "시도를 소진했으니 사람이 보라"이고
-- canceled는 "사람이 이미 보았고 그만두라고 했다"입니다. 둘을 한 값으로 합치면
-- 프론트가 재시도 버튼을 어디에 그려야 하는지 알 수 없습니다.
--
-- ⚠️ 이 파일도 0007·0008처럼 자기 자신을 begin/commit으로 감쌉니다. 섹션 3
--    (usage_events 신설)만 적용되고 섹션 8(권한)이 빠지면, 워크스페이스 지출
--    기록이 생겼는데 그것을 아무도 읽지 못하거나 반대로 누구나 지울 수 있는
--    상태가 남습니다.
--
-- ⚠️ 섹션 8은 0008이 클라우드에서 놓친 것을 함께 정정합니다. 클라우드의
--    pg_default_acl에는 (schema public, objtype f, owner postgres) 항목이 있어
--    새 함수에 anon·authenticated·service_role 세 롤 모두에게 EXECUTE를
--    기본 부여합니다. 로컬에는 그 항목이 없습니다. 그래서 0007·0008이 쓴
--    `revoke all ... from public, anon`은 클라우드에서 service_role을 걷어내지
--    못했고, search_chunks의 EXECUTE가 service_role에 남았습니다.
--    이 파일의 모든 함수 revoke는 service_role을 명시적으로 포함합니다.
-- =============================================================================

begin;


-- -----------------------------------------------------------------------------
-- 1. jobs 상태 확장 — 'canceled' 추가와 cancel_requested_at
--
-- CHECK 재정의는 "기존 객체 변경"이지만 D-01의 판별 기준(0008 이하 수정 불가)에
-- 걸리지 않습니다. 되돌릴 수 없는 것은 파일 번호이지 객체가 아니고, CHECK는 어느
-- 번호의 마이그레이션에서도 drop + add로 되돌릴 수 있습니다. 임베딩 차원과 다른
-- 점은 데이터가 걸려 있지 않다는 것입니다 (03-02-PLAN.md > D-P3).
--
-- 제약 이름은 0003:39-40의 인라인 CHECK가 Postgres 기본 규칙으로 얻은 이름이며
-- 적용 대상 DB에서 직접 확인했습니다 (pg_constraint: jobs_status_check).
--
-- ⚠️ 'canceled'는 'running'이 아니므로 jobs_lock_consistency(0003:65-68)가
--    locked_at·locked_by를 null로 요구합니다. 취소 경로는 전부 두 컬럼을 함께
--    비워야 하며, 비우지 않으면 CHECK가 행을 거부합니다.
-- ⚠️ claim_job의 술어가 status in ('queued','failed')이므로(0003:120) 취소된 잡은
--    다시 집히지 않습니다. 취소는 별도 인덱스나 필터 없이 폴링 경로에서 사라집니다.
-- -----------------------------------------------------------------------------
alter table public.jobs
  drop constraint jobs_status_check;

alter table public.jobs
  add constraint jobs_status_check
    check (status in ('queued', 'running', 'succeeded', 'failed', 'dead', 'canceled'));

alter table public.jobs
  add column cancel_requested_at timestamptz;

comment on column public.jobs.cancel_requested_at is
  '취소 요청 시각. queued/failed 잡은 요청과 동시에 canceled가 되지만 running 잡은 이 값만 찍히고 워커가 다음 체인 단계 경계에서 읽어 스스로 마감한다(협조적 취소). null이면 취소 요청이 없었다는 뜻이다.';


-- -----------------------------------------------------------------------------
-- 2. workspaces 월 비용 상한
--
-- 단위는 micro-dollar 정수입니다. 근거는 03-02-PLAN.md > D-P2 (여기서 재서술하지
-- 않습니다). 기본값 5000000 = $5.00/월/워크스페이스는 checklists.json >
-- open_questions의 "워크스페이스별 월 LLM 비용 상한값"을 이 페이즈가 닫은 값입니다.
-- -----------------------------------------------------------------------------
alter table public.workspaces
  add column monthly_budget_micros bigint not null default 5000000
    constraint workspaces_budget_non_negative check (monthly_budget_micros >= 0);

comment on column public.workspaces.monthly_budget_micros is
  '이 워크스페이스의 월 LLM·임베딩 비용 상한. 단위는 micro-dollar 정수(1000000 = $1.00)이며 부동소수를 쓰지 않는 이유는 03-02-PLAN.md > D-P2에 있다. enqueue_source_job이 인큐 시점에 이 값과 이번 달 usage_events 합을 비교한다.';


-- -----------------------------------------------------------------------------
-- 3. usage_events — LLM·임베딩 사용 기록 (OPS-01)
--
-- 이 테이블은 감사 기록입니다. 그래서 어느 롤에도 UPDATE/DELETE를 주지 않습니다
-- (섹션 8). 기록을 고칠 수 있으면 상한은 상한이 아니라 제안이 됩니다.
--
-- cost_micros가 bigint인 이유: sum()이 더하는 순서와 무관하게 정확해야 상한
-- 판정이 재현 가능합니다. 비용 경로 어디에도 부동소수 타입을 두지 않습니다.
--
-- job_id는 on delete set null입니다 — 잡이 지워져도(현재 어느 롤에도 jobs DELETE
-- 권한이 없으므로 실질적으로는 워크스페이스 cascade뿐입니다) 지출 기록은 남아야
-- 합니다. 반대로 workspace_id는 cascade입니다: 워크스페이스가 사라지면 그
-- 워크스페이스의 지출 기록도 의미를 잃습니다.
--
-- 0001의 관례에 따라 테이블 생성과 같은 마이그레이션에서 RLS를 켭니다. 정책이
-- 붙기 전 한 순간도 무방비로 노출되지 않습니다.
-- -----------------------------------------------------------------------------
create table public.usage_events (
  id           uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  job_id       uuid references public.jobs (id) on delete set null,

  kind     text not null check (kind in ('llm', 'embedding')),
  provider text not null check (char_length(btrim(provider)) > 0),
  model    text not null check (char_length(btrim(model)) > 0),

  prompt_tokens     int not null default 0 check (prompt_tokens >= 0),
  completion_tokens int not null default 0 check (completion_tokens >= 0),
  total_tokens      int not null default 0 check (total_tokens >= 0),

  cost_micros bigint not null default 0 check (cost_micros >= 0),

  occurred_at timestamptz not null default now(),
  metadata    jsonb not null default '{}'
);

-- 인큐 시점 상한 판정(이번 달 합)과 프론트의 최근 사용 내역이 같은 경로를 씁니다.
create index usage_events_workspace_occurred_idx
  on public.usage_events (workspace_id, occurred_at desc);

comment on column public.usage_events.cost_micros is
  '이 호출의 비용. 단위는 micro-dollar 정수이며 workspaces.monthly_budget_micros와 같은 축이다. 근거는 03-02-PLAN.md > D-P2.';
comment on column public.usage_events.metadata is
  '⚠️ 여기에 프롬프트 본문이나 LLM 응답 본문을 싣지 않는다. 이 테이블은 워크스페이스 멤버가 SELECT할 수 있으므로(usage_events_select_member) 본문을 실으면 사용량 화면이 그대로 원문 유출 경로가 된다. 담을 것은 요청 식별자·라우팅된 실제 호스트·재시도 횟수 같은 비본문 메타데이터뿐이다.';

alter table public.usage_events enable row level security;

-- 사용자 쓰기 경로는 설계상 없습니다. 기록은 워커(service_role)만 만듭니다.
create policy usage_events_select_member on public.usage_events
  for select to authenticated
  using (public.is_workspace_member(workspace_id));


-- -----------------------------------------------------------------------------
-- 4. dead_letter_job — 특정 잡을 한 번에 dead로 (03-CONTEXT.md > D-03)
--
-- 0007:212-233의 release_job과 동형입니다. 미등록 job type을 만난 워커는 지금
-- fail_job(backoff=0)으로 max_attempts만큼 왕복해야 dead에 수렴하는데
-- (apps/worker/src/worker/queue.py:112-136에 그 한계가 인라인으로 기록되어 있습니다),
-- 그 왕복은 잡 하나당 세 번의 무의미한 claim을 만듭니다.
--
-- ⚠️ locked_by = p_worker_id 술어가 이 함수가 release_job과 시그니처를 맞춘
--    유일한 이유입니다. 빼면 reap이 이미 락을 뺏은 뒤 늦게 깨어난 워커가 남의
--    잡을(그 사이 다른 워커가 정상 처리 중인 잡을) dead로 만듭니다.
--    이 계약은 supabase/tests/0009_pipeline_ops.sql T1이 SQL 수준에서 고정합니다.
-- -----------------------------------------------------------------------------
create or replace function public.dead_letter_job(
  p_job_id    uuid,
  p_worker_id text,
  p_error     text
)
returns setof public.jobs
language sql
volatile
set search_path = public
as $$
  update public.jobs j
  set status     = 'dead',
      last_error = p_error,
      locked_at  = null,
      locked_by  = null
  where j.id = p_job_id
    and j.status = 'running'
    and j.locked_by = p_worker_id
  returning j.*;
$$;

comment on function public.dead_letter_job(uuid, text, text) is
  '락 소유자 본인이 잡을 한 번에 dead로 보내고 last_error를 남긴다. locked_by가 다르거나 running이 아니면 예외가 아니라 0행 no-op이다. service_role 전용.';


-- -----------------------------------------------------------------------------
-- 5. cancel_job — 워커가 취소 요청을 수용해 잡을 마감한다
--
-- 워커는 claim 직후 cancel_requested_at을 읽고, 값이 있으면 핸들러를 돌리지 않은
-- 채 이 함수로 마감합니다. 술어 3개는 dead_letter_job과 같습니다 — 취소도 락
-- 소유자만 할 수 있어야 남의 진행을 덮어쓰지 않습니다.
--
-- complete_job_and_chain이 아니라 이 함수를 쓰는 이유: 체인을 잇지 않기 위함입니다.
-- 취소된 parse 잡이 compile을 인큐하면 취소가 아무 일도 하지 않은 것이 됩니다.
-- -----------------------------------------------------------------------------
create or replace function public.cancel_job(
  p_job_id    uuid,
  p_worker_id text
)
returns setof public.jobs
language sql
volatile
set search_path = public
as $$
  update public.jobs j
  set status    = 'canceled',
      locked_at = null,
      locked_by = null
  where j.id = p_job_id
    and j.status = 'running'
    and j.locked_by = p_worker_id
  returning j.*;
$$;

comment on function public.cancel_job(uuid, text) is
  '락 소유자 본인이 취소 요청을 수용해 running 잡을 canceled로 마감한다. 체인을 잇지 않는다. locked_by가 다르거나 running이 아니면 0행 no-op이다. service_role 전용.';


-- -----------------------------------------------------------------------------
-- 6. 사용자 RPC 3종 — security definer
--
-- 셋 다 security definer이므로 RLS를 우회합니다. 그래서 본문 첫머리의
-- has_workspace_role 확인이 이 경로의 유일한 격리 수단이며, set search_path =
-- public이 필수입니다(0004:36-38이 같은 규율을 설명합니다).
--
-- ⚠️ 잡이 없는 경우와 멤버가 아닌 경우를 같은 42501로 렌더합니다. 두 경우를
--    다른 신호로 만들면 잡 id를 하나씩 넣어보는 것만으로 다른 워크스페이스에
--    어떤 잡이 존재하는지 열거할 수 있습니다 (02-CONTEXT.md > D-12).
-- -----------------------------------------------------------------------------

-- (a) enqueue_source_job — 사용자 경로의 유일한 인큐 통로
--
-- ⚠️ 이 함수가 사용자 경로의 유일한 인큐 통로이고, 그래서 jobs에는 어느 사용자
--    롤에도 INSERT 권한도 INSERT 정책도 만들지 않습니다(0007:361은 SELECT만 줍니다).
--    조건부 INSERT 정책을 주면 authenticated가 PostgREST로 /jobs에 직접 INSERT할 수
--    있게 되고 그 경로는 아래 비용 상한을 지나지 않습니다. "상한을 통과하지 않고는
--    잡이 만들어질 수 없다"가 구조적으로 참이어야 OPS-01이 성립합니다
--    (03-02-PLAN.md > D-P1).
--
-- ⚠️ 잡 종류를 인자로 받지 않고 'parse'를 본문이 고정합니다. 인자로 받으면 로그인
--    사용자가 임의의 jobs.type과 임의의 payload를 definer 권한으로 삽입할 수 있고,
--    jobs.type에는 CHECK 열거가 없으므로(0003:31-36) DB가 그것을 막지 못합니다.
--
-- ⚠️ 상한 비교는 포함(>=)입니다. 합이 상한과 정확히 같으면 거부합니다.
create or replace function public.enqueue_source_job(
  p_workspace_id  uuid,
  p_raw_source_id uuid
)
returns setof public.jobs
language plpgsql
volatile
security definer
set search_path = public
as $fn$
declare
  v_spent bigint;
  v_cap   bigint;
  v_job   public.jobs;
begin
  -- (1) 멤버십. definer라 RLS가 걸리지 않으므로 이 확인이 유일한 격리 수단이다.
  if not public.has_workspace_role(p_workspace_id, 'editor') then
    raise exception '워크스페이스에 대한 편집 권한이 없습니다'
      using errcode = '42501';
  end if;

  -- (2) 소스 소유권. 이 확인이 없으면 남의 워크스페이스 raw_source에 대한 잡을
  --     자기 워크스페이스에 만들 수 있다 — definer가 RLS를 우회하기 때문이다.
  --     실패 신호는 (1)과 같은 42501이다(존재 여부를 상태로 구분하지 않는다).
  if not exists (
    select 1 from public.raw_sources r
    where r.id = p_raw_source_id
      and r.workspace_id = p_workspace_id
  ) then
    raise exception '워크스페이스에 대한 편집 권한이 없습니다'
      using errcode = '42501';
  end if;

  -- (3) 이번 달 누적 지출. 기록이 하나도 없으면 null이 아니라 0이어야 한다 —
  --     null이면 아래 비교가 null이 되어 상한이 조용히 사라진다.
  --
  --     ⚠️ date_trunc('month', now() at time zone 'utc')는 timestamp(무 tz)라
  --        timestamptz 컬럼과 비교하면 세션 TimeZone으로 암묵 캐스트된다.
  --        세션이 UTC가 아닌 순간 월 경계가 조용히 어긋나므로 at time zone 'utc'로
  --        다시 고정해 timestamptz로 되돌린다. 경계는 포함(>=)이다.
  select coalesce(sum(u.cost_micros), 0) into v_spent
  from public.usage_events u
  where u.workspace_id = p_workspace_id
    and u.occurred_at >= (date_trunc('month', now() at time zone 'utc') at time zone 'utc');

  select w.monthly_budget_micros into v_cap
  from public.workspaces w
  where w.id = p_workspace_id;

  -- (4) 상한 판정. 같으면 거부한다.
  if v_spent >= v_cap then
    raise exception '월 비용 상한 초과 (사용 %, 상한 %)', v_spent, v_cap
      using errcode = '53400';
  end if;

  -- (5) 인큐. 같은 대상의 잡이 이미 대기·진행 중이면 jobs_dedup_idx(0007 섹션 2)가
  --     막으므로 23505로 죽지 않고 조용히 넘어간다.
  insert into public.jobs (workspace_id, type, payload)
  values (
    p_workspace_id,
    'parse',
    jsonb_build_object(
      'target_id',     p_raw_source_id::text,
      'raw_source_id', p_raw_source_id::text
    )
  )
  on conflict do nothing
  returning * into v_job;

  -- (6) 중복이었다면 이미 큐에 있는 그 잡을 돌려준다. 같은 요청을 두 번 보낸
  --     사용자가 두 번 다 같은 job_id를 받아야 프론트가 하나의 진행을 따라간다.
  if not found then
    select * into v_job
    from public.jobs j
    where j.workspace_id = p_workspace_id
      and j.type = 'parse'
      and j.payload ->> 'target_id' = p_raw_source_id::text
      and j.status in ('queued', 'running', 'failed')
    limit 1;
  end if;

  -- 방어: 삽입도 조회도 실패했다면 null 레코드를 돌려주지 않고 0행으로 끝낸다.
  if v_job.id is null then
    return;
  end if;

  return next v_job;
end
$fn$;

comment on function public.enqueue_source_job(uuid, uuid) is
  '사용자 경로의 유일한 parse 잡 인큐 통로. editor 이상 멤버십과 raw_source 소유권을 확인하고(위반은 42501) 이번 달 usage_events 합이 workspaces.monthly_budget_micros 이상이면 53400으로 거부한다. 같은 대상으로 다시 부르면 새 잡을 만들지 않고 기존 잡을 돌려준다. authenticated 전용 — service_role에는 EXECUTE를 주지 않는다.';


-- (b) request_job_cancel — 사용자가 취소를 요청한다
--
-- queued/failed 잡은 아직 아무도 잡고 있지 않으므로 즉시 canceled로 만듭니다.
-- running 잡은 cancel_requested_at만 찍습니다 — 워커가 jobs를 직접 UPDATE하지
-- 않는다는 계약과 COMP-04의 잡 분할 덕분에, 취소는 다음 체인 단계 경계에서
-- 반영됩니다 (02-CONTEXT.md > D-16이 하트비트 대신 분할을 택한 것의 배당금).
--
-- succeeded/dead/canceled 잡은 0행입니다. 이미 끝난 것을 취소하는 것은 오류가
-- 아니라 아무 일도 아닙니다.
create or replace function public.request_job_cancel(p_job_id uuid)
returns setof public.jobs
language plpgsql
volatile
security definer
set search_path = public
as $fn$
declare
  v_ws  uuid;
  v_job public.jobs;
begin
  select j.workspace_id into v_ws from public.jobs j where j.id = p_job_id;

  if v_ws is null or not public.has_workspace_role(v_ws, 'editor') then
    raise exception '잡에 대한 편집 권한이 없습니다'
      using errcode = '42501';
  end if;

  -- 아직 아무도 집지 않은 잡: 즉시 전이. locked_*는 이미 null이지만 명시적으로
  -- 비워 jobs_lock_consistency를 이 경로에서도 무조건 참으로 만든다.
  update public.jobs j
  set status              = 'canceled',
      cancel_requested_at = now(),
      locked_at           = null,
      locked_by           = null
  where j.id = p_job_id
    and j.status in ('queued', 'failed')
  returning j.* into v_job;

  if found then
    return next v_job;
    return;
  end if;

  -- 진행 중인 잡: 협조적 취소. 상태는 그대로 두고 요청 시각만 남긴다.
  update public.jobs j
  set cancel_requested_at = now()
  where j.id = p_job_id
    and j.status = 'running'
  returning j.* into v_job;

  if found then
    return next v_job;
  end if;

  return;
end
$fn$;

comment on function public.request_job_cancel(uuid) is
  'queued/failed 잡을 즉시 canceled로 만들고 running 잡에는 cancel_requested_at만 찍는다(협조적 취소). 잡이 없거나 editor 미만이면 42501, 이미 끝난 잡이면 0행. authenticated 전용.';


-- (c) retry_dead_job — dead 잡을 큐로 되돌린다 (ING-07)
--
-- attempts를 0으로 되돌리는 것이 이 함수의 요점입니다. 되돌리지 않으면
-- attempts >= max_attempts가 그대로라 claim 직후 fail_job이 곧바로 다시 dead로
-- 판정합니다 (0003:169).
--
-- dead가 아닌 잡에 부르면 0행입니다 — 프론트의 중복 클릭이 예외가 아니라 no-op
-- 이어야 하고, 이미 queued로 되돌린 잡에 다시 불러도 attempts가 재초기화되거나
-- 잡이 증식하지 않아야 합니다.
--
-- ⚠️ 같은 대상의 다른 잡이 이미 queued/running/failed로 있으면 jobs_dedup_idx가
--    이 UPDATE를 23505로 막습니다. 그것이 맞는 동작입니다 — 되살린 잡과 살아 있는
--    잡이 같은 대상을 두 번 처리하는 것보다 소란스러운 실패가 낫습니다.
create or replace function public.retry_dead_job(p_job_id uuid)
returns setof public.jobs
language plpgsql
volatile
security definer
set search_path = public
as $fn$
declare
  v_ws  uuid;
  v_job public.jobs;
begin
  select j.workspace_id into v_ws from public.jobs j where j.id = p_job_id;

  if v_ws is null or not public.has_workspace_role(v_ws, 'editor') then
    raise exception '잡에 대한 편집 권한이 없습니다'
      using errcode = '42501';
  end if;

  update public.jobs j
  set status              = 'queued',
      attempts            = 0,
      last_error          = null,
      run_after           = now(),
      locked_at           = null,
      locked_by           = null,
      cancel_requested_at = null
  where j.id = p_job_id
    and j.status = 'dead'
  returning j.* into v_job;

  if not found then
    return;
  end if;

  return next v_job;
end
$fn$;

comment on function public.retry_dead_job(uuid) is
  'dead 잡을 attempts 0으로 되돌려 다시 큐에 올린다. dead가 아니면 0행 no-op이라 중복 클릭이 안전하다. 잡이 없거나 editor 미만이면 42501. authenticated 전용.';


-- -----------------------------------------------------------------------------
-- 7. enum_check_values — Python enum ↔ DB CHECK 대조용 카탈로그 읽기 (COMP-02)
--
-- pg_constraint는 공개 카탈로그이므로 security definer가 필요 없습니다.
-- security invoker로 두면 이 함수가 권한 상승 표면이 되지 않습니다.
--
-- 소비자: apps/worker의 기동 시 enum 대조 가드. 워커가 아는 값 집합과 DB의 CHECK가
-- 어긋난 채로 뜨면 잘못된 값의 INSERT가 런타임 한복판에서 23514로 처음 드러납니다.
--
-- ⚠️ 정의 문자열에 'ANY (ARRAY[' 형태가 있는 CHECK만 봅니다. 이 필터가 없으면
--    같은 컬럼을 언급하는 다른 CHECK의 리터럴이 섞입니다 — 예를 들어
--    jobs_lock_consistency(0003:65-68)는 status를 언급하며 'running'을 담고 있어,
--    필터 없이는 그 값이 열거의 일부인 것처럼 보입니다. 지금은 우연히 같은 집합에
--    들어 있지만 우연에 기대면 다음 CHECK 하나가 워커 기동을 깹니다.
-- ⚠️ 열거가 아닌 컬럼(jobs.type은 의도적으로 CHECK 열거가 없습니다, 0003:31-36)이나
--    존재하지 않는 컬럼에는 null이 아니라 빈 배열을 돌려줍니다. null을 돌려주면
--    호출자가 "열거 없음"과 "조회 실패"를 구분할 수 없습니다.
-- ⚠️ p_column을 정규식에 끼워 넣으므로 메타문자가 든 이름은 의도대로 동작하지
--    않습니다. 이 함수는 service_role 전용이고 호출자는 상수 컬럼명을 넘깁니다.
-- -----------------------------------------------------------------------------
create or replace function public.enum_check_values(
  p_table  text,
  p_column text
)
returns text[]
language sql
stable
security invoker
set search_path = public
as $$
  select coalesce(
    array(
      select distinct m[1]
      from pg_constraint c
      join pg_class     t on t.oid = c.conrelid
      join pg_namespace n on n.oid = t.relnamespace
      cross join lateral regexp_matches(
        pg_get_constraintdef(c.oid), '''([^'']*)''', 'g'
      ) as m
      where n.nspname = 'public'
        and t.relname = p_table
        and c.contype = 'c'
        and pg_get_constraintdef(c.oid) ~ ('\m' || p_column || '\M')
        and pg_get_constraintdef(c.oid) like '%ANY (ARRAY[%'
      order by 1
    ),
    array[]::text[]
  );
$$;

comment on function public.enum_check_values(text, text) is
  'public 스키마 테이블 컬럼의 CHECK 열거값을 정렬·중복 제거한 text[]로 돌려준다. 열거가 없으면 빈 배열이다. 소비자는 apps/worker의 기동 시 enum 대조 가드(COMP-02). service_role 전용.';


-- -----------------------------------------------------------------------------
-- 8. 권한
--
-- 0007 §8의 방향을 이 파일이 만든 객체 전부에 대해 반복합니다.
--
-- ⚠️ 함수 revoke 대상에 service_role을 명시적으로 넣습니다. 0003·0007·0008은
--    `from public, anon, authenticated`만 썼는데, 클라우드의 pg_default_acl에는
--    로컬에 없는 (public, f, postgres) 항목이 있어 새 함수에 service_role EXECUTE를
--    기본 부여합니다. 그 결과 0008의 search_chunks가 클라우드에서만 service_role에
--    열린 채 남았습니다. 아래 마지막 두 줄이 그것을 정정합니다.
--    실측 방법: 원격 카탈로그를 직접 조회할 것 — CI는 소스만 읽고 psql 러너는
--    로컬 DB만 봅니다. 어느 자동 게이트도 이 차이를 잡지 못합니다.
--
-- 새 테이블은 pg_default_acl에서 다시 Dxtm(TRUNCATE 포함)을 물려받습니다.
-- TRUNCATE는 RLS를 우회하므로 워크스페이스가 아니라 테이블 전체가 사라집니다.
-- 아래 revoke가 그것까지 함께 걷어냅니다.
--
-- usage_events는 감사 기록이라 UPDATE/DELETE를 어느 롤에도 주지 않습니다.
-- authenticated는 SELECT만(자기 워크스페이스 지출을 보는 것은 정상 경로),
-- service_role은 SELECT/INSERT만(워커가 기록을 만든다).
-- -----------------------------------------------------------------------------
revoke all on table public.usage_events from public, anon, authenticated, service_role;

grant select         on table public.usage_events to authenticated;
grant select, insert on table public.usage_events to service_role;

-- 워커 전용 함수 3종. 사용자 롤에는 주지 않습니다 — PostgREST /rpc/로 열리면
-- 아무나 남의 잡을 데드레터로 보내거나 취소할 수 있습니다.
revoke all on function public.dead_letter_job(uuid, text, text) from public, anon, authenticated, service_role;
revoke all on function public.cancel_job(uuid, text)            from public, anon, authenticated, service_role;
revoke all on function public.enum_check_values(text, text)     from public, anon, authenticated, service_role;

grant execute on function public.dead_letter_job(uuid, text, text) to service_role;
grant execute on function public.cancel_job(uuid, text)            to service_role;
grant execute on function public.enum_check_values(text, text)     to service_role;

-- 사용자 RPC 3종은 방향이 반대입니다. 셋 다 security definer라 본문이 스스로
-- has_workspace_role로 격리를 강제하며, 그 확인의 기준은 auth.uid()입니다.
-- BYPASSRLS인 service_role이 이 함수를 부르면 auth.uid()가 null이라 멤버십 확인이
-- 항상 거짓이 되어 아무 일도 못 하거나, 우회 경로를 찾게 만드는 유혹이 됩니다.
-- 그래서 service_role에는 주지 않습니다 — 워커는 jobs에 직접 INSERT 권한이 있습니다.
revoke all on function public.enqueue_source_job(uuid, uuid) from public, anon, authenticated, service_role;
revoke all on function public.request_job_cancel(uuid)       from public, anon, authenticated, service_role;
revoke all on function public.retry_dead_job(uuid)           from public, anon, authenticated, service_role;

grant execute on function public.enqueue_source_job(uuid, uuid) to authenticated;
grant execute on function public.request_job_cancel(uuid)       to authenticated;
grant execute on function public.retry_dead_job(uuid)           to authenticated;

-- 0008이 클라우드에서 놓친 정정. 0008은 이미 push되어 소급 수정할 수 없으므로
-- 여기서 앞으로 나아가는 방식으로 닫습니다. search_chunks는 요청자 JWT의
-- authenticated로 불려야 RLS가 격리를 강제합니다 — BYPASSRLS인 service_role이
-- 부르면 워크스페이스 필터가 애플리케이션 코드 한 줄에만 의존하게 됩니다.
-- 로컬에서는 이미 없는 권한이라 이 revoke가 no-op이고, 클라우드에서만 실제로
-- 걷어냅니다. 양쪽에서 결과 상태가 같아지는 것이 목적입니다.
revoke execute on function public.search_chunks(uuid, extensions.vector, int) from service_role;


-- -----------------------------------------------------------------------------
-- 9. PostgREST 스키마 캐시 갱신
--
-- 갱신 전에는 새 함수 호출이 PGRST202로 떨어집니다. 사용자 RPC 3종은 PostgREST
-- /rpc/ 경로로 불리므로 이 한 줄이 없으면 이 마이그레이션의 절반이 없는 것과 같습니다.
-- -----------------------------------------------------------------------------
notify pgrst, 'reload schema';

commit;
