-- #183, #186 Control Room [예산] 탭 집계 계약. 마지막에 모두 롤백한다.
begin;

insert into auth.users(id, email) values
  ('10000000-0000-0000-0000-000000000281', 'owner-0028@example.test'),
  ('10000000-0000-0000-0000-000000000282', 'viewer-0028@example.test'),
  ('10000000-0000-0000-0000-000000000283', 'outsider-0028@example.test');

insert into public.workspaces(id, owner_id, name, slug, monthly_budget_micros) values
  ('20000000-0000-0000-0000-000000000028', '10000000-0000-0000-0000-000000000281',
   '예산 탭 테스트', 'budget-tab-test-0028', 5000000);

insert into public.workspace_members(workspace_id, user_id, role) values
  ('20000000-0000-0000-0000-000000000028', '10000000-0000-0000-0000-000000000282', 'viewer');

-- owner와 viewer 각각의 Ask 스레드 및 메시지
insert into public.ask_threads(id, workspace_id, user_id, title) values
  ('30000000-0000-0000-0000-000000000281', '20000000-0000-0000-0000-000000000028',
   '10000000-0000-0000-0000-000000000281', 'owner 스레드'),
  ('30000000-0000-0000-0000-000000000282', '20000000-0000-0000-0000-000000000028',
   '10000000-0000-0000-0000-000000000282', 'viewer 스레드');

insert into public.ask_messages(
  id, workspace_id, thread_id, client_turn_id, trace_id, question, answer_text, status, control_report
) values
  (
    '40000000-0000-0000-0000-000000000281',
    '20000000-0000-0000-0000-000000000028',
    '30000000-0000-0000-0000-000000000281',
    gen_random_uuid(),
    gen_random_uuid(),
    'owner 질문',
    '근거를 찾지 못했습니다.',
    'no-evidence',
    '{"route": {"decision": "NO_EVIDENCE"}}'::jsonb
  ),
  (
    '40000000-0000-0000-0000-000000000282',
    '20000000-0000-0000-0000-000000000028',
    '30000000-0000-0000-0000-000000000282',
    gen_random_uuid(),
    gen_random_uuid(),
    'viewer 질문',
    '답변',
    'resolved',
    '{"route": {"decision": "STANDARD"}, "budget": {"truncated": true}}'::jsonb
  );

-- 컴파일·충돌 검사 사용량 및 SKIP_UNCHANGED 체인 잡
insert into public.usage_events(
  workspace_id, kind, provider, model, prompt_tokens, completion_tokens, total_tokens, cost_micros, metadata
) values
  (
    '20000000-0000-0000-0000-000000000028',
    'llm',
    'openrouter',
    'test-model',
    1200,
    300,
    1500,
    4500,
    '{"call": "compile", "route": "TRUNCATED", "max_tokens": 4096}'::jsonb
  ),
  (
    '20000000-0000-0000-0000-000000000028',
    'llm',
    'openrouter',
    'test-model',
    400,
    40,
    440,
    900,
    '{"call": "conflict_check", "truncated_input": true, "max_tokens": 512}'::jsonb
  );

insert into public.raw_sources(id, workspace_id, title, source_type, content, content_hash) values
  ('50000000-0000-0000-0000-000000000281', '20000000-0000-0000-0000-000000000028',
   '예산 탭 원문', 'text', '원문 본문', 'budget-hash-0028');

insert into public.jobs(workspace_id, type, status, payload) values
  (
    '20000000-0000-0000-0000-000000000028',
    'link_sync',
    'succeeded',
    '{"target_id": "50000000-0000-0000-0000-000000000281", "raw_source_id": "50000000-0000-0000-0000-000000000281", "compile_route": "SKIP_UNCHANGED"}'::jsonb
  );

-- 1. 비멤버와 anon/service_role은 호출할 수 없다.
set local role anon;
do $$ begin
  begin
    perform public.control_budget_snapshot('20000000-0000-0000-0000-000000000028', now() - interval '30 days');
    raise exception 'anon 실행이 허용됨';
  exception when insufficient_privilege then null; end;
end $$;
reset role;

set local role service_role;
do $$ begin
  begin
    perform public.control_budget_snapshot('20000000-0000-0000-0000-000000000028', now() - interval '30 days');
    raise exception 'service_role 실행이 허용됨';
  exception when insufficient_privilege then null; end;
end $$;
reset role;

set local role authenticated;
select set_config('request.jwt.claim.sub', '10000000-0000-0000-0000-000000000283', true);
do $$ begin
  begin
    perform public.control_budget_snapshot('20000000-0000-0000-0000-000000000028', now() - interval '30 days');
    raise exception '비멤버 실행이 허용됨';
  exception when insufficient_privilege then null; end;
end $$;

-- 2. viewer는 월간 상한·소진액과 본인의 Ask 절감 카운트만 보고 워크스페이스 호출 내역은 보지 못한다.
select set_config('request.jwt.claim.sub', '10000000-0000-0000-0000-000000000282', true);
do $$
declare
  snap record;
begin
  select * into snap
  from public.control_budget_snapshot('20000000-0000-0000-0000-000000000028', now() - interval '30 days');

  assert snap.can_view_workspace is false, 'viewer의 can_view_workspace가 true';
  assert snap.cap_micros = 5000000, 'cap_micros 불일치';
  assert snap.budget_micros = 5400, 'budget_micros 불일치';
  assert snap.ask_no_evidence_count = 0, 'viewer에게 타인의 no-evidence가 보임';
  assert snap.ask_context_truncated_count = 1, 'viewer 본인의 context_truncated 누락';
  assert snap.compile_truncated_count = 0, 'viewer에게 compile_truncated가 보임';
  assert snap.compile_skipped_count = 0, 'viewer에게 compile_skipped가 보임';
  assert snap.by_call_path = '[]'::jsonb, 'viewer에게 by_call_path가 노출됨';
end $$;

-- 3. owner/editor는 워크스페이스 전체 절감 카운트와 호출 경로별 내역을 조회한다.
select set_config('request.jwt.claim.sub', '10000000-0000-0000-0000-000000000281', true);
do $$
declare
  snap record;
begin
  select * into snap
  from public.control_budget_snapshot('20000000-0000-0000-0000-000000000028', now() - interval '30 days');

  assert snap.can_view_workspace is true, 'owner의 can_view_workspace가 false';
  assert snap.cap_micros = 5000000, 'cap_micros 불일치';
  assert snap.reported_micros = 5400, 'reported_micros 불일치';
  assert snap.budget_micros = 5400, 'budget_micros 불일치';
  assert snap.ask_no_evidence_count = 1, '워크스페이스 no-evidence 집계 불일치';
  assert snap.ask_context_truncated_count = 1, '워크스페이스 context_truncated 집계 불일치';
  assert snap.compile_truncated_count = 1, 'compile_truncated 집계 불일치';
  assert snap.compile_skipped_count = 1, 'compile_skipped 집계 불일치';
  assert jsonb_array_length(snap.by_call_path) = 2, 'by_call_path 항목 수 불일치';
  assert (snap.by_call_path -> 0 ->> 'call') = 'compile', '첫 호출 경로가 compile이 아님';
  assert (snap.by_call_path -> 0 ->> 'budget_micros')::bigint = 4500, 'compile 비용 불일치';
  assert (snap.by_call_path -> 1 ->> 'call') = 'conflict_check', '둘째 호출 경로가 conflict_check가 아님';
end $$;

reset role;
select '0028_control_budget_tab: ok';
rollback;
