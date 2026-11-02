-- =============================================================================
-- NexusWiki 0031: Control Room [품질] 탭 집계
--
-- 관련 이슈: #188, #192
-- 설계 근거: openspec/changes/ai-control-output-contract/design.md > D9
-- 계약:     openspec/changes/ai-control-output-contract/specs/ai-control-room/spec.md
--
-- 요청자 JWT 전용이다. 본문과 사용자 식별자를 돌려주지 않는다. viewer는 본인 Ask 집계만 받고
-- 수집 경로 집계는 0이다.
-- =============================================================================

begin;

create function public.control_quality_snapshot(
  p_workspace_id uuid,
  p_since        timestamptz
)
returns table (
  can_view_workspace      boolean,
  ask_turns               bigint,
  ask_violation_turns     bigint,
  ask_no_citation_turns   bigint,
  ask_fabricated_turns    bigint,
  ask_repair_attempted    bigint,
  ask_repaired            bigint,
  ask_fallback            bigint,
  structured_calls        bigint,
  structured_fence_stripped bigint,
  structured_json_invalid bigint,
  structured_schema_invalid bigint,
  structured_semantic_invalid bigint,
  structured_missing_content bigint,
  structured_exhausted    bigint,
  wiki_pages_total        bigint,
  wiki_pages_with_evidence bigint
)
language plpgsql
stable
security definer
set search_path = ''
as $fn$
declare
  -- ⚠️ UTC 일 단위로 내린다. 초 단위 경계를 옮겨 가며 차이를 재면 개별 턴을 역추적할 수 있다.
  v_since       constant timestamptz := date_trunc('day', p_since, 'UTC');
  v_can_view_ws boolean;
begin
  -- ⚠️ 이 검사를 지우면 security definer 함수가 RLS를 우회해 다른 테넌트의 집계를 노출한다.
  if not public.has_workspace_role(p_workspace_id, 'viewer') then
    raise exception '워크스페이스에 대한 조회 권한이 없습니다'
      using errcode = '42501';
  end if;

  v_can_view_ws := public.has_workspace_role(p_workspace_id, 'editor');

  return query
  with turns as (
    -- ⚠️ control_report는 작성자가 쓸 수 있는 값이다. 타입을 확인한 뒤에만 읽는다. 잘못된 값이
    --    집계 전체를 실패시키면 다른 멤버의 화면까지 깨진다.
    select
      case
        when jsonb_typeof(m.control_report -> 'quality' -> 'violations') = 'array'
          then m.control_report -> 'quality' -> 'violations'
        else '[]'::jsonb
      end as violations,
      jsonb_typeof(m.control_report -> 'quality' -> 'repair_attempted') = 'boolean'
        and (m.control_report -> 'quality' ->> 'repair_attempted')::boolean as repair_attempted,
      jsonb_typeof(m.control_report -> 'quality' -> 'repaired') = 'boolean'
        and (m.control_report -> 'quality' ->> 'repaired')::boolean as repaired,
      m.status
    from public.ask_messages m
    join public.ask_threads t on t.id = m.thread_id
    where m.workspace_id = p_workspace_id
      and m.created_at >= v_since
      and m.status in ('resolved', 'fallback')
      and (v_can_view_ws or t.user_id = (select auth.uid()))
  ),
  ask as (
    select
      count(*)::bigint as turns,
      count(*) filter (where jsonb_array_length(violations) > 0)::bigint as violation_turns,
      count(*) filter (where violations ? 'no_citation')::bigint as no_citation_turns,
      count(*) filter (where violations ? 'fabricated_anchor')::bigint as fabricated_turns,
      count(*) filter (where repair_attempted is true)::bigint as repair_attempted,
      count(*) filter (where repaired is true)::bigint as repaired,
      count(*) filter (where status = 'fallback')::bigint as fallback
    from turns
  ),
  structured as (
    select
      count(*)::bigint as calls,
      count(*) filter (where u.metadata ->> 'fence_stripped' = 'true')::bigint as fence_stripped,
      count(*) filter (where u.metadata ->> 'violation' = 'json_invalid')::bigint as json_invalid,
      count(*) filter (where u.metadata ->> 'violation' = 'schema_invalid')::bigint as schema_invalid,
      count(*) filter (where u.metadata ->> 'violation' = 'semantic_invalid')::bigint as semantic_invalid,
      count(*) filter (where u.metadata ->> 'violation' = 'missing_content')::bigint as missing_content,
      count(*) filter (where u.metadata ->> 'exhausted' = 'true')::bigint as exhausted
    from public.usage_events u
    where v_can_view_ws
      and u.workspace_id = p_workspace_id
      and u.occurred_at >= v_since
      and u.metadata ->> 'call' in ('compile', 'conflict_check')
  ),
  pages as (
    select
      count(*)::bigint as total,
      count(*) filter (
        where exists (select 1 from public.wiki_page_evidence e where e.wiki_id = w.id)
      )::bigint as with_evidence
    from public.wiki_pages w
    where v_can_view_ws
      and w.workspace_id = p_workspace_id
  )
  select
    v_can_view_ws,
    ask.turns,
    ask.violation_turns,
    ask.no_citation_turns,
    ask.fabricated_turns,
    ask.repair_attempted,
    ask.repaired,
    ask.fallback,
    structured.calls,
    structured.fence_stripped,
    structured.json_invalid,
    structured.schema_invalid,
    structured.semantic_invalid,
    structured.missing_content,
    structured.exhausted,
    pages.total,
    pages.with_evidence
  from ask, structured, pages;
end
$fn$;

comment on function public.control_quality_snapshot(uuid, timestamptz) is
  'Control Room [품질] 탭 전용 집계. viewer에게는 본인 Ask 집계만 준다. 본문과 사용자 식별자는 없다.';

-- ⚠️ 기본 실행 권한을 회수하지 않으면 anon이 호출할 수 있다.
revoke all on function public.control_quality_snapshot(uuid, timestamptz)
  from public, anon, service_role;
grant execute on function public.control_quality_snapshot(uuid, timestamptz)
  to authenticated;

notify pgrst, 'reload schema';

commit;
