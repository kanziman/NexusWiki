-- =============================================================================
-- NexusWiki 0024: 사용량 행의 trace와 호출 소요 시간
--
-- 관련 이슈: #161
-- 설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D1, D4
-- 계약:     openspec/changes/ai-control-flow-accounting/specs/usage-guardrails/spec.md
--
-- 추가 전용입니다. 월 상한 계산은 cost_micros 합만 보므로 이 파일로 달라지지 않습니다.
-- =============================================================================

begin;

alter table public.usage_events
  -- null을 허용합니다. 이전 행에는 값이 없고, 백필하지 않습니다.
  add column trace_id uuid,
  -- 음수는 시계 오류이며, 그대로 두면 trace 합계가 조용히 틀립니다.
  add column duration_ms int check (duration_ms is null or duration_ms >= 0);

-- 부분 인덱스입니다. trace 상세 화면 말고는 이 조회가 없고, 과거 행은 값이 없습니다.
create index usage_events_workspace_trace_idx
  on public.usage_events (workspace_id, trace_id)
  where trace_id is not null;

comment on column public.usage_events.trace_id is
  '이 호출을 일으킨 요청의 trace. 멤버가 SELECT할 수 있으므로 식별 불가능한 값이어야 하며, Ask trace의 상세는 ask_messages의 작성자 RLS가 막는다.';
comment on column public.usage_events.duration_ms is
  '공급자 호출 소요 시간. 재시도는 시도마다 별도 행이다.';

notify pgrst, 'reload schema';

commit;
