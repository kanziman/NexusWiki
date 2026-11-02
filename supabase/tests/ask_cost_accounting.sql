-- #172 예약·정산 계약. 데이터는 마지막에 모두 롤백한다.
-- 설계: openspec/changes/reconcile-interrupted-ask-cost/design.md D1~D6.
begin;
insert into auth.users(id, email) values
  ('10000000-0000-0000-0000-000000000027', 'ask-cost@example.test');
insert into public.workspaces(id, owner_id, name, slug, monthly_budget_micros) values
  ('20000000-0000-0000-0000-000000000027', '10000000-0000-0000-0000-000000000027',
   '비용 테스트', 'ask-cost-test', 100);

do $$
declare ws uuid := '20000000-0000-0000-0000-000000000027';
  call_id uuid := gen_random_uuid(); trace uuid := gen_random_uuid(); n bigint;
begin
  perform public.reserve_ask_cost(ws, call_id, trace, 'm', 'v1', 70);
  perform public.reserve_ask_cost(ws, call_id, trace, 'm', 'v1', 70);
  select public.sum_usage_events_since(ws, date_trunc('month', now(), 'UTC')) into n;
  assert n = 70, '중복 예약';
  begin
    perform public.reserve_ask_cost(ws, gen_random_uuid(), gen_random_uuid(), 'm', 'v1', 40);
    raise exception '예산 초과 승인이 허용됨';
  exception when sqlstate 'NW402' then null; end;
  assert public.update_ask_cost(ws, call_id, 'start');
  assert not public.update_ask_cost(ws, call_id, 'start'), '중복 전송';
  assert not public.update_ask_cost(ws, call_id, 'release'), '전송 후 해제';
  insert into public.usage_events(workspace_id, ask_call_id, kind, provider, model, cost_micros)
    values(ws, call_id, 'llm', 'p', 'm', 90);
  assert public.sum_usage_events_since(ws, date_trunc('month', now(), 'UTC')) = 90,
    '관측액과 확보액 중 큰 값';
  assert public.update_ask_cost(ws, call_id, 'settle', p_cost_micros => 20);
  assert not public.update_ask_cost(ws, call_id, 'settle', p_cost_micros => 99);
  assert public.sum_usage_events_since(ws, date_trunc('month', now(), 'UTC')) = 20,
    '하향 정산 중복';
  assert (select cost_micros from public.usage_events where ask_call_id = call_id) = 90,
    '원 관측 행 변조';
  call_id := gen_random_uuid();
  perform public.reserve_ask_cost(ws, call_id, gen_random_uuid(), 'm', 'v1', 50);
  perform public.update_ask_cost(ws, call_id, 'start');
  perform public.update_ask_cost(ws, call_id, 'settle', p_cost_micros => 110);
  assert public.sum_usage_events_since(ws, date_trunc('month', now(), 'UTC')) = 130,
    '확보 초과 비용 누락';
  -- 이전 달 정산이 이번 달 사용량으로 들어오지 않는다.
  update public.ask_cost_calls set created_at = date_trunc('month', now(), 'UTC') - interval '1 day'
    where id = call_id;
  assert public.sum_usage_events_since(ws, date_trunc('month', now(), 'UTC')) = 20;
  call_id := gen_random_uuid();
  perform public.reserve_ask_cost(ws, call_id, gen_random_uuid(), 'm', 'v1', 30);
  assert public.update_ask_cost(ws, call_id, 'release');
  assert public.sum_usage_events_since(ws, date_trunc('month', now(), 'UTC')) = 20;
  call_id := gen_random_uuid();
  perform public.reserve_ask_cost(ws, call_id, gen_random_uuid(), 'm', 'v1', 30);
  perform public.update_ask_cost(ws, call_id, 'start');
  perform public.update_ask_cost(ws, call_id, 'generation', 'gen-a');
  perform public.update_ask_cost(ws, call_id, 'generation', 'gen-b');
  assert not public.update_ask_cost(ws, call_id, 'settle', p_cost_micros => 0), 'ID 충돌';
  assert public.sum_usage_events_since(ws, date_trunc('month', now(), 'UTC')) = 50;
end $$;

-- 호출·generation ID는 사용자와 service_role의 직접 읽기를 모두 닫는다.
set local role authenticated;
do $$ begin
  begin perform * from public.ask_cost_calls; raise exception '직접 읽기 허용';
  exception when insufficient_privilege then null; end;
  begin perform public.claim_ask_costs(); raise exception '임대 허용';
  exception when insufficient_privilege then null; end;
  begin perform public.reserve_ask_cost(gen_random_uuid(),gen_random_uuid(),gen_random_uuid(),'m','v',1);
    raise exception '예약 허용'; exception when insufficient_privilege then null; end;
  begin perform public.ask_cost_snapshot('20000000-0000-0000-0000-000000000027',now());
    raise exception '비멤버 조회 허용'; exception when insufficient_privilege then null; end;
end $$;
reset role;
do $$
declare ws uuid := '20000000-0000-0000-0000-000000000027';
  call_id uuid := gen_random_uuid(); claimed public.ask_cost_calls;
begin
  perform public.reserve_ask_cost(ws, call_id, gen_random_uuid(), 'm', 'v1', 10);
  perform public.update_ask_cost(ws, call_id, 'start');
  perform public.update_ask_cost(ws, call_id, 'generation', 'gen-lease');
  update public.ask_cost_calls set next_attempt_at = now() - interval '1 minute' where id = call_id;
  select * into claimed from public.claim_ask_costs(10) where id = call_id;
  assert claimed.lease_id is not null, '만료 호출 복구 누락';
  assert not public.update_ask_cost(ws, call_id, 'settle', p_cost_micros => 0,
    p_source => 'generation', p_lease_id => gen_random_uuid()), '틀린 임대 정산';
  assert public.update_ask_cost(ws, call_id, 'retry', p_lease_id => claimed.lease_id);
  assert public.sum_usage_events_since(ws, date_trunc('month', now(), 'UTC')) = 60,
    '조회 실패 후 점유 유실';
  update public.ask_cost_calls set next_attempt_at = now() - interval '1 minute',
    lease_until = now() - interval '1 second' where id = call_id;
  select * into claimed from public.claim_ask_costs(10) where id = call_id;
  assert public.update_ask_cost(ws, call_id, 'settle', p_cost_micros => 3,
    p_source => 'generation', p_lease_id => claimed.lease_id);
  assert public.sum_usage_events_since(ws, date_trunc('month', now(), 'UTC')) = 53;
end $$;
select 'ask_cost_accounting: ok';
-- 인큐 경로도 원시 usage가 아니라 예약을 포함한 공통 예산을 읽는다.
insert into public.raw_sources(id, workspace_id, title, source_type, content, content_hash)
values ('40000000-0000-0000-0000-000000000027','20000000-0000-0000-0000-000000000027',
  '원문','text','합성','ask-cost-hash');
update public.workspaces set monthly_budget_micros = 50
  where id = '20000000-0000-0000-0000-000000000027';
select set_config('request.jwt.claim.sub', '10000000-0000-0000-0000-000000000027', true);
do $$ begin
  begin
    perform public.enqueue_source_job('20000000-0000-0000-0000-000000000027',
      '40000000-0000-0000-0000-000000000027');
    raise exception '미확정 점유를 무시하고 인큐됨';
  exception when sqlstate 'NW402' then null; end;
end $$;
rollback;
