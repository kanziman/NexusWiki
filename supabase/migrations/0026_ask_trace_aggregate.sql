-- =============================================================================
-- NexusWiki 0026: 작성자를 드러내지 않는 Ask 집계
--
-- 관련 이슈: #166
-- 설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D9
-- 계약:     openspec/changes/ai-control-flow-accounting/specs/ai-control-room/spec.md
--
-- ask_messages는 작성자 전용 RLS라 editor가 직접 읽을 수 없습니다. 그래서 집계값만 돌려주는
-- security definer 함수를 둡니다. enqueue_source_job과 같은 패턴입니다.
-- =============================================================================

begin;

create function public.ask_trace_aggregate(
  p_workspace_id uuid,
  p_since        timestamptz
)
returns table (
  turn_count           bigint,
  resolved_count       bigint,
  no_evidence_count    bigint,
  error_count          bigint,
  decision_counts      jsonb,
  p50_total_ms         int,
  p95_total_ms         int,
  total_cost_micros    bigint,
  incomplete_call_count bigint
)
language plpgsql
stable
security definer
set search_path = public
as $fn$
begin
  -- ⚠️ 이 검사가 빠지면 BYPASSRLS처럼 동작해 비멤버가 다른 테넌트의 집계를 읽습니다.
  if not public.has_workspace_role(p_workspace_id, 'editor') then
    raise exception '워크스페이스에 대한 편집 권한이 없습니다'
      using errcode = '42501';
  end if;

  return query
  with turns as (
    select m.status, m.control_report
    from public.ask_messages m
    where m.workspace_id = p_workspace_id
      and m.created_at >= p_since
      and m.status <> 'streaming'
  ),
  durations as (
    -- ⚠️ control_report는 작성자가 수정할 수 있습니다. 타입을 확인하지 않고 캐스팅하면 한 사람이
    --    넣은 문자열 때문에 워크스페이스 전체의 집계가 실패합니다.
    select (t.control_report ->> 'total_ms')::numeric as total_ms
    from turns t
    where jsonb_typeof(t.control_report -> 'total_ms') = 'number'
  ),
  decisions as (
    -- 알려진 값만 셉니다. 임의의 문자열이 집계 키로 다른 멤버에게 전달되면 안 됩니다.
    select t.control_report -> 'route' ->> 'decision' as decision, count(*) as n
    from turns t
    where t.control_report -> 'route' ->> 'decision'
      in ('NO_EVIDENCE', 'LOOKUP', 'SINGLE_KIND', 'STANDARD')
    group by 1
  ),
  usage as (
    select
      coalesce(sum(u.cost_micros), 0)::bigint as total_cost_micros,
      count(*) filter (where u.metadata ->> 'incomplete' = 'true') as incomplete_call_count
    from public.usage_events u
    where u.workspace_id = p_workspace_id
      and u.occurred_at >= p_since
      and u.metadata ->> 'call' = 'ask'
  )
  select
    (select count(*) from turns),
    (select count(*) from turns t where t.status = 'resolved'),
    (select count(*) from turns t where t.status = 'no-evidence'),
    (select count(*) from turns t where t.status = 'error'),
    (select coalesce(jsonb_object_agg(d.decision, d.n), '{}'::jsonb) from decisions d),
    (select percentile_cont(0.5) within group (order by d.total_ms)::int from durations d),
    (select percentile_cont(0.95) within group (order by d.total_ms)::int from durations d),
    usage.total_cost_micros,
    usage.incomplete_call_count
  from usage;
end
$fn$;

comment on function public.ask_trace_aggregate(uuid, timestamptz) is
  'editor 이상에게 Ask 건수·지연·결정 분포·비용의 집계만 돌려준다. 사용자·스레드·trace 식별자를 반환하지 않는다. 결정 분포와 지연은 작성자가 수정할 수 있는 값에서 나오므로 참고 수치이고, 비용은 service_role이 쓴 usage_events에서 나온다.';

-- ⚠️ 새로 만든 함수에는 기본 권한이 붙습니다. 회수하지 않으면 anon이 실행할 수 있습니다.
revoke all on function public.ask_trace_aggregate(uuid, timestamptz) from public, anon, service_role;
grant execute on function public.ask_trace_aggregate(uuid, timestamptz) to authenticated;

notify pgrst, 'reload schema';

commit;
