-- =============================================================================
-- NexusWiki 0010: 비용 상한 거부용 프로젝트 SQLSTATE
--
-- 관련 태스크: P2-ING-01 · OPS-01
-- 설계 근거: 03-05 회귀 — PostgREST는 클래스 53(53400)을 opaque 500으로 숨긴다.
-- =============================================================================

begin;

-- `53400`은 insufficient_resources 클래스라 PostgREST가 SQLSTATE와 본문을 숨긴다.
-- NW402는 PostgreSQL 예약 클래스가 아닌 프로젝트 전용 코드다. 따라서 `api.errors`가
-- 이를 402로 매핑해도 진짜 데이터베이스 자원 장애를 예산 초과로 오인할 수 없다.
-- HTTP 상태 코드의 소유자는 계속 API의 단일 등록 지점(`api.errors`)에 남긴다.
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

comment on function public.enqueue_source_job(uuid, uuid) is
  '사용자 경로의 유일한 parse 잡 인큐 통로. editor 이상 멤버십과 raw_source 소유권을 확인하고(위반은 42501) 이번 달 usage_events 합이 workspaces.monthly_budget_micros 이상이면 NW402으로 거부한다. 같은 대상으로 다시 부르면 새 잡을 만들지 않고 기존 잡을 돌려준다. authenticated 전용 — service_role에는 EXECUTE를 주지 않는다.';

commit;
