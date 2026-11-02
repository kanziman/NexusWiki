-- =============================================================================
-- NexusWiki 0034: Control Room [리스크] 탭 집계
--
-- 관련 이슈: #196, #200
-- 계약: openspec/changes/ai-control-risk-policy/specs/ai-control-room/spec.md
--
-- 요청자 JWT 전용이다. 본문과 사용자 식별자를 돌려주지 않는다.
-- =============================================================================

begin;

create function public.control_risk_snapshot(
  p_workspace_id uuid,
  p_since        timestamptz
)
returns table (
  can_view_workspace boolean,
  revisions_low      bigint,
  revisions_medium   bigint,
  revisions_high     bigint,
  pending_proposals  bigint,
  approved_proposals bigint,
  applied_proposals  bigint,
  rejected_proposals bigint,
  policy_versions    jsonb
)
language plpgsql
stable
security definer
set search_path = ''
as $fn$
declare
  v_since       constant timestamptz := date_trunc('day', p_since, 'UTC');
  v_can_view_ws boolean;
begin
  -- ⚠️ 이 검사를 지우면 definer 함수가 RLS를 우회해 다른 테넌트의 집계를 노출한다.
  if not public.has_workspace_role(p_workspace_id, 'viewer') then
    raise exception '워크스페이스에 대한 조회 권한이 없습니다' using errcode = '42501';
  end if;

  v_can_view_ws := public.has_workspace_role(p_workspace_id, 'editor');

  return query
  select
    v_can_view_ws,
    (select count(*)::bigint from public.wiki_page_revisions r
      where r.workspace_id = p_workspace_id and r.created_at >= v_since and r.risk_level = 'low'),
    (select count(*)::bigint from public.wiki_page_revisions r
      where r.workspace_id = p_workspace_id and r.created_at >= v_since and r.risk_level = 'medium'),
    (select count(*)::bigint from public.wiki_page_revisions r
      where r.workspace_id = p_workspace_id and r.created_at >= v_since and r.risk_level = 'high'),
    (select count(*)::bigint from public.wiki_write_proposals p
      where p.workspace_id = p_workspace_id and p.status = 'pending'),
    -- 승인했지만 적용 잡이 끝나지 않은 제안이다. 잡이 죽으면 여기에 남아 드러난다.
    (select count(*)::bigint from public.wiki_write_proposals p
      where p.workspace_id = p_workspace_id and p.status = 'approved'),
    (select count(*)::bigint from public.wiki_write_proposals p
      where p.workspace_id = p_workspace_id and p.created_at >= v_since and p.status = 'applied'),
    (select count(*)::bigint from public.wiki_write_proposals p
      where p.workspace_id = p_workspace_id and p.created_at >= v_since and p.status = 'rejected'),
    -- ⚠️ viewer에게 호출 경로 메타데이터를 주지 않는다.
    case
      when v_can_view_ws then coalesce(
        (select jsonb_agg(distinct u.metadata ->> 'policy_version')
           from public.usage_events u
          where u.workspace_id = p_workspace_id
            and u.occurred_at >= v_since
            and u.metadata ? 'policy_version'),
        '[]'::jsonb
      )
      else '[]'::jsonb
    end;
end
$fn$;

revoke all on function public.control_risk_snapshot(uuid, timestamptz)
  from public, anon, service_role;
grant execute on function public.control_risk_snapshot(uuid, timestamptz)
  to authenticated;

notify pgrst, 'reload schema';

commit;
