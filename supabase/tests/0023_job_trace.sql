-- =============================================================================
-- NexusWiki 0023 검증: 잡 체인의 trace 연속성
--
-- 관련 이슈: #160
--
-- ⚠️ 이 파일은 마이그레이션이 아닙니다. 전체가 하나의 트랜잭션이고 마지막이 rollback입니다.
--
-- 실행
--   cat supabase/tests/0023_job_trace.sql \
--     | docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1
-- =============================================================================

begin;

insert into auth.users (id, email)
values ('10000000-0000-0000-0000-000000000023', 'trace@example.test');

insert into public.workspaces (id, name, slug, owner_id)
values (
  '20000000-0000-0000-0000-000000000023',
  'trace 계약 테스트',
  'trace-contract',
  '10000000-0000-0000-0000-000000000023'
);

insert into public.raw_sources (id, workspace_id, title, source_type, content, content_hash)
values (
  '40000000-0000-0000-0000-000000000023',
  '20000000-0000-0000-0000-000000000023',
  '원문',
  'text',
  '본문',
  'trace-contract-hash'
);

-- 인큐 함수는 요청자 JWT로 호출되므로 그 신원을 흉내 냅니다.
select set_config('request.jwt.claim.sub', '10000000-0000-0000-0000-000000000023', true);
select set_config(
  'request.jwt.claims',
  '{"sub":"10000000-0000-0000-0000-000000000023","role":"authenticated"}',
  true
);


-- -----------------------------------------------------------------------------
-- 계약 1: 인큐가 trace를 저장하고, 중복 인큐는 기존 값을 바꾸지 않는다.
-- -----------------------------------------------------------------------------
do $t1$
declare
  v public.jobs;
begin
  select * into v from public.enqueue_source_job(
    '20000000-0000-0000-0000-000000000023',
    '40000000-0000-0000-0000-000000000023',
    '50000000-0000-0000-0000-000000000023'
  );
  if v.trace_id is distinct from '50000000-0000-0000-0000-000000000023' then
    raise exception '인큐가 trace를 저장하지 않았습니다 (trace_id=%)', v.trace_id;
  end if;

  select * into v from public.enqueue_source_job(
    '20000000-0000-0000-0000-000000000023',
    '40000000-0000-0000-0000-000000000023',
    '60000000-0000-0000-0000-000000000023'
  );
  if v.trace_id is distinct from '50000000-0000-0000-0000-000000000023' then
    raise exception '중복 인큐가 기존 trace를 덮어썼습니다 (trace_id=%)', v.trace_id;
  end if;
end
$t1$;


-- -----------------------------------------------------------------------------
-- 계약 2: 기본값 덕분에 이전 버전 코드의 2인자 이름 호출이 그대로 동작한다.
-- -----------------------------------------------------------------------------
do $t2$
declare
  v public.jobs;
begin
  select * into v from public.enqueue_source_job(
    p_workspace_id  => '20000000-0000-0000-0000-000000000023',
    p_raw_source_id => '40000000-0000-0000-0000-000000000023'
  );
  if v.id is null then
    raise exception '2인자 호출이 잡을 돌려주지 않았습니다';
  end if;
end
$t2$;


-- -----------------------------------------------------------------------------
-- 계약 3: 함수 권한. anon과 service_role은 인큐 함수를 실행할 수 없다.
-- -----------------------------------------------------------------------------
do $t3$
begin
  if has_function_privilege('anon', 'public.enqueue_source_job(uuid, uuid, uuid)', 'execute') then
    raise exception 'anon이 enqueue_source_job을 실행할 수 있습니다';
  end if;
  if has_function_privilege('service_role', 'public.enqueue_source_job(uuid, uuid, uuid)', 'execute') then
    raise exception 'service_role이 enqueue_source_job을 실행할 수 있습니다';
  end if;
  if not has_function_privilege('authenticated', 'public.enqueue_source_job(uuid, uuid, uuid)', 'execute') then
    raise exception 'authenticated가 enqueue_source_job을 실행할 수 없습니다';
  end if;
  if to_regprocedure('public.enqueue_source_job(uuid, uuid)') is not null then
    raise exception '2인자 오버로드가 남아 PostgREST 호출이 모호해집니다';
  end if;
end
$t3$;


-- -----------------------------------------------------------------------------
-- 계약 4: claim이 시작 시각을 남기고, 완료 후에도 남으며, 체인 후속 잡이 trace를 상속한다.
-- -----------------------------------------------------------------------------
do $t4$
declare
  v_claimed public.jobs;
  v_done    public.jobs;
  v_next    public.jobs;
begin
  select * into v_claimed from public.claim_job('w1', array['parse']);
  if v_claimed.last_claimed_at is null then
    raise exception 'claim이 last_claimed_at을 남기지 않았습니다';
  end if;

  select * into v_done from public.complete_job_and_chain(
    v_claimed.id, 'compile', '{"target_id": "trace-contract"}'::jsonb
  );
  if v_done.locked_at is not null or v_done.last_claimed_at is null then
    raise exception '완료 후 시각 상태가 어긋났습니다 (locked_at=%, last_claimed_at=%)',
      v_done.locked_at, v_done.last_claimed_at;
  end if;

  select * into v_next
  from public.jobs j
  where j.workspace_id = '20000000-0000-0000-0000-000000000023' and j.type = 'compile';
  if v_next.trace_id is distinct from '50000000-0000-0000-0000-000000000023' then
    raise exception '후속 잡이 trace를 상속하지 않았습니다 (trace_id=%)', v_next.trace_id;
  end if;
end
$t4$;


-- -----------------------------------------------------------------------------
-- 계약 5: 실패 재시도, 반납, 회수, dead 재시도는 trace를 바꾸지 않는다.
-- -----------------------------------------------------------------------------
do $t5$
declare
  v public.jobs;
begin
  select * into v from public.claim_job('w1', array['compile']);
  select * into v from public.fail_job(v.id, 'boom', '0 seconds');
  if v.trace_id is distinct from '50000000-0000-0000-0000-000000000023' then
    raise exception 'fail_job이 trace를 바꿨습니다';
  end if;

  select * into v from public.claim_job('w1', array['compile']);
  select * into v from public.release_job(v.id, 'w1');
  if v.trace_id is distinct from '50000000-0000-0000-0000-000000000023' then
    raise exception 'release_job이 trace를 바꿨습니다';
  end if;

  -- 회수: 잠금이 시간 초과된 잡을 reaper가 되돌려도 trace는 그대로여야 합니다. 트랜잭션 안에서는
  -- now()가 고정되어 타임아웃 0으로는 방금 claim한 잡이 대상이 되지 않으므로 음수를 줍니다.
  select * into v from public.claim_job('w1', array['compile']);
  perform public.reap_stale_jobs('-1 hour');
  select * into v from public.jobs j where j.id = v.id;
  if v.status <> 'queued'
     or v.locked_at is not null
     or v.trace_id is distinct from '50000000-0000-0000-0000-000000000023' then
    raise exception 'reap_stale_jobs 상태가 어긋났습니다 (status=%, locked_at=%, trace_id=%)',
      v.status, v.locked_at, v.trace_id;
  end if;

  select * into v from public.claim_job('w1', array['compile']);
  select * into v from public.dead_letter_job(v.id, 'w1', 'dead');
  select * into v from public.retry_dead_job(v.id);
  if v.status <> 'queued' or v.trace_id is distinct from '50000000-0000-0000-0000-000000000023' then
    raise exception 'dead 재시도 상태가 어긋났습니다 (status=%, trace_id=%)', v.status, v.trace_id;
  end if;
end
$t5$;


-- -----------------------------------------------------------------------------
-- 계약 6: trace가 없는 잡도 체인을 정상 통과한다.
-- -----------------------------------------------------------------------------
do $t6$
declare
  v_id   uuid;
  v      public.jobs;
  v_next public.jobs;
begin
  insert into public.jobs (workspace_id, type, payload)
  values ('20000000-0000-0000-0000-000000000023', 'legacy', '{"target_id": "legacy-1"}')
  returning id into v_id;

  select * into v from public.claim_job('w1', array['legacy']);
  select * into v from public.complete_job_and_chain(
    v_id, 'legacy_next', '{"target_id": "legacy-1"}'::jsonb
  );
  if v.status <> 'succeeded' then
    raise exception 'trace 없는 잡이 완료되지 않았습니다';
  end if;

  select * into v_next from public.jobs j
  where j.workspace_id = '20000000-0000-0000-0000-000000000023' and j.type = 'legacy_next';
  if v_next.id is null or v_next.trace_id is not null then
    raise exception 'trace 없는 잡의 후속 상태가 어긋났습니다';
  end if;
end
$t6$;


select 'job_trace: ok' as result;

rollback;
