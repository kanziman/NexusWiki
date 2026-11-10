-- =============================================================================
-- NexusWiki 0037 검증: 평가 실험 기록의 접근 경계와 종류별 제약
--
-- 관련 이슈: #273
--
-- ⚠️ 이 파일은 마이그레이션이 아닙니다. 전체가 하나의 트랜잭션이고 마지막이 rollback입니다.
--
-- 실행
--   cat supabase/tests/0037_eval_experiments.sql \
--     | docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1
-- =============================================================================

begin;

insert into public.eval_policies
  (version, regression_rule, require_improvement, max_excluded,
   max_cost_increase_pct, max_p95_increase_ms, limitation, defined_on)
values ('test-policy', 'per_question', true, 0, 50, 15000, '반복 측정 없이 판정', '2026-11-10');

insert into public.eval_criteria_sets
  (id, name, source_path, source_commit, source_first_commit_at, earliest_run_at, conditions, adopted)
values
  ('test-late', '실행 뒤 기록', 'docs/x.md', '8a1800d', '2026-11-09 09:43+09', '2026-11-09 08:26+09',
   '[{"key": "a", "met": false}]', false),
  ('test-early', '실행 전 기록', 'docs/y.md', 'abcdef0', '2026-11-01 00:00+09', '2026-11-09 08:26+09',
   '[{"key": "a", "met": true}]', true);

insert into public.eval_experiments
  (id, kind, title, question, run_source, baseline_run_id, candidate_run_id,
   baseline_role, candidate_role, criteria_set_id, policy_version, public)
values
  ('test-adoption', 'adoption', '도입', '좋아지나?', 'research', 'off', 'on',
   '현재 방식', '도입 검토안', 'test-late', 'test-policy', true),
  ('test-stability', 'stability', '반복', '유지되나?', 'reliability', 'run-1', 'run-2',
   '기준 반복', '비교 반복', null, null, true);

insert into public.eval_decisions (experiment_id, status, rationale, decided_on, criteria_set_id)
values ('test-adoption', 'not_adopted', '원래 기준 미충족', '2026-11-09', 'test-late');

-- 1. 사전 등록 여부는 시각 비교로만 정해진다
do $$
begin
  if (select preregistered from public.eval_criteria_sets where id = 'test-late') then
    raise exception '실행 뒤 기록이 사전 등록으로 표시됨';
  end if;
  if not (select preregistered from public.eval_criteria_sets where id = 'test-early') then
    raise exception '실행 전 기록이 사전 등록으로 표시되지 않음';
  end if;
end $$;

do $$
begin
  update public.eval_criteria_sets set preregistered = true where id = 'test-late';
  raise exception '생성 열을 손으로 쓸 수 있음';
exception when generated_always then null;
end $$;

do $$
begin
  insert into public.eval_criteria_sets
    (id, name, source_path, source_commit, source_first_commit_at, earliest_run_at, conditions, adopted)
  values ('test-unknown', '출처 시각 없음', 'docs/z.md', null, null, '2026-11-09 08:26+09',
          '[{"key": "a", "met": true}]', true);
  if (select preregistered from public.eval_criteria_sets where id = 'test-unknown') is not null then
    raise exception '출처 시각이 없는데 사전 등록 여부가 정해짐';
  end if;
end $$;

-- 2. 종류별 제약
do $$
begin
  insert into public.eval_experiments
    (id, kind, title, question, run_source, baseline_run_id, candidate_run_id,
     baseline_role, candidate_role, criteria_set_id, policy_version, public)
  values ('test-grader', 'grader', '채점', '?', 'local', 'a', 'b', 'a', 'b', null, null, false);
  raise exception '출처 없는 채점 검증이 들어감';
exception when check_violation then null;
end $$;
do $$
begin
  insert into public.eval_decisions (experiment_id, status, rationale, decided_on, criteria_set_id)
  values ('test-stability', 'adopted', '측정 실험 결정', '2026-11-10', 'test-late');
  raise exception '측정 실험에 결정이 들어감';
exception when foreign_key_violation then null;
end $$;

do $$
begin
  insert into public.eval_decisions
    (experiment_id, experiment_kind, status, rationale, decided_on, criteria_set_id)
  values ('test-stability', 'stability', 'adopted', '종류 위장', '2026-11-10', 'test-late');
  raise exception '결정의 실험 종류를 바꿔 넣을 수 있음';
exception when check_violation then null;
end $$;

do $$
begin
  insert into public.eval_experiments
    (id, kind, title, question, run_source, baseline_run_id, candidate_run_id,
     baseline_role, candidate_role, criteria_set_id, policy_version, public)
  values ('test-bad-adoption', 'adoption', '기준 없음', '?', 'research', 'off', 'on',
          'a', 'b', null, null, true);
  raise exception '기준 없는 도입 실험이 들어감';
exception when check_violation then null;
end $$;

do $$
begin
  insert into public.eval_experiments
    (id, kind, title, question, run_source, baseline_run_id, candidate_run_id,
     baseline_role, candidate_role, criteria_set_id, policy_version, public)
  values ('test-bad-stability', 'stability', '기준 붙음', '?', 'reliability', 'run-1', 'run-2',
          'a', 'b', 'test-late', 'test-policy', true);
  raise exception '기준이 붙은 측정 실험이 들어감';
exception when check_violation then null;
end $$;

do $$
begin
  insert into public.eval_experiments
    (id, kind, title, question, run_source, baseline_run_id, candidate_run_id,
     baseline_role, candidate_role, criteria_set_id, policy_version, public)
  values ('test-same-run', 'stability', '같은 실행', '?', 'reliability', 'run-1', 'run-1',
          'a', 'b', null, null, true);
  raise exception '같은 실행끼리의 실험이 들어감';
exception when check_violation then null;
end $$;

do $$
begin
  update public.eval_experiments
  set kind = 'stability', criteria_set_id = null, policy_version = null
  where id = 'test-adoption';
  raise exception '결정이 있는 도입 실험의 종류를 바꿀 수 있음';
exception when foreign_key_violation then null;
end $$;

do $$
begin
  update public.eval_decisions set criteria_set_id = 'test-early' where experiment_id = 'test-adoption';
  raise exception '결정이 실험과 다른 기준 세트를 가리킬 수 있음';
exception when foreign_key_violation then null;
end $$;

do $$
begin
  insert into public.eval_policies
    (version, regression_rule, require_improvement, max_excluded,
     max_cost_increase_pct, max_p95_increase_ms, limitation, defined_on)
  values ('test-aggregate', 'aggregate', false, 0, 50, 15000, '합계', '2026-11-10');
  raise exception '합계 기준 정책이 들어감';
exception when check_violation then null;
end $$;

-- 3. 접근 경계: anon과 authenticated는 읽기·쓰기 모두 거부된다
set local role anon;
do $$
begin
  perform 1 from public.eval_experiments;
  raise exception 'anon이 실험을 읽음';
exception when insufficient_privilege then null;
end $$;
do $$
begin
  insert into public.eval_policies
    (version, regression_rule, require_improvement, max_excluded,
     max_cost_increase_pct, max_p95_increase_ms, limitation, defined_on)
  values ('anon-policy', 'per_question', true, 0, 999, 999999, 'x', '2026-11-10');
  raise exception 'anon이 정책을 씀';
exception when insufficient_privilege then null;
end $$;
-- TRUNCATE는 RLS를 거치지 않는다. 권한 회수가 좁혀지면 이 줄이 먼저 깨진다.
do $$
begin
  truncate public.eval_decisions;
  raise exception 'anon이 결정 기록을 비움';
exception when insufficient_privilege then null;
end $$;
reset role;

set local role authenticated;
set local request.jwt.claims = '{"sub": "10000000-0000-0000-0000-000000000037", "role": "authenticated"}';
do $$
declare
  t text;
begin
  foreach t in array array['eval_policies', 'eval_criteria_sets', 'eval_experiments', 'eval_decisions'] loop
    begin
      execute format('select 1 from public.%I', t);
      raise exception 'authenticated가 %를 읽음', t;
    exception when insufficient_privilege then null;
    end;
  end loop;
end $$;
do $$
begin
  update public.eval_decisions set status = 'adopted' where experiment_id = 'test-adoption';
  raise exception 'authenticated가 결정을 고침';
exception when insufficient_privilege then null;
end $$;
do $$
begin
  truncate public.eval_experiments cascade;
  raise exception 'authenticated가 실험 기록을 비움';
exception when insufficient_privilege then null;
end $$;
reset role;

-- 4. service_role은 읽고, 결정은 그대로다
set local role service_role;
do $$
begin
  if (select count(*) from public.eval_experiments where id like 'test-%') <> 2 then
    raise exception 'service_role이 실험을 읽지 못함';
  end if;
  if (select status from public.eval_decisions where experiment_id = 'test-adoption') <> 'not_adopted' then
    raise exception '결정이 바뀜';
  end if;
end $$;
reset role;

\echo '0037 eval_experiments: ok'
rollback;
