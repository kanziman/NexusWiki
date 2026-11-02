-- =============================================================================
-- NexusWiki 0028: Control Room [예산] 탭 집계 투영
--
-- 관련 이슈: #183, #186
-- 설계 근거: openspec/changes/ai-context-budget/design.md > D4
-- 계약:     openspec/changes/ai-context-budget/specs/ai-control-room/spec.md
--
-- 요청자 JWT(authenticated) 전용으로 월간 워크스페이스 예산 정산 현황, 사전 차단·절단으로
-- 절감된 실행 횟수, 그리고 editor 이상 멤버에게는 호출 경로별(ask, compile, conflict_check,
-- embed_source, embed_wiki, query_embedding) 토큰·비용 내역을 반환합니다.
-- =============================================================================

begin;

create function public.control_budget_snapshot(
  p_workspace_id uuid,
  p_since        timestamptz
)
returns table (
  can_view_workspace          boolean,
  cap_micros                  bigint,
  month_start                 timestamptz,
  reported_micros             bigint,
  pending_micros              bigint,
  budget_micros               bigint,
  unresolved_count            bigint,
  manual_review_count         bigint,
  over_reserve_count          bigint,
  ask_no_evidence_count       bigint,
  ask_context_truncated_count bigint,
  compile_truncated_count     bigint,
  compile_skipped_count       bigint,
  by_call_path                jsonb
)
language plpgsql
stable
security definer
set search_path = ''
as $fn$
declare
  -- ⚠️ UTC 일 단위로 내립니다. 경계를 초·밀리초 단위로 움직여 차이를 보면 개별 사용자의
  --    질문 시각과 비용을 역추적할 수 있어 작성자 비노출 불변식이 깨집니다.
  v_since       constant timestamptz := date_trunc('day', p_since, 'UTC');
  v_month_start constant timestamptz := date_trunc('month', now(), 'UTC');
  v_can_view_ws boolean;
  v_cap         bigint;
begin
  -- ⚠️ 이 검사를 지우면 security definer 함수가 RLS를 우회해 비멤버에게 타 테넌트의
  --    예산·비용 집계를 노출합니다.
  if not public.has_workspace_role(p_workspace_id, 'viewer') then
    raise exception '워크스페이스에 대한 조회 권한이 없습니다'
      using errcode = '42501';
  end if;

  v_can_view_ws := public.has_workspace_role(p_workspace_id, 'editor');

  select w.monthly_budget_micros
    into v_cap
    from public.workspaces w
   where w.id = p_workspace_id;

  if not found then
    raise exception '워크스페이스에 대한 조회 권한이 없습니다'
      using errcode = '42501';
  end if;

  return query
  with monthly as (
    select
      coalesce(sum(e.reported_micros), 0)::bigint as reported_micros,
      coalesce(sum(e.pending_micros), 0)::bigint as pending_micros,
      coalesce(sum(e.budget_micros), 0)::bigint as budget_micros
    from public.effective_usage e
    where e.workspace_id = p_workspace_id
      and e.occurred_at >= v_month_start
  ),
  ask_turns as (
    -- ⚠️ viewer는 본인이 만든 스레드의 Ask 턴만 집계하고, editor 이상은 워크스페이스 전체를
    --    익명 집계합니다. control_report는 작성자가 수정할 수 있으므로 jsonb_typeof로
    --    불리언 여부를 먼저 확인한 뒤 캐스팅합니다.
    select
      count(*) filter (where m.status = 'no-evidence')::bigint as no_evidence_count,
      count(*) filter (
        where jsonb_typeof(m.control_report -> 'budget' -> 'truncated') = 'boolean'
          and (m.control_report -> 'budget' ->> 'truncated')::boolean is true
      )::bigint as context_truncated_count
    from public.ask_messages m
    join public.ask_threads t on t.id = m.thread_id
    where m.workspace_id = p_workspace_id
      and m.created_at >= v_since
      and m.status <> 'streaming'
      and (v_can_view_ws or t.user_id = auth.uid())
  ),
  compile_savings as (
    select
      case
        when v_can_view_ws then (
          select count(*)::bigint
          from public.usage_events u
          where u.workspace_id = p_workspace_id
            and u.occurred_at >= v_since
            and u.metadata ->> 'call' = 'compile'
            and u.metadata ->> 'route' = 'TRUNCATED'
        )
        else 0::bigint
      end as truncated_count,
      case
        when v_can_view_ws then (
          (
            select count(*)::bigint
            from public.jobs j
            where j.workspace_id = p_workspace_id
              and j.created_at >= v_since
              and j.type = 'link_sync'
              and j.payload ->> 'compile_route' = 'SKIP_UNCHANGED'
          ) + (
            select count(*)::bigint
            from public.usage_events u
            where u.workspace_id = p_workspace_id
              and u.occurred_at >= v_since
              and u.metadata ->> 'call' = 'compile'
              and u.metadata ->> 'route' = 'SKIP_UNCHANGED'
          )
        )
        else 0::bigint
      end as skipped_count
  ),
  call_events as (
    -- ⚠️ 원시 metadata 문자열을 그대로 그룹 키로 쓰면 예상치 못한 문자열이 응답에 노출될 수 있으므로
    --    허용된 호출 경로 식별자 집합으로만 정규화합니다.
    select
      case
        when u.metadata ->> 'call' in (
          'ask', 'compile', 'conflict_check', 'embed_source', 'embed_wiki', 'query_embedding'
        ) then u.metadata ->> 'call'
        when u.kind = 'embedding' then 'embed_source'
        else 'compile'
      end as call_path,
      u.kind as kind,
      coalesce(u.prompt_tokens, 0)::bigint as prompt_tokens,
      coalesce(u.completion_tokens, 0)::bigint as completion_tokens,
      coalesce(u.total_tokens, 0)::bigint as total_tokens,
      u.cost_micros::bigint as reported_micros,
      0::bigint as pending_micros,
      u.cost_micros::bigint as budget_micros
    from public.usage_events u
    where v_can_view_ws
      and u.workspace_id = p_workspace_id
      and u.occurred_at >= v_since
      and u.ask_call_id is null
    union all
    select
      'ask' as call_path,
      'llm' as kind,
      coalesce(u.prompt_tokens, 0)::bigint as prompt_tokens,
      coalesce(u.completion_tokens, 0)::bigint as completion_tokens,
      coalesce(u.total_tokens, 0)::bigint as total_tokens,
      coalesce(s.cost_micros, u.cost_micros, 0)::bigint as reported_micros,
      case
        when c.status in ('settled', 'released') then 0::bigint
        else greatest(c.reserve_micros - coalesce(u.cost_micros, 0), 0)::bigint
      end as pending_micros,
      case
        when c.status = 'released' then 0::bigint
        when s.call_id is not null then s.cost_micros::bigint
        else greatest(c.reserve_micros, coalesce(u.cost_micros, 0))::bigint
      end as budget_micros
    from public.ask_cost_calls c
    left join public.ask_cost_settlements s on s.call_id = c.id
    left join public.usage_events u on u.ask_call_id = c.id
    where v_can_view_ws
      and c.workspace_id = p_workspace_id
      and c.created_at >= v_since
      and c.status <> 'released'
  ),
  grouped_calls as (
    select
      ce.call_path,
      ce.kind,
      count(*)::bigint as call_count,
      coalesce(sum(ce.prompt_tokens), 0)::bigint as prompt_tokens,
      coalesce(sum(ce.completion_tokens), 0)::bigint as completion_tokens,
      coalesce(sum(ce.total_tokens), 0)::bigint as total_tokens,
      coalesce(sum(ce.reported_micros), 0)::bigint as reported_micros,
      coalesce(sum(ce.pending_micros), 0)::bigint as pending_micros,
      coalesce(sum(ce.budget_micros), 0)::bigint as budget_micros
    from call_events ce
    group by ce.call_path, ce.kind
  )
  select
    v_can_view_ws,
    v_cap,
    v_month_start,
    monthly.reported_micros,
    monthly.pending_micros,
    monthly.budget_micros,
    case
      when v_can_view_ws then (
        select count(*)::bigint
        from public.ask_cost_calls c
        where c.workspace_id = p_workspace_id
          and c.created_at >= v_month_start
          and c.status in ('reserved', 'in_flight', 'unresolved')
      )
      else 0::bigint
    end,
    case
      when v_can_view_ws then (
        select count(*)::bigint
        from public.ask_cost_calls c
        where c.workspace_id = p_workspace_id
          and c.created_at >= v_month_start
          and c.manual_review
          and c.status = 'unresolved'
      )
      else 0::bigint
    end,
    case
      when v_can_view_ws then (
        select count(*)::bigint
        from public.ask_cost_calls c
        join public.ask_cost_settlements s on s.call_id = c.id
        where c.workspace_id = p_workspace_id
          and c.created_at >= v_month_start
          and s.cost_micros > c.reserve_micros
      )
      else 0::bigint
    end,
    ask_turns.no_evidence_count,
    ask_turns.context_truncated_count,
    compile_savings.truncated_count,
    compile_savings.skipped_count,
    case
      when v_can_view_ws then coalesce(
        (
          select jsonb_agg(
            jsonb_build_object(
              'call', gc.call_path,
              'kind', gc.kind,
              'call_count', gc.call_count,
              'prompt_tokens', gc.prompt_tokens,
              'completion_tokens', gc.completion_tokens,
              'total_tokens', gc.total_tokens,
              'reported_micros', gc.reported_micros,
              'pending_micros', gc.pending_micros,
              'budget_micros', gc.budget_micros
            )
            order by gc.budget_micros desc, gc.call_path asc
          )
          from grouped_calls gc
        ),
        '[]'::jsonb
      )
      else '[]'::jsonb
    end
  from monthly, ask_turns, compile_savings;
end
$fn$;

comment on function public.control_budget_snapshot(uuid, timestamptz) is
  'Control Room [예산] 탭 전용 집계. viewer에게는 월간 예산 상한·소진액과 본인의 Ask 절감 카운트만 돌려주고, editor 이상에게는 워크스페이스 전체 절감 카운트와 호출 경로별 토큰·비용 내역을 함께 돌려준다. 사용자·스레드·trace 식별자나 본문 텍스트는 반환하지 않는다.';

-- ⚠️ 기본 실행 권한을 회수하지 않으면 anon이나 service_role이 호출할 수 있습니다.
revoke all on function public.control_budget_snapshot(uuid, timestamptz)
  from public, anon, service_role;
grant execute on function public.control_budget_snapshot(uuid, timestamptz)
  to authenticated;

notify pgrst, 'reload schema';

commit;
