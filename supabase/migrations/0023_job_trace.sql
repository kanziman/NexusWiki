-- =============================================================================
-- NexusWiki 0023: 잡 체인의 trace 연속성과 시작 시각
--
-- 관련 이슈: #160
-- 설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D1, D3
-- 계약:     openspec/changes/ai-control-flow-accounting/specs/ai-request-tracing/spec.md
--
-- 전부 추가 전용입니다. 컬럼은 null을 허용하고 새 인자에는 기본값이 있으므로, 이 파일을
-- 적용한 뒤에도 이전 버전 코드가 그대로 동작합니다.
-- =============================================================================

begin;


-- -----------------------------------------------------------------------------
-- 1. 컬럼
-- -----------------------------------------------------------------------------

-- null을 허용합니다. 이전에 만들어진 잡과 원문 삭제가 만드는 Storage 정리 잡에는 값이 없습니다.
-- not null로 두면 그 잡들의 인큐가 실패합니다.
alter table public.jobs
  add column trace_id uuid,
  -- 완료 처리는 locked_at을 지우므로(jobs_lock_consistency) 그것만으로는 소요 시간을 잴 수 없습니다.
  add column last_claimed_at timestamptz;

-- 부분 인덱스입니다. 값이 없는 과거 행을 색인해 봐야 조회할 일이 없습니다.
create index jobs_workspace_trace_idx
  on public.jobs (workspace_id, trace_id)
  where trace_id is not null;

comment on column public.jobs.trace_id is
  '이 잡을 시작한 요청의 trace. 후속 단계는 complete_job_and_chain이 물려받는다. 재시도·회수·반납은 값을 바꾸지 않는다.';
comment on column public.jobs.last_claimed_at is
  '가장 최근 claim 시각. 완료 후에도 남으므로 updated_at과 함께 마지막 시도의 소요 시간을 계산한다.';


-- -----------------------------------------------------------------------------
-- 2. claim_job — 시작 시각 기록
-- -----------------------------------------------------------------------------
create or replace function public.claim_job(
  p_worker_id text,
  p_types     text[] default null
)
returns setof public.jobs
language sql
volatile
set search_path = public
as $$
  update public.jobs j
  set status          = 'running',
      locked_at       = now(),
      locked_by       = p_worker_id,
      last_claimed_at = now(),
      attempts        = j.attempts + 1
  where j.id = (
    select c.id
    from public.jobs c
    where c.status in ('queued', 'failed')
      and c.run_after <= now()
      and (p_types is null or c.type = any (p_types))
    order by c.run_after, c.created_at
    for update skip locked
    limit 1
  )
  returning j.*;
$$;


-- -----------------------------------------------------------------------------
-- 3. complete_job_and_chain — 후속 잡이 trace를 물려받는다
--
-- ⚠️ 핸들러의 next_payload로 전달하지 않습니다. 핸들러 다섯 곳 중 하나만 빠져도 추적이
--    예외 없이 조용히 끊기기 때문입니다. SQL에서 복사하면 누락할 수 없습니다.
-- -----------------------------------------------------------------------------
create or replace function public.complete_job_and_chain(
  p_job_id       uuid,
  p_next_type    text  default null,
  p_next_payload jsonb default '{}'::jsonb
)
returns setof public.jobs
language plpgsql
volatile
set search_path = public
as $fn$
declare
  v_job public.jobs;
begin
  update public.jobs j
  set status     = 'succeeded',
      last_error = null,
      locked_at  = null,
      locked_by  = null
  where j.id = p_job_id and j.status = 'running'
  returning j.* into v_job;

  -- 0행이면 다음 잡을 인큐하지 않고 그대로 빠져나갑니다.
  if not found then
    return;
  end if;

  if p_next_type is not null then
    insert into public.jobs (workspace_id, type, payload, trace_id)
    values (
      v_job.workspace_id,
      p_next_type,
      coalesce(p_next_payload, '{}'::jsonb),
      v_job.trace_id
    )
    on conflict do nothing;
  end if;

  return next v_job;
end
$fn$;


-- -----------------------------------------------------------------------------
-- 4. enqueue_source_job — trace 인자 추가
--
-- ⚠️ create or replace만 쓰면 2인자 함수가 오버로드로 남아 PostgREST 호출이 모호해집니다.
--    그래서 지우고 다시 만들며, 그 결과 권한도 다시 부여합니다.
-- -----------------------------------------------------------------------------
drop function public.enqueue_source_job(uuid, uuid);

create function public.enqueue_source_job(
  p_workspace_id  uuid,
  p_raw_source_id uuid,
  p_trace_id      uuid default null
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
  if not public.has_workspace_role(p_workspace_id, 'editor') then
    raise exception '워크스페이스에 대한 편집 권한이 없습니다'
      using errcode = '42501';
  end if;

  if not exists (
    select 1 from public.raw_sources r
    where r.id = p_raw_source_id
      and r.workspace_id = p_workspace_id
  ) then
    raise exception '워크스페이스에 대한 편집 권한이 없습니다'
      using errcode = '42501';
  end if;

  select coalesce(sum(u.cost_micros), 0) into v_spent
  from public.usage_events u
  where u.workspace_id = p_workspace_id
    and u.occurred_at >= (date_trunc('month', now() at time zone 'utc') at time zone 'utc');

  select w.monthly_budget_micros into v_cap
  from public.workspaces w
  where w.id = p_workspace_id;

  if v_spent >= v_cap then
    raise exception '월 비용 상한 초과 (사용 %, 상한 %)', v_spent, v_cap
      using errcode = 'NW402';
  end if;

  insert into public.jobs (workspace_id, type, payload, trace_id)
  values (
    p_workspace_id,
    'parse',
    jsonb_build_object(
      'target_id',     p_raw_source_id::text,
      'raw_source_id', p_raw_source_id::text
    ),
    p_trace_id
  )
  on conflict do nothing
  returning * into v_job;

  -- 중복 인큐는 기존 잡을 그대로 돌려줍니다. 기존 잡의 trace를 덮어쓰지 않습니다.
  if not found then
    select * into v_job
    from public.jobs j
    where j.workspace_id = p_workspace_id
      and j.type = 'parse'
      and j.payload ->> 'target_id' = p_raw_source_id::text
      and j.status in ('queued', 'running', 'failed')
    limit 1;
  end if;

  if v_job.id is null then
    return;
  end if;

  return next v_job;
end
$fn$;

comment on function public.enqueue_source_job(uuid, uuid, uuid) is
  '사용자 경로의 유일한 parse 잡 인큐 통로. editor 이상 멤버십과 raw_source 소유권을 확인하고(위반은 42501) 이번 달 usage_events 합이 workspaces.monthly_budget_micros 이상이면 NW402으로 거부한다. 같은 대상으로 다시 부르면 새 잡을 만들지 않고 기존 잡을 돌려주며 기존 trace를 바꾸지 않는다. authenticated 전용 — service_role에는 EXECUTE를 주지 않는다.';

-- ⚠️ 새로 만든 함수에는 기본 권한이 다시 붙습니다. 회수하지 않으면 anon이 실행할 수 있습니다.
revoke all on function public.enqueue_source_job(uuid, uuid, uuid) from public, anon, authenticated, service_role;
grant execute on function public.enqueue_source_job(uuid, uuid, uuid) to authenticated;


notify pgrst, 'reload schema';

commit;
