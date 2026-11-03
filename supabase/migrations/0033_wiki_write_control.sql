-- =============================================================================
-- NexusWiki 0033: 위키 쓰기 개정 이력과 승인 보류
--
-- 관련 이슈: #196, #198
-- 설계 근거: openspec/changes/ai-control-risk-policy/design.md > D3, D4, D6
-- 계약:     openspec/changes/ai-control-risk-policy/specs/wiki-compilation/spec.md
--
-- 전부 추가형이라 이전 코드와 호환된다.
-- =============================================================================

begin;

-- 컴파일이 공개 페이지인지 판정하는 데 필요하다. 없으면 기존 페이지 재컴파일이 403으로 실패한다.
-- 발행본 본문은 쓰기 판정에 필요 없으므로 식별 컬럼만 연다.
grant select (wiki_page_id, workspace_id) on public.wiki_page_publications to service_role;

create table public.wiki_page_revisions (
  id               uuid primary key default gen_random_uuid(),
  workspace_id     uuid not null references public.workspaces (id) on delete cascade,
  wiki_id          uuid not null,
  raw_source_id    uuid,
  job_id           uuid not null,
  risk_level       text not null check (risk_level in ('low', 'medium', 'high')),
  reason           text not null check (char_length(reason) <= 64),
  previous_title   text not null,
  previous_content text not null,
  created_at       timestamptz not null default now(),

  -- ⚠️ 잡은 at-least-once다. 이 키가 없으면 재실행이 같은 개정을 다시 쌓는다.
  constraint wiki_page_revisions_job_key unique (wiki_id, job_id),
  constraint wiki_page_revisions_wiki_fkey
    foreign key (wiki_id, workspace_id)
    references public.wiki_pages (id, workspace_id) on delete cascade
);

create index wiki_page_revisions_workspace_idx
  on public.wiki_page_revisions (workspace_id, created_at desc);

alter table public.wiki_page_revisions enable row level security;

create policy wiki_page_revisions_select_member on public.wiki_page_revisions
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

revoke all on public.wiki_page_revisions from public, anon, authenticated;
grant select on public.wiki_page_revisions to authenticated;
grant select, insert on public.wiki_page_revisions to service_role;

create table public.wiki_write_proposals (
  id                  uuid primary key default gen_random_uuid(),
  workspace_id        uuid not null references public.workspaces (id) on delete cascade,
  wiki_id             uuid not null,
  raw_source_id       uuid not null,
  status              text not null default 'pending'
                        check (status in ('pending', 'approved', 'rejected', 'applied')),
  risk_reason         text not null check (char_length(risk_reason) <= 64),
  proposed_title      text not null,
  proposed_category   text not null,
  proposed_aliases    jsonb not null default '[]'::jsonb,
  proposed_confidence text not null,
  proposed_content    text not null,
  evidence_chunk_ids  uuid[] not null default '{}',
  decided_by          uuid references auth.users (id) on delete set null,
  decided_at          timestamptz,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),

  constraint wiki_write_proposals_wiki_fkey
    foreign key (wiki_id, workspace_id)
    references public.wiki_pages (id, workspace_id) on delete cascade,
  constraint wiki_write_proposals_raw_source_fkey
    foreign key (raw_source_id, workspace_id)
    references public.raw_sources (id, workspace_id) on delete cascade
);

-- 재컴파일이 대기 제안을 쌓지 않게 한다. 처리된 제안의 기록은 남긴다.
create unique index wiki_write_proposals_pending_key
  on public.wiki_write_proposals (wiki_id, raw_source_id)
  where status = 'pending';

create index wiki_write_proposals_workspace_idx
  on public.wiki_write_proposals (workspace_id, status, created_at desc);

alter table public.wiki_write_proposals enable row level security;

-- ⚠️ 제안 본문은 검토 권한이 있는 사람만 본다. viewer는 리스크 탭의 집계만 받는다.
create policy wiki_write_proposals_select_editor on public.wiki_write_proposals
  for select to authenticated
  using (public.has_workspace_role(workspace_id, 'editor'));

revoke all on public.wiki_write_proposals from public, anon, authenticated;
grant select on public.wiki_write_proposals to authenticated;
grant select, insert, update on public.wiki_write_proposals to service_role;

create function public.upsert_wiki_write_proposal(
  p_workspace_id uuid,
  p_wiki_id uuid,
  p_raw_source_id uuid,
  p_risk_reason text,
  p_title text,
  p_category text,
  p_aliases jsonb,
  p_confidence text,
  p_content text,
  p_evidence_chunk_ids uuid[]
)
returns uuid
language sql
security invoker
set search_path = public
as $$
  insert into public.wiki_write_proposals (
    workspace_id, wiki_id, raw_source_id, risk_reason, proposed_title, proposed_category,
    proposed_aliases, proposed_confidence, proposed_content, evidence_chunk_ids
  )
  values (
    p_workspace_id, p_wiki_id, p_raw_source_id, p_risk_reason, p_title, p_category,
    coalesce(p_aliases, '[]'::jsonb), p_confidence, p_content, coalesce(p_evidence_chunk_ids, '{}')
  )
  on conflict (wiki_id, raw_source_id) where status = 'pending'
  do update set
    risk_reason = excluded.risk_reason,
    proposed_title = excluded.proposed_title,
    proposed_category = excluded.proposed_category,
    proposed_aliases = excluded.proposed_aliases,
    proposed_confidence = excluded.proposed_confidence,
    proposed_content = excluded.proposed_content,
    evidence_chunk_ids = excluded.evidence_chunk_ids,
    updated_at = now()
  returning id;
$$;

revoke all on function public.upsert_wiki_write_proposal(
  uuid, uuid, uuid, text, text, text, jsonb, text, text, uuid[]
) from public, anon, authenticated;
grant execute on function public.upsert_wiki_write_proposal(
  uuid, uuid, uuid, text, text, text, jsonb, text, text, uuid[]
) to service_role;

-- 요청자 JWT로 호출한다. 제안 테이블에 사용자 쓰기 권한이 없으므로 definer다.
-- ⚠️ 승인과 잡 등록이 한 트랜잭션이어야 한다. 나뉘면 승인됐는데 반영되지 않는 제안이 남는다.
create function public.decide_wiki_write_proposal(
  p_workspace_id uuid,
  p_proposal_id uuid,
  p_decision text
)
returns table (id uuid, status text)
language plpgsql
security definer
set search_path = ''
as $fn$
declare
  v_row public.wiki_write_proposals%rowtype;
begin
  -- ⚠️ 이 검사를 지우면 definer 함수가 RLS를 우회해 누구나 위키 변경을 승인할 수 있다.
  if not public.has_workspace_role(p_workspace_id, 'editor') then
    raise exception '위키 변경을 승인할 권한이 없습니다' using errcode = '42501';
  end if;
  if p_decision not in ('approved', 'rejected') then
    raise exception 'invalid proposal decision' using errcode = '23514';
  end if;

  update public.wiki_write_proposals p
     set status = p_decision,
         decided_by = (select auth.uid()),
         decided_at = now(),
         updated_at = now()
   where p.id = p_proposal_id
     and p.workspace_id = p_workspace_id
     and p.status = 'pending'
  returning p.* into v_row;

  -- 없거나 이미 처리된 제안은 0행이다. 라우터가 409로 바꾼다.
  if not found then
    return;
  end if;

  if p_decision = 'approved' then
    insert into public.jobs (workspace_id, type, payload, trace_id)
    values (
      p_workspace_id,
      'wiki_proposal_apply',
      jsonb_build_object(
        'target_id', v_row.id::text,
        'proposal_id', v_row.id::text,
        'raw_source_id', v_row.raw_source_id::text
      ),
      gen_random_uuid()
    );
  end if;

  id := v_row.id;
  status := v_row.status;
  return next;
end
$fn$;

revoke all on function public.decide_wiki_write_proposal(uuid, uuid, text)
  from public, anon, service_role;
grant execute on function public.decide_wiki_write_proposal(uuid, uuid, text)
  to authenticated;

notify pgrst, 'reload schema';

commit;
