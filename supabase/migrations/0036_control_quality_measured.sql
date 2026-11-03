-- =============================================================================
-- NexusWiki 0036: Control Room [품질] 탭의 측정 건수
--
-- 관련 이슈: #215, #216
-- 설계 근거: openspec/changes/control-quality-measured-coverage/design.md > D1, D2, D3
-- 계약:     openspec/changes/control-quality-measured-coverage/specs/ai-control-room/spec.md
--
-- 품질 판정 기록이 없는 턴과 호출을 위반 없음으로 세지 않도록 측정 건수를 분리한다.
-- 요청자 JWT 전용이며 본문과 사용자 식별자를 돌려주지 않는다. viewer는 본인 Ask 집계만 받고
-- 수집 경로 집계는 0이다. 저장된 데이터는 바꾸지 않는다.
--
-- ⚠️ 운영 적용 순서는 0036, API, 대시보드다. 새 API가 이 컬럼을 받지 못하면 측정 건수가 0이 되어
--    화면이 측정 기록 없음으로 잘못 표시된다. 기존 API는 추가 컬럼을 무시한다.
-- =============================================================================

begin;

-- 반환 컬럼을 바꾸려면 create or replace로는 안 된다. 트랜잭션 안에서 다시 만들어 함수가 없는
-- 순간이 다른 연결에 보이지 않게 한다.
drop function public.control_quality_snapshot(uuid, timestamptz);

create function public.control_quality_snapshot(
  p_workspace_id uuid,
  p_since        timestamptz
)
returns table (
  can_view_workspace      boolean,
  ask_turns               bigint,
  ask_measured_turns      bigint,
  ask_violation_turns     bigint,
  ask_no_citation_turns   bigint,
  ask_fabricated_turns    bigint,
  ask_repair_attempted    bigint,
  ask_repaired            bigint,
  ask_fallback            bigint,
  structured_calls        bigint,
  structured_measured_calls bigint,
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
      -- ⚠️ 객체인지만 보면 안 된다. `off`는 계약 검사를 건너뛰고도 빈 위반 목록을 저장하고, 형식이
      --    잘못된 기록은 위반 없음과 구별되지 않아 미측정이 위반 0건으로 보인다.
      coalesce(
        jsonb_typeof(m.control_report -> 'quality') = 'object'
          and m.control_report -> 'quality' ->> 'mode' in ('shadow', 'enforce')
          and jsonb_typeof(m.control_report -> 'quality' -> 'violations') = 'array'
          and jsonb_typeof(m.control_report -> 'quality' -> 'repair_attempted') = 'boolean'
          and jsonb_typeof(m.control_report -> 'quality' -> 'repaired') = 'boolean',
        false
      ) as measured,
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
      count(*) filter (where measured)::bigint as measured_turns,
      count(*) filter (where measured and jsonb_array_length(violations) > 0)::bigint as violation_turns,
      count(*) filter (where measured and violations ? 'no_citation')::bigint as no_citation_turns,
      count(*) filter (where measured and violations ? 'fabricated_anchor')::bigint as fabricated_turns,
      count(*) filter (where measured and repair_attempted is true)::bigint as repair_attempted,
      count(*) filter (where measured and repaired is true)::bigint as repaired,
      -- ⚠️ 측정 전 Fallback을 세면 측정 건수보다 큰 지표가 나올 수 있다.
      count(*) filter (where measured and status = 'fallback')::bigint as fallback
    from turns
  ),
  usage_rows as (
    select
      u.metadata,
      -- ⚠️ 시도 기록에는 항상 정책 버전이 함께 남는다. llm_gateway.py에서 이 키를 빼면 모든 호출이
      --    미측정으로 보인다. 정상 호출은 위반 키가 없어 그 키들로는 측정 여부를 알 수 없다.
      u.metadata ? 'policy_version' as measured
    from public.usage_events u
    where v_can_view_ws
      and u.workspace_id = p_workspace_id
      and u.occurred_at >= v_since
      and u.metadata ->> 'call' in ('compile', 'conflict_check')
  ),
  structured as (
    select
      count(*)::bigint as calls,
      count(*) filter (where measured)::bigint as measured_calls,
      count(*) filter (where measured and r.metadata ->> 'fence_stripped' = 'true')::bigint as fence_stripped,
      count(*) filter (where measured and r.metadata ->> 'violation' = 'json_invalid')::bigint as json_invalid,
      count(*) filter (where measured and r.metadata ->> 'violation' = 'schema_invalid')::bigint as schema_invalid,
      count(*) filter (where measured and r.metadata ->> 'violation' = 'semantic_invalid')::bigint as semantic_invalid,
      count(*) filter (where measured and r.metadata ->> 'violation' = 'missing_content')::bigint as missing_content,
      count(*) filter (where measured and r.metadata ->> 'exhausted' = 'true')::bigint as exhausted
    from usage_rows r
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
    ask.measured_turns,
    ask.violation_turns,
    ask.no_citation_turns,
    ask.fabricated_turns,
    ask.repair_attempted,
    ask.repaired,
    ask.fallback,
    structured.calls,
    structured.measured_calls,
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
  'Control Room [품질] 탭 전용 집계. 측정된 데이터만 지표에 센다. viewer에게는 본인 Ask 집계만 준다. 본문과 사용자 식별자는 없다.';

-- ⚠️ 함수를 다시 만들면 기본 실행 권한이 되살아난다. 회수하지 않으면 anon이 호출할 수 있다.
revoke all on function public.control_quality_snapshot(uuid, timestamptz)
  from public, anon, service_role;
grant execute on function public.control_quality_snapshot(uuid, timestamptz)
  to authenticated;

notify pgrst, 'reload schema';

commit;
