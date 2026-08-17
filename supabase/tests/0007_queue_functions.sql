-- =============================================================================
-- NexusWiki 0007 검증: 큐 함수 계약 (release_job · complete_job_and_chain)
--
-- 관련 태스크: P2-JOB-01 (소비자는 02-07의 큐 루프)
-- 설계 근거:  02-CONTEXT.md > D-18
--
-- ⚠️ 이 파일은 마이그레이션이 아닙니다. supabase/migrations/ 밖에 있으므로
--    supabase db reset이 적용하지 않으며 마이그레이션 순서에도 들어가지 않습니다.
--    0005_storage_policies.sql과 같은 자리, 같은 관례입니다.
--
-- 전체가 하나의 트랜잭션이고 마지막이 rollback이므로 픽스처 행은 남지 않습니다.
-- 남기면 jobs_dedup_idx(0007 섹션 2)가 다음 실행의 인큐를 막습니다.
--
-- 실행
--   cat supabase/tests/0007_queue_functions.sql \
--     | docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1
-- =============================================================================

begin;

-- 픽스처는 고정 UUID를 써서 실패를 재현하기 쉽게 만듭니다.
insert into auth.users (id, email)
values ('10000000-0000-0000-0000-000000000011', 'queue@example.test');

-- 소유자 멤버십은 workspaces_add_owner_member 트리거가 자동으로 만듭니다.
insert into public.workspaces (id, name, slug, owner_id)
values (
  '20000000-0000-0000-0000-000000000011',
  '큐 계약 테스트',
  'queue-contract',
  '10000000-0000-0000-0000-000000000011'
);

insert into public.jobs (id, workspace_id, type, payload)
values (
  '30000000-0000-0000-0000-000000000011',
  '20000000-0000-0000-0000-000000000011',
  'noop',
  '{"target_id": "t-1"}'
);


-- -----------------------------------------------------------------------------
-- 준비: 워커 w1이 잡을 점유한다. attempts는 claim 시점에 증가한다(0003:44-47).
-- -----------------------------------------------------------------------------
do $t0$
declare
  v public.jobs;
begin
  select * into v from public.claim_job('w1', array['noop']);

  if v.id is null then
    raise exception 'claim_job이 잡을 점유하지 못했습니다';
  end if;
  if v.attempts <> 1 or v.status <> 'running' or v.locked_by <> 'w1' then
    raise exception 'claim 직후 상태가 어긋났습니다 (attempts=%, status=%, locked_by=%)',
      v.attempts, v.status, v.locked_by;
  end if;
end
$t0$;


-- -----------------------------------------------------------------------------
-- 계약 2: 락 소유자 술어 — w1이 점유한 잡을 w2가 반납할 수 없다.
--
-- 이것이 "다른 워커의 진행을 덮어쓰지 않는다"(SPEC R10)의 SQL 수준 증명이다.
-- 술어가 빠지면 종료 중인 워커가 살아 있는 워커의 잡을 큐로 되돌려
-- 같은 잡이 두 번 처리된다.
-- -----------------------------------------------------------------------------
do $t2$
declare
  v_rows int;
  v      public.jobs;
begin
  select count(*) into v_rows from public.release_job(
    '30000000-0000-0000-0000-000000000011', 'w2'
  );
  if v_rows <> 0 then
    raise exception '다른 워커(w2)의 release_job이 %행을 바꿨습니다 (기대 0)', v_rows;
  end if;

  select * into v from public.jobs
  where id = '30000000-0000-0000-0000-000000000011';
  if v.status <> 'running' or v.locked_by <> 'w1' or v.attempts <> 1 then
    raise exception '다른 워커 호출 뒤 잡 상태가 변했습니다 (status=%, locked_by=%, attempts=%)',
      v.status, v.locked_by, v.attempts;
  end if;
end
$t2$;


-- -----------------------------------------------------------------------------
-- 계약 1: attempts 되돌림 — 락 소유자 본인이 반납하면 시도가 하나 돌아온다.
--
-- 되돌리지 않으면 자발적 종료(재배포)가 독약 잡 카운트를 소모해
-- 세 번의 배포만으로 정상 잡이 dead로 떨어진다 (02-CONTEXT.md > D-18).
-- -----------------------------------------------------------------------------
do $t1$
declare
  v_rows int;
  v      public.jobs;
begin
  select count(*) into v_rows from public.release_job(
    '30000000-0000-0000-0000-000000000011', 'w1'
  );
  if v_rows <> 1 then
    raise exception '락 소유자의 release_job이 %행을 바꿨습니다 (기대 1)', v_rows;
  end if;

  select * into v from public.jobs
  where id = '30000000-0000-0000-0000-000000000011';
  if v.status <> 'queued'
     or v.attempts <> 0
     or v.locked_at is not null
     or v.locked_by is not null then
    raise exception '반납 뒤 상태가 어긋났습니다 (status=%, attempts=%, locked_at=%, locked_by=%)',
      v.status, v.attempts, v.locked_at, v.locked_by;
  end if;
end
$t1$;


-- -----------------------------------------------------------------------------
-- 계약 4: complete_job_and_chain 원자성 — 완료와 다음 잡 인큐가 함께 일어나고,
--         재호출은 0행 no-op이며 다음 잡을 증식시키지 않는다.
--
-- 잡은 at-least-once라 재호출이 정상 경로다. 여기서 실패하면 재처리마다
-- 다음 잡이 하나씩 더 생겨 큐가 무한히 불어난다.
-- -----------------------------------------------------------------------------
do $t4$
declare
  v_rows int;
  v      public.jobs;
  v_next int;
begin
  -- 다시 점유한다. attempts는 0 → 1이 된다.
  select * into v from public.claim_job('w1', array['noop']);
  if v.id is null or v.attempts <> 1 then
    raise exception '재점유가 실패했습니다 (id=%, attempts=%)', v.id, v.attempts;
  end if;

  select count(*) into v_rows from public.complete_job_and_chain(
    '30000000-0000-0000-0000-000000000011',
    'noop-next',
    '{"target_id": "t-2"}'::jsonb
  );
  if v_rows <> 1 then
    raise exception 'complete_job_and_chain이 %행을 반환했습니다 (기대 1)', v_rows;
  end if;

  select * into v from public.jobs
  where id = '30000000-0000-0000-0000-000000000011';
  if v.status <> 'succeeded' or v.locked_at is not null or v.locked_by is not null then
    raise exception '완료 뒤 상태가 어긋났습니다 (status=%, locked_at=%, locked_by=%)',
      v.status, v.locked_at, v.locked_by;
  end if;

  select count(*) into v_next from public.jobs where type = 'noop-next';
  if v_next <> 1 then
    raise exception '다음 잡이 %개 생겼습니다 (기대 1)', v_next;
  end if;

  -- 재호출: 0행이어야 하고 다음 잡이 추가로 생기면 안 된다.
  select count(*) into v_rows from public.complete_job_and_chain(
    '30000000-0000-0000-0000-000000000011',
    'noop-next',
    '{"target_id": "t-2"}'::jsonb
  );
  if v_rows <> 0 then
    raise exception '이미 succeeded인 잡의 재호출이 %행을 반환했습니다 (기대 0)', v_rows;
  end if;

  select count(*) into v_next from public.jobs where type = 'noop-next';
  if v_next <> 1 then
    raise exception '재호출로 다음 잡이 %개가 되었습니다 (기대 1)', v_next;
  end if;
end
$t4$;


-- -----------------------------------------------------------------------------
-- 계약 3: 상태 술어 — 이미 succeeded인 잡에 release_job을 불러도 예외가 아니라
--         0행 no-op이다. 재처리 경로가 예외로 죽으면 워커가 종료하지 못한다.
-- -----------------------------------------------------------------------------
do $t3$
declare
  v_rows int;
  v      public.jobs;
begin
  select count(*) into v_rows from public.release_job(
    '30000000-0000-0000-0000-000000000011', 'w1'
  );
  if v_rows <> 0 then
    raise exception 'succeeded 잡의 release_job이 %행을 바꿨습니다 (기대 0)', v_rows;
  end if;

  select * into v from public.jobs
  where id = '30000000-0000-0000-0000-000000000011';
  if v.status <> 'succeeded' then
    raise exception 'succeeded 잡의 상태가 %로 변했습니다', v.status;
  end if;
end
$t3$;


select 'queue_functions: ok' as result;

rollback;
