-- =============================================================================
-- NexusWiki 0009 검증: 파이프라인 운영 표면 계약
--   (dead_letter_job · cancel_job · request_job_cancel · retry_dead_job ·
--    enqueue_source_job · enum_check_values · usage_events 권한)
--
-- 관련 태스크: P2-JOB-01 · P2-ING-01 · P4-OPS-01 (소비자는 03-03 이후의 워커·라우터)
-- 설계 근거:  03-CONTEXT.md > D-03
--             03-02-PLAN.md > D-P1, D-P2, D-P3
--
-- ⚠️ 이 파일은 마이그레이션이 아닙니다. supabase/migrations/ 밖에 있으므로
--    supabase db reset이 적용하지 않으며 마이그레이션 순서에도 들어가지 않습니다.
--    0007_queue_functions.sql·0008_search_contract.sql과 같은 자리, 같은 관례입니다.
--
-- 전체가 하나의 트랜잭션이고 마지막이 rollback이므로 픽스처 행은 남지 않습니다.
-- 남기면 jobs_dedup_idx(0007 섹션 2)가 다음 실행의 인큐를 막습니다.
--
-- ⚠️ 멤버십을 요구하는 security definer 함수 3종(enqueue_source_job ·
--    request_job_cancel · retry_dead_job)을 psql의 postgres 롤에서 그냥 부르면
--    auth.uid()가 null이라 has_workspace_role이 **항상 거짓**이 되어 무엇을 넣든
--    42501이 돌아옵니다. 계약이 깨져서가 아니라 호출 컨텍스트가 없어서입니다.
--    그래서 이 파일은 그 3종을 호출하기 전에
--      set local role authenticated;
--      set local request.jwt.claims = '{"sub":"<픽스처 사용자 uuid>", ...}';
--    를 세우고, 블록을 나올 때 reset role; 합니다. jobs·usage_events를 직접
--    읽는 단언은 RLS를 피해 postgres 롤로 되돌아온 뒤에 합니다.
--
-- 픽스처 UUID는 0007·0008과 겹치지 않도록 마지막 두 자리를 21부터 씁니다.
--   10000000-…  사용자 / 20000000-…  워크스페이스
--   30000000-…  잡     / 40000000-…  raw_sources
--
-- 실행
--   cat supabase/tests/0009_pipeline_ops.sql \
--     | docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1
-- =============================================================================

begin;

insert into auth.users (id, email)
values ('10000000-0000-0000-0000-000000000021', 'pipeline@example.test');

-- 소유자 멤버십은 workspaces_add_owner_member 트리거가 자동으로 만듭니다(role=owner).
insert into public.workspaces (id, name, owner_id)
values
  ('20000000-0000-0000-0000-000000000021', '큐·취소 계약',   '10000000-0000-0000-0000-000000000021'),
  ('20000000-0000-0000-0000-000000000022', '인큐 멱등성',     '10000000-0000-0000-0000-000000000021'),
  ('20000000-0000-0000-0000-000000000023', '상한 경계',       '10000000-0000-0000-0000-000000000021'),
  ('20000000-0000-0000-0000-000000000024', '빈 워크스페이스', '10000000-0000-0000-0000-000000000021'),
  ('20000000-0000-0000-0000-000000000025', '남의 워크스페이스', '10000000-0000-0000-0000-000000000021'),
  ('20000000-0000-0000-0000-000000000026', '월 경계',         '10000000-0000-0000-0000-000000000021');

-- 잡 종류를 테스트마다 다르게 둡니다. claim_job은 종류만 맞으면 워크스페이스를
-- 가리지 않고 가장 오래된 것을 집으므로, 같은 종류를 나눠 쓰면 어느 잡이 집혔는지가
-- 픽스처 삽입 순서에 의존하게 됩니다.
insert into public.jobs (id, workspace_id, type, payload)
values
  ('30000000-0000-0000-0000-000000000021', '20000000-0000-0000-0000-000000000021', 't1-dead',    '{"target_id": "t-21"}'),
  ('30000000-0000-0000-0000-000000000022', '20000000-0000-0000-0000-000000000021', 't2-cancel',  '{"target_id": "t-22"}'),
  ('30000000-0000-0000-0000-000000000023', '20000000-0000-0000-0000-000000000021', 't3-running', '{"target_id": "t-23"}'),
  ('30000000-0000-0000-0000-000000000024', '20000000-0000-0000-0000-000000000021', 't8-retry',   '{"target_id": "t-24"}'),
  ('30000000-0000-0000-0000-000000000025', '20000000-0000-0000-0000-000000000021', 't8-done',    '{"target_id": "t-25"}');

insert into public.raw_sources (id, workspace_id, title, source_type, content, content_hash)
values
  ('40000000-0000-0000-0000-000000000021', '20000000-0000-0000-0000-000000000022', '멱등성 소스', 'text', '본문', 'hash-21'),
  ('40000000-0000-0000-0000-000000000022', '20000000-0000-0000-0000-000000000023', '상한 소스 A', 'text', '본문', 'hash-22'),
  ('40000000-0000-0000-0000-000000000023', '20000000-0000-0000-0000-000000000023', '상한 소스 B', 'text', '본문', 'hash-23'),
  ('40000000-0000-0000-0000-000000000024', '20000000-0000-0000-0000-000000000024', '빈 워크스페이스 소스', 'text', '본문', 'hash-24'),
  ('40000000-0000-0000-0000-000000000025', '20000000-0000-0000-0000-000000000025', '남의 소스', 'text', '본문', 'hash-25');


-- -----------------------------------------------------------------------------
-- T1: dead_letter_job 락 소유자 술어 (T-03-10)
--
-- w1이 점유한 잡을 w2가 dead로 만들 수 없어야 한다. 이 술어가 빠지면 reap이 이미
-- 락을 뺏은 뒤 늦게 깨어난 워커가, 그 사이 다른 워커가 정상 처리 중인 잡을
-- dead로 만든다. 마지막 재호출 0행은 at-least-once 재시도가 예외로 죽지 않음을
-- 함께 고정한다.
-- -----------------------------------------------------------------------------
do $t1$
declare
  v_rows int;
  v      public.jobs;
begin
  select * into v from public.claim_job('w1', array['t1-dead']);
  if v.id <> '30000000-0000-0000-0000-000000000021' or v.status <> 'running' or v.locked_by <> 'w1' then
    raise exception 'T1 준비: claim이 어긋났습니다 (id=%, status=%, locked_by=%)', v.id, v.status, v.locked_by;
  end if;

  -- 남의 워커: 0행이고 잡은 그대로여야 한다.
  select count(*) into v_rows from public.dead_letter_job(
    '30000000-0000-0000-0000-000000000021', 'w2', '남의 잡'
  );
  if v_rows <> 0 then
    raise exception 'T1: 다른 워커(w2)의 dead_letter_job이 %행을 바꿨습니다 (기대 0)', v_rows;
  end if;

  select * into v from public.jobs where id = '30000000-0000-0000-0000-000000000021';
  if v.status <> 'running' or v.locked_by <> 'w1' then
    raise exception 'T1: w2 호출 뒤 잡이 변했습니다 (status=%, locked_by=%)', v.status, v.locked_by;
  end if;

  -- 락 소유자: 1행이고 dead + 락 해제.
  select count(*) into v_rows from public.dead_letter_job(
    '30000000-0000-0000-0000-000000000021', 'w1', 'boom'
  );
  if v_rows <> 1 then
    raise exception 'T1: 락 소유자의 dead_letter_job이 %행을 바꿨습니다 (기대 1)', v_rows;
  end if;

  select * into v from public.jobs where id = '30000000-0000-0000-0000-000000000021';
  if v.status <> 'dead' or v.last_error <> 'boom'
     or v.locked_at is not null or v.locked_by is not null then
    raise exception 'T1: dead 전이 뒤 상태가 어긋났습니다 (status=%, last_error=%, locked_at=%, locked_by=%)',
      v.status, v.last_error, v.locked_at, v.locked_by;
  end if;

  -- 재호출: 예외가 아니라 0행 no-op.
  select count(*) into v_rows from public.dead_letter_job(
    '30000000-0000-0000-0000-000000000021', 'w1', 'boom'
  );
  if v_rows <> 0 then
    raise exception 'T1: 이미 dead인 잡의 재호출이 %행을 바꿨습니다 (기대 0)', v_rows;
  end if;
end
$t1$;


-- -----------------------------------------------------------------------------
-- T2: request_job_cancel — queued 잡은 즉시 canceled (03-02-PLAN.md > D-P3)
-- -----------------------------------------------------------------------------
set local role authenticated;
set local request.jwt.claims = '{"sub":"10000000-0000-0000-0000-000000000021","role":"authenticated"}';

do $t2a$
declare
  v_rows int;
  v      public.jobs;
begin
  select count(*) into v_rows from public.request_job_cancel('30000000-0000-0000-0000-000000000022');
  if v_rows <> 1 then
    raise exception 'T2: queued 잡의 request_job_cancel이 %행을 돌려줬습니다 (기대 1)', v_rows;
  end if;

  select * into v from public.request_job_cancel('30000000-0000-0000-0000-000000000022');
  if v.id is not null then
    raise exception 'T2: 이미 canceled인 잡의 재호출이 행을 돌려줬습니다 (기대 0행)';
  end if;
end
$t2a$;

reset role;

do $t2b$
declare
  v      public.jobs;
  v_rows int;
begin
  select * into v from public.jobs where id = '30000000-0000-0000-0000-000000000022';
  if v.status <> 'canceled' or v.cancel_requested_at is null
     or v.locked_at is not null or v.locked_by is not null then
    raise exception 'T2: 취소 뒤 상태가 어긋났습니다 (status=%, cancel_requested_at=%, locked_at=%, locked_by=%)',
      v.status, v.cancel_requested_at, v.locked_at, v.locked_by;
  end if;

  -- canceled 잡은 claim_job의 status in ('queued','failed') 술어에 걸리지 않는다.
  select count(*) into v_rows from public.claim_job('w1', array['t2-cancel']);
  if v_rows <> 0 then
    raise exception 'T2: claim_job이 canceled 잡을 %개 집었습니다 (기대 0)', v_rows;
  end if;
end
$t2b$;


-- -----------------------------------------------------------------------------
-- T3: 협조적 취소 — running 잡은 cancel_requested_at만 찍히고,
--     락 소유자만 cancel_job으로 마감할 수 있으며, 체인이 이어지지 않는다.
-- -----------------------------------------------------------------------------
do $t3a$
declare
  v public.jobs;
begin
  select * into v from public.claim_job('w1', array['t3-running']);
  if v.id <> '30000000-0000-0000-0000-000000000023' or v.status <> 'running' then
    raise exception 'T3 준비: claim이 어긋났습니다 (id=%, status=%)', v.id, v.status;
  end if;
end
$t3a$;

set local role authenticated;
set local request.jwt.claims = '{"sub":"10000000-0000-0000-0000-000000000021","role":"authenticated"}';

do $t3b$
declare
  v_rows int;
begin
  select count(*) into v_rows from public.request_job_cancel('30000000-0000-0000-0000-000000000023');
  if v_rows <> 1 then
    raise exception 'T3: running 잡의 request_job_cancel이 %행을 돌려줬습니다 (기대 1)', v_rows;
  end if;
end
$t3b$;

reset role;

do $t3c$
declare
  v_rows int;
  v_next int;
  v      public.jobs;
begin
  -- 협조적: 상태는 아직 running이고 요청 시각만 찍혔다.
  select * into v from public.jobs where id = '30000000-0000-0000-0000-000000000023';
  if v.status <> 'running' or v.cancel_requested_at is null or v.locked_by <> 'w1' then
    raise exception 'T3: running 잡이 즉시 전이됐습니다 (status=%, cancel_requested_at=%, locked_by=%)',
      v.status, v.cancel_requested_at, v.locked_by;
  end if;

  -- 남의 워커는 마감할 수 없다.
  select count(*) into v_rows from public.cancel_job('30000000-0000-0000-0000-000000000023', 'w2');
  if v_rows <> 0 then
    raise exception 'T3: 다른 워커(w2)의 cancel_job이 %행을 바꿨습니다 (기대 0)', v_rows;
  end if;

  -- 락 소유자가 마감한다.
  select count(*) into v_rows from public.cancel_job('30000000-0000-0000-0000-000000000023', 'w1');
  if v_rows <> 1 then
    raise exception 'T3: 락 소유자의 cancel_job이 %행을 바꿨습니다 (기대 1)', v_rows;
  end if;

  select * into v from public.jobs where id = '30000000-0000-0000-0000-000000000023';
  if v.status <> 'canceled' or v.locked_at is not null or v.locked_by is not null then
    raise exception 'T3: cancel_job 뒤 상태가 어긋났습니다 (status=%, locked_at=%, locked_by=%)',
      v.status, v.locked_at, v.locked_by;
  end if;

  -- 취소된 잡은 체인을 잇지 않는다.
  select count(*) into v_rows from public.complete_job_and_chain(
    '30000000-0000-0000-0000-000000000023',
    't3-next',
    '{"target_id": "t-23-next"}'::jsonb
  );
  if v_rows <> 0 then
    raise exception 'T3: canceled 잡의 complete_job_and_chain이 %행을 돌려줬습니다 (기대 0)', v_rows;
  end if;

  select count(*) into v_next from public.jobs where type = 't3-next';
  if v_next <> 0 then
    raise exception 'T3: 취소된 잡이 다음 잡을 %개 만들었습니다 (기대 0)', v_next;
  end if;
end
$t3c$;


-- -----------------------------------------------------------------------------
-- T4: 인큐 멱등성과 소스 소유권 (T-03-08)
--
-- 같은 대상으로 두 번 부르면 잡이 하나만 생기고 두 호출이 같은 job_id를 돌려준다.
-- 다른 워크스페이스의 raw_source_id로 부르면 42501 — definer가 RLS를 우회하므로
-- 이 확인이 없으면 남의 소스에 대한 잡을 자기 워크스페이스에 만들 수 있다.
-- -----------------------------------------------------------------------------
set local role authenticated;
set local request.jwt.claims = '{"sub":"10000000-0000-0000-0000-000000000021","role":"authenticated"}';

do $t4a$
declare
  v_first  uuid;
  v_second uuid;
  v_state  text := 'none';
begin
  select id into v_first from public.enqueue_source_job(
    '20000000-0000-0000-0000-000000000022', '40000000-0000-0000-0000-000000000021'
  );
  if v_first is null then
    raise exception 'T4: 첫 인큐가 0행이었습니다';
  end if;

  select id into v_second from public.enqueue_source_job(
    '20000000-0000-0000-0000-000000000022', '40000000-0000-0000-0000-000000000021'
  );
  if v_second is distinct from v_first then
    raise exception 'T4: 두 번째 인큐가 다른 잡을 돌려줬습니다 (첫 %, 두 번째 %)', v_first, v_second;
  end if;

  -- 남의 워크스페이스 소스: 존재 여부를 상태로 구분하지 않고 42501.
  begin
    perform public.enqueue_source_job(
      '20000000-0000-0000-0000-000000000022', '40000000-0000-0000-0000-000000000025'
    );
    v_state := 'ok';
  exception when sqlstate '42501' then
    v_state := 'denied';
  end;
  if v_state <> 'denied' then
    raise exception 'T4: 남의 워크스페이스 소스 인큐가 %로 끝났습니다 (기대 denied)', v_state;
  end if;
end
$t4a$;

reset role;

do $t4b$
declare
  v_jobs int;
begin
  select count(*) into v_jobs from public.jobs
  where type = 'parse'
    and payload ->> 'target_id' = '40000000-0000-0000-0000-000000000021';
  if v_jobs <> 1 then
    raise exception 'T4: 같은 대상의 parse 잡이 %개입니다 (기대 1)', v_jobs;
  end if;
end
$t4b$;


-- -----------------------------------------------------------------------------
-- T5: 비용 상한 경계 — 합이 상한과 **같으면 거부**한다 (OPS-01, D-P2)
--
-- 상한 1000 micros. 999에서는 통과하고, 1 micro를 더해 정확히 1000이 되면 53400.
-- "같으면 통과"로 잘못 구현하면 이 두 단언 중 뒤엣것만 깨진다.
-- -----------------------------------------------------------------------------
update public.workspaces
set monthly_budget_micros = 1000
where id = '20000000-0000-0000-0000-000000000023';

insert into public.usage_events (workspace_id, kind, provider, model, cost_micros)
values ('20000000-0000-0000-0000-000000000023', 'llm', 'openrouter', 'test-model', 999);

set local role authenticated;
set local request.jwt.claims = '{"sub":"10000000-0000-0000-0000-000000000021","role":"authenticated"}';

do $t5a$
declare
  v_rows int;
begin
  select count(*) into v_rows from public.enqueue_source_job(
    '20000000-0000-0000-0000-000000000023', '40000000-0000-0000-0000-000000000022'
  );
  if v_rows <> 1 then
    raise exception 'T5: 상한(1000)보다 1 micro 적은 지출(999)에서 인큐가 %행이었습니다 (기대 1)', v_rows;
  end if;
end
$t5a$;

reset role;

-- 합을 정확히 상한과 같게 만든다.
insert into public.usage_events (workspace_id, kind, provider, model, cost_micros)
values ('20000000-0000-0000-0000-000000000023', 'embedding', 'openrouter', 'bge-m3', 1);

set local role authenticated;
set local request.jwt.claims = '{"sub":"10000000-0000-0000-0000-000000000021","role":"authenticated"}';

do $t5b$
declare
  v_state text := 'none';
begin
  begin
    perform public.enqueue_source_job(
      '20000000-0000-0000-0000-000000000023', '40000000-0000-0000-0000-000000000023'
    );
    v_state := 'ok';
  exception when sqlstate '53400' then
    v_state := 'capped';
  end;
  if v_state <> 'capped' then
    raise exception 'T5: 지출이 상한과 정확히 같을 때 인큐가 %로 끝났습니다 (기대 capped — 같으면 거부)', v_state;
  end if;
end
$t5b$;

reset role;

do $t5c$
declare
  v_jobs int;
begin
  select count(*) into v_jobs from public.jobs
  where type = 'parse'
    and payload ->> 'target_id' = '40000000-0000-0000-0000-000000000023';
  if v_jobs <> 0 then
    raise exception 'T5: 상한에 걸린 인큐가 잡을 %개 만들었습니다 (기대 0)', v_jobs;
  end if;
end
$t5c$;


-- -----------------------------------------------------------------------------
-- T6: 빈 워크스페이스 — usage_events가 0행이면 합은 null이 아니라 0이다.
--
-- coalesce가 빠지면 v_spent가 null이 되고 `null >= v_cap`은 null이라 상한 판정이
-- 조용히 통과한다. 기록이 하나도 없는 워크스페이스가 상한 없는 워크스페이스가 된다.
-- -----------------------------------------------------------------------------
do $t6a$
declare
  v_spent bigint;
begin
  select coalesce(sum(u.cost_micros), 0) into v_spent
  from public.usage_events u
  where u.workspace_id = '20000000-0000-0000-0000-000000000024'
    and u.occurred_at >= (date_trunc('month', now() at time zone 'utc') at time zone 'utc');

  if v_spent is null or v_spent <> 0 then
    raise exception 'T6: 기록 없는 워크스페이스의 이번 달 합이 %입니다 (기대 0)', v_spent;
  end if;
end
$t6a$;

set local role authenticated;
set local request.jwt.claims = '{"sub":"10000000-0000-0000-0000-000000000021","role":"authenticated"}';

do $t6b$
declare
  v_rows int;
begin
  select count(*) into v_rows from public.enqueue_source_job(
    '20000000-0000-0000-0000-000000000024', '40000000-0000-0000-0000-000000000024'
  );
  if v_rows <> 1 then
    raise exception 'T6: 기록 없는 워크스페이스의 인큐가 %행이었습니다 (기대 1)', v_rows;
  end if;
end
$t6b$;

reset role;


-- -----------------------------------------------------------------------------
-- T7: 월 경계 — 경계와 정확히 같은 시각의 행은 이번 달에 **포함**된다.
--
-- 경계 비교가 > 였다면 매월 1일 0시 정각에 기록된 사용량이 영원히 어느 달에도
-- 세어지지 않는다. 비교식은 enqueue_source_job의 것과 글자 그대로 같아야 한다.
-- -----------------------------------------------------------------------------
insert into public.usage_events (workspace_id, kind, provider, model, cost_micros, occurred_at)
values
  ('20000000-0000-0000-0000-000000000026', 'llm', 'openrouter', 'test-model', 700,
   (date_trunc('month', now() at time zone 'utc') at time zone 'utc')),
  ('20000000-0000-0000-0000-000000000026', 'llm', 'openrouter', 'test-model', 300,
   (date_trunc('month', now() at time zone 'utc') at time zone 'utc') - interval '1 microsecond');

do $t7$
declare
  v_spent bigint;
begin
  select coalesce(sum(u.cost_micros), 0) into v_spent
  from public.usage_events u
  where u.workspace_id = '20000000-0000-0000-0000-000000000026'
    and u.occurred_at >= (date_trunc('month', now() at time zone 'utc') at time zone 'utc');

  if v_spent <> 700 then
    raise exception 'T7: 월 경계 합이 %입니다 (기대 700 — 경계 시각은 포함, 1마이크로초 이전은 제외)', v_spent;
  end if;
end
$t7$;


-- -----------------------------------------------------------------------------
-- T8: retry_dead_job — 재호출이 no-op이고 dead가 아닌 잡에는 0행 (ING-07)
-- -----------------------------------------------------------------------------
do $t8a$
declare
  v public.jobs;
begin
  -- dead 상태를 실제 경로로 만든다(직접 UPDATE 금지 계약을 테스트도 지킨다).
  select * into v from public.claim_job('w1', array['t8-retry']);
  if v.id <> '30000000-0000-0000-0000-000000000024' then
    raise exception 'T8 준비: claim이 어긋났습니다 (id=%)', v.id;
  end if;
  perform public.dead_letter_job('30000000-0000-0000-0000-000000000024', 'w1', '핸들러 없음');

  -- succeeded 잡도 하나 만들어 둔다(retry 대상이 아님을 확인하기 위해).
  select * into v from public.claim_job('w1', array['t8-done']);
  if v.id <> '30000000-0000-0000-0000-000000000025' then
    raise exception 'T8 준비: 두 번째 claim이 어긋났습니다 (id=%)', v.id;
  end if;
  perform public.complete_job_and_chain('30000000-0000-0000-0000-000000000025');
end
$t8a$;

set local role authenticated;
set local request.jwt.claims = '{"sub":"10000000-0000-0000-0000-000000000021","role":"authenticated"}';

do $t8b$
declare
  v_rows int;
begin
  select count(*) into v_rows from public.retry_dead_job('30000000-0000-0000-0000-000000000024');
  if v_rows <> 1 then
    raise exception 'T8: dead 잡의 retry_dead_job이 %행이었습니다 (기대 1)', v_rows;
  end if;

  -- 중복 클릭: 예외가 아니라 0행이어야 한다.
  select count(*) into v_rows from public.retry_dead_job('30000000-0000-0000-0000-000000000024');
  if v_rows <> 0 then
    raise exception 'T8: 이미 queued인 잡의 재호출이 %행이었습니다 (기대 0)', v_rows;
  end if;

  -- succeeded 잡은 되살릴 수 없다.
  select count(*) into v_rows from public.retry_dead_job('30000000-0000-0000-0000-000000000025');
  if v_rows <> 0 then
    raise exception 'T8: succeeded 잡의 retry_dead_job이 %행이었습니다 (기대 0)', v_rows;
  end if;
end
$t8b$;

reset role;

do $t8c$
declare
  v public.jobs;
begin
  select * into v from public.jobs where id = '30000000-0000-0000-0000-000000000024';
  if v.status <> 'queued' or v.attempts <> 0 or v.last_error is not null
     or v.locked_at is not null or v.locked_by is not null then
    raise exception 'T8: 재시도 뒤 상태가 어긋났습니다 (status=%, attempts=%, last_error=%, locked_by=%)',
      v.status, v.attempts, v.last_error, v.locked_by;
  end if;
end
$t8c$;


-- -----------------------------------------------------------------------------
-- T9: enum_check_values — 워커 기동 시 enum 대조 가드가 읽을 값 (COMP-02)
--
-- jobs.status는 0009가 여섯 값으로 확장했다. 이 단언은 CHECK 재정의와 워커가 아는
-- 집합이 같은 곳을 출처로 삼는지를 고정한다.
-- -----------------------------------------------------------------------------
do $t9$
declare
  v_cat    text[];
  v_status text[];
  v_none   text[];
begin
  v_cat := public.enum_check_values('wiki_pages', 'category');
  if v_cat is distinct from array['concepts', 'entities', 'guides', 'maps'] then
    raise exception 'T9: wiki_pages.category 열거가 %입니다 (기대 concepts/entities/guides/maps)', v_cat;
  end if;

  v_status := public.enum_check_values('jobs', 'status');
  if v_status is distinct from array['canceled', 'dead', 'failed', 'queued', 'running', 'succeeded'] then
    raise exception 'T9: jobs.status 열거가 %입니다 (기대 6값, canceled 포함)', v_status;
  end if;

  -- 존재하지 않는 컬럼: null이 아니라 빈 배열. null이면 호출자가 "열거 없음"과
  -- "조회 실패"를 구분할 수 없다.
  v_none := public.enum_check_values('jobs', 'no_such_column');
  if v_none is null then
    raise exception 'T9: 없는 컬럼에 대해 null을 돌려줬습니다 (기대 빈 배열)';
  end if;
  if array_length(v_none, 1) is not null then
    raise exception 'T9: 없는 컬럼에 대해 %를 돌려줬습니다 (기대 빈 배열)', v_none;
  end if;
end
$t9$;


-- -----------------------------------------------------------------------------
-- T10: 권한 방향 (T-03-11, T-03-13, 그리고 0008이 클라우드에서 놓친 정정)
--
-- ⚠️ 이 단언들은 **로컬 카탈로그**만 본다. 클라우드의 pg_default_acl은 로컬에 없는
--    (public, f, postgres) 항목을 갖고 있어 새 함수에 service_role EXECUTE를 기본
--    부여하므로, 같은 질문을 원격에 대해 다시 물어야 한다(docs/ops/migration-0009-record.md).
-- -----------------------------------------------------------------------------
do $t10$
declare
  v_bad text := '';
begin
  -- usage_events는 감사 기록이다: 사용자 쓰기 없음, 워커도 수정·삭제 없음.
  if has_table_privilege('authenticated', 'public.usage_events', 'SELECT') is false then
    v_bad := v_bad || ' authenticated에 SELECT가 없음;';
  end if;
  if has_table_privilege('authenticated', 'public.usage_events', 'INSERT') then
    v_bad := v_bad || ' authenticated에 INSERT가 있음;';
  end if;
  if has_table_privilege('authenticated', 'public.usage_events', 'UPDATE') then
    v_bad := v_bad || ' authenticated에 UPDATE가 있음;';
  end if;
  if has_table_privilege('authenticated', 'public.usage_events', 'DELETE') then
    v_bad := v_bad || ' authenticated에 DELETE가 있음;';
  end if;
  if has_table_privilege('authenticated', 'public.usage_events', 'TRUNCATE') then
    v_bad := v_bad || ' authenticated에 TRUNCATE가 있음;';
  end if;
  if has_table_privilege('service_role', 'public.usage_events', 'INSERT') is false then
    v_bad := v_bad || ' service_role에 INSERT가 없음;';
  end if;
  if has_table_privilege('service_role', 'public.usage_events', 'UPDATE') then
    v_bad := v_bad || ' service_role에 UPDATE가 있음;';
  end if;
  if has_table_privilege('service_role', 'public.usage_events', 'DELETE') then
    v_bad := v_bad || ' service_role에 DELETE가 있음;';
  end if;
  if has_table_privilege('service_role', 'public.usage_events', 'TRUNCATE') then
    v_bad := v_bad || ' service_role에 TRUNCATE가 있음;';
  end if;
  if has_table_privilege('anon', 'public.usage_events', 'SELECT') then
    v_bad := v_bad || ' anon에 SELECT가 있음;';
  end if;

  -- 워커 전용 함수는 사용자 롤에 열리면 안 된다.
  if has_function_privilege('authenticated', 'public.dead_letter_job(uuid, text, text)', 'EXECUTE') then
    v_bad := v_bad || ' authenticated가 dead_letter_job을 실행 가능;';
  end if;
  if has_function_privilege('authenticated', 'public.cancel_job(uuid, text)', 'EXECUTE') then
    v_bad := v_bad || ' authenticated가 cancel_job을 실행 가능;';
  end if;
  if has_function_privilege('authenticated', 'public.enum_check_values(text, text)', 'EXECUTE') then
    v_bad := v_bad || ' authenticated가 enum_check_values를 실행 가능;';
  end if;
  if has_function_privilege('service_role', 'public.dead_letter_job(uuid, text, text)', 'EXECUTE') is false then
    v_bad := v_bad || ' service_role이 dead_letter_job을 실행 불가;';
  end if;

  -- 사용자 RPC 3종은 방향이 반대. service_role에는 주지 않는다.
  if has_function_privilege('authenticated', 'public.enqueue_source_job(uuid, uuid)', 'EXECUTE') is false then
    v_bad := v_bad || ' authenticated가 enqueue_source_job을 실행 불가;';
  end if;
  if has_function_privilege('authenticated', 'public.request_job_cancel(uuid)', 'EXECUTE') is false then
    v_bad := v_bad || ' authenticated가 request_job_cancel을 실행 불가;';
  end if;
  if has_function_privilege('authenticated', 'public.retry_dead_job(uuid)', 'EXECUTE') is false then
    v_bad := v_bad || ' authenticated가 retry_dead_job을 실행 불가;';
  end if;
  if has_function_privilege('service_role', 'public.enqueue_source_job(uuid, uuid)', 'EXECUTE') then
    v_bad := v_bad || ' service_role이 enqueue_source_job을 실행 가능;';
  end if;
  if has_function_privilege('anon', 'public.enqueue_source_job(uuid, uuid)', 'EXECUTE') then
    v_bad := v_bad || ' anon이 enqueue_source_job을 실행 가능;';
  end if;

  -- 0008이 클라우드에서 놓친 정정: search_chunks는 authenticated만.
  if has_function_privilege('service_role', 'public.search_chunks(uuid, extensions.vector, int)', 'EXECUTE') then
    v_bad := v_bad || ' service_role이 search_chunks를 실행 가능;';
  end if;
  if has_function_privilege('authenticated', 'public.search_chunks(uuid, extensions.vector, int)', 'EXECUTE') is false then
    v_bad := v_bad || ' authenticated가 search_chunks를 실행 불가;';
  end if;

  if v_bad <> '' then
    raise exception 'T10: 권한 방향이 어긋났습니다 —%', v_bad;
  end if;
end
$t10$;


select 'pipeline_ops: ok' as result;

rollback;
