-- =============================================================================
-- NexusWiki 0003: 잡 큐
--
-- 관련 태스크: P1-DB-03 (소비자는 P2-JOB-01 워커, 생산자는 P2-ING-01 수집 API)
-- 설계 근거:  checklists.json > decisions.job_queue
--             (Postgres 테이블 + FOR UPDATE SKIP LOCKED 폴링. 새 인프라 0,
--              잡 상태를 그대로 프론트에 노출, 재시도/데드레터가 투명)
--
-- 상태 전이
--
--   queued ──claim──> running ──complete──> succeeded
--     ^                  │
--     │                  ├──fail (attempts < max)──> failed ──run_after 경과──┐
--     │                  └──fail (attempts >= max)──> dead                    │
--     └────────────────────────── reap (락 타임아웃) ───────────────────────────┘
--
-- 'failed'는 종착점이 아니라 "직전 시도 실패, 백오프 후 재시도 예정"입니다.
-- 사람이 손대야 하는 종착점은 'dead' 하나뿐입니다.
-- 둘을 나눠 두면 프론트가 "3번 중 2번째 실패, 4분 후 재시도"를 그대로 보여줄 수
-- 있습니다 (decisions.job_queue의 "잡 상태를 그대로 프론트에 노출").
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. jobs
-- -----------------------------------------------------------------------------
create table public.jobs (
  id           uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,

  -- 잡 종류. 의도적으로 CHECK 열거를 걸지 않았습니다.
  -- 0001/0002는 도메인 값에 전부 CHECK를 걸었지만, 잡 종류만은 Phase 2에서
  -- 파이프라인을 쪼개고 합치며 계속 바뀝니다(현재 계획서가 명시하는 건 'compile'
  -- 하나뿐). DB에 열거를 박으면 잡 하나 추가할 때마다 마이그레이션이 필요합니다.
  -- 대신 P2-JOB-01 워커가 자기 핸들러 레지스트리에 없는 type을 만나면
  -- 즉시 dead로 보내고 last_error에 남기도록 하세요 — 오타는 그 경로로 잡힙니다.
  type text not null check (char_length(btrim(type)) > 0),

  status text not null default 'queued'
    check (status in ('queued', 'running', 'succeeded', 'failed', 'dead')),

  payload jsonb not null default '{}',

  -- claim 시점에 증가합니다(실패 시점이 아니라).
  -- 워커가 잡을 물고 죽어도 reap 후 재시도에서 소진되므로,
  -- 워커를 죽이는 독약 잡(poison pill)이 무한 루프를 돌지 않습니다.
  attempts     int not null default 0 check (attempts >= 0),
  max_attempts int not null default 3 check (max_attempts >= 1),
  last_error   text,

  -- 재시도 백오프 스케줄. 폴링은 run_after <= now() 인 것만 집어갑니다.
  -- 기본값이 now()이므로 새 잡은 곧바로 대상이 되고, 그 결과 run_after 정렬이
  -- 신규 잡에 대해서는 그대로 FIFO가 됩니다.
  run_after timestamptz not null default now(),

  -- 락 소유자. 워커 인스턴스 식별자(호스트+PID 등). 회수 판정은 locked_at 기준.
  locked_at timestamptz,
  locked_by text,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  -- running이면 락 정보가 있어야 하고, running이 아니면 없어야 합니다.
  -- 회수/완료 처리가 락을 지우지 않고 빠져나가는 버그를 DB가 막습니다.
  constraint jobs_lock_consistency check (
    (status = 'running' and locked_at is not null and locked_by is not null)
    or (status <> 'running' and locked_at is null and locked_by is null)
  )
);

create trigger jobs_set_updated_at
  before update on public.jobs
  for each row execute function public.set_updated_at();

-- 워커 폴링 경로. claim_job()의 where/order by와 정확히 같은 모양이어야
-- 부분 인덱스가 적용됩니다.
create index jobs_poll_idx
  on public.jobs (run_after, created_at)
  where status in ('queued', 'failed');

-- 프론트의 잡 목록/상태 조회 (P2-API-01, P3-UI-01)
create index jobs_workspace_created_idx
  on public.jobs (workspace_id, created_at desc);

-- 유실된 락 회수 스캔 (P2-JOB-01)
create index jobs_stale_lock_idx
  on public.jobs (locked_at)
  where status = 'running';


-- -----------------------------------------------------------------------------
-- 2. 큐 조작 함수
--
-- 전부 service_role 전용입니다 (decisions.db_access: 워커만 service_role).
-- 파일 끝에서 anon/authenticated의 EXECUTE를 회수합니다 — Supabase는 public
-- 스키마 함수에 기본 실행 권한을 주므로, 놔두면 PostgREST의 /rpc/ 로 아무나
-- 남의 워크스페이스 잡을 집어가거나 죽일 수 있습니다.
-- -----------------------------------------------------------------------------

-- 잡 하나를 원자적으로 점유합니다. 동시에 폴링하는 워커들은
-- FOR UPDATE SKIP LOCKED 덕분에 서로 다른 행을 가져갑니다(대기하지 않음).
-- p_types가 NULL이면 모든 종류를 대상으로 합니다.
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
  set status    = 'running',
      locked_at = now(),
      locked_by = p_worker_id,
      attempts  = j.attempts + 1
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

comment on function public.claim_job(text, text[]) is
  '잡 하나를 점유(running)하고 반환. 동시 폴링 시 SKIP LOCKED로 중복 점유 없음. service_role 전용.';


-- 성공 처리. 락을 반드시 함께 비웁니다(jobs_lock_consistency).
create or replace function public.complete_job(p_job_id uuid)
returns public.jobs
language sql
volatile
set search_path = public
as $$
  update public.jobs
  set status     = 'succeeded',
      last_error = null,
      locked_at  = null,
      locked_by  = null
  where id = p_job_id and status = 'running'
  returning *;
$$;


-- 실패 처리. 남은 시도가 있으면 지수 백오프로 재예약(failed),
-- 소진했으면 데드레터(dead).
--
-- attempts는 claim에서 이미 증가했으므로 여기서는 판정만 합니다.
-- 백오프: base * 2^(attempts-1), 상한 p_max_backoff.
--   base=30s 기준 1회차 실패 후 30초, 2회차 60초, 3회차 120초...
create or replace function public.fail_job(
  p_job_id      uuid,
  p_error       text,
  p_backoff     interval default interval '30 seconds',
  p_max_backoff interval default interval '1 hour'
)
returns public.jobs
language sql
volatile
set search_path = public
as $$
  update public.jobs
  set status     = case when attempts >= max_attempts then 'dead' else 'failed' end,
      last_error = p_error,
      run_after  = case
                     when attempts >= max_attempts then run_after
                     else now() + least(p_backoff * power(2, attempts - 1), p_max_backoff)
                   end,
      locked_at  = null,
      locked_by  = null
  where id = p_job_id and status = 'running'
  returning *;
$$;


-- 유실된 락 회수. 워커가 잡을 물고 죽으면 그 행은 영원히 running으로 남습니다.
-- locked_at이 p_timeout보다 오래된 running 잡을 큐로 되돌립니다.
-- attempts는 claim에서 이미 소진됐으므로 재시도 횟수가 정직하게 유지됩니다.
--
-- ⚠️ p_timeout은 정상 잡의 최장 실행 시간보다 넉넉해야 합니다.
--    짧으면 살아 있는 워커의 잡을 뺏어 같은 잡이 두 번 처리됩니다.
--    LLM 컴파일 잡은 수 분이 걸릴 수 있으므로 기본 15분으로 잡았습니다.
create or replace function public.reap_stale_jobs(
  p_timeout interval default interval '15 minutes'
)
returns setof public.jobs
language sql
volatile
set search_path = public
as $$
  update public.jobs j
  set status     = case when j.attempts >= j.max_attempts then 'dead' else 'queued' end,
      last_error = coalesce(j.last_error || E'\n', '')
                   || '[reaped] worker ' || coalesce(j.locked_by, '?')
                   || ' 가 ' || j.locked_at::text || ' 이후 응답 없음',
      locked_at  = null,
      locked_by  = null
  where j.id in (
    select c.id from public.jobs c
    where c.status = 'running' and c.locked_at < now() - p_timeout
    for update skip locked
  )
  returning j.*;
$$;


-- -----------------------------------------------------------------------------
-- 3. 권한
--
-- Supabase는 public 스키마의 새 함수에 anon/authenticated 실행 권한을
-- 기본 부여합니다. 큐 조작 함수는 SECURITY INVOKER지만, 사용자 롤에게
-- jobs의 RLS 정책이 붙는 순간(0004) 자기 워크스페이스 잡을 임의로
-- 점유/삭제할 수 있게 됩니다. 애초에 노출하지 않습니다.
-- -----------------------------------------------------------------------------
revoke all on function public.claim_job(text, text[])                      from public, anon, authenticated;
revoke all on function public.complete_job(uuid)                           from public, anon, authenticated;
revoke all on function public.fail_job(uuid, text, interval, interval)     from public, anon, authenticated;
revoke all on function public.reap_stale_jobs(interval)                    from public, anon, authenticated;

grant execute on function public.claim_job(text, text[])                   to service_role;
grant execute on function public.complete_job(uuid)                        to service_role;
grant execute on function public.fail_job(uuid, text, interval, interval)  to service_role;
grant execute on function public.reap_stale_jobs(interval)                 to service_role;


-- -----------------------------------------------------------------------------
-- RLS: 정책 없이 활성화 = 전면 거부 (0001/0002와 동일)
-- 0004에서 "멤버는 자기 워크스페이스 잡을 SELECT" 정책만 부여할 예정입니다.
-- 잡의 생성/전이는 전부 서버(service_role) 경로입니다.
-- -----------------------------------------------------------------------------
alter table public.jobs enable row level security;
