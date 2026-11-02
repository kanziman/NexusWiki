-- =============================================================================
-- NexusWiki 0030: 위키 페이지의 근거 원문 청크
--
-- 관련 이슈: #188, #191
-- 설계 근거: openspec/changes/ai-control-output-contract/design.md > D8
-- 계약:     openspec/changes/ai-control-output-contract/specs/wiki-compilation/spec.md
--
-- `wiki_pages.sources`는 문서 단위 합집합이다. 위키에서 원문으로 가는 추적을 청크 단위로
-- 강화하려고 페이지·청크 쌍을 따로 둔다. jsonb 배열로 두면 재처리로 청크가 지워졌을 때
-- 매달린 참조가 남는다.
-- =============================================================================

begin;

-- ⚠️ 복합 FK의 대상이다. 없으면 다른 워크스페이스의 청크를 근거로 가리키는 행을 막지 못한다.
alter table public.source_chunks
  add constraint source_chunks_id_workspace_key unique (id, workspace_id);

create table public.wiki_page_evidence (
  wiki_id       uuid not null,
  chunk_id      uuid not null,
  workspace_id  uuid not null references public.workspaces (id) on delete cascade,
  raw_source_id uuid not null,
  created_at    timestamptz not null default now(),

  -- 재실행해도 행이 늘지 않게 하는 멱등 키다.
  primary key (wiki_id, chunk_id),
  constraint wiki_page_evidence_wiki_fkey
    foreign key (wiki_id, workspace_id)
    references public.wiki_pages (id, workspace_id) on delete cascade,
  constraint wiki_page_evidence_chunk_fkey
    foreign key (chunk_id, workspace_id)
    references public.source_chunks (id, workspace_id) on delete cascade
);

create index wiki_page_evidence_chunk_idx on public.wiki_page_evidence (chunk_id);
create index wiki_page_evidence_scope_idx
  on public.wiki_page_evidence (workspace_id, wiki_id, raw_source_id);

alter table public.wiki_page_evidence enable row level security;

-- anon에는 정책과 권한을 주지 않는다. 쓰기는 워커 전용이다.
create policy wiki_page_evidence_select_member on public.wiki_page_evidence
  for select to authenticated
  using (public.is_workspace_member(workspace_id));

revoke all on public.wiki_page_evidence from public, anon, authenticated;
grant select on public.wiki_page_evidence to authenticated;
grant select, insert, delete on public.wiki_page_evidence to service_role;

-- ⚠️ 범위가 (페이지, 원문)이다. 페이지 전체를 지우면 같은 페이지를 함께 만든 다른 원문의
--    근거가 재컴파일 때 사라진다.
-- ⚠️ service_role은 BYPASSRLS다. 청크가 그 워크스페이스·원문 소속인지 함수 안에서 거른다.
create function public.replace_wiki_page_evidence(
  p_workspace_id uuid,
  p_wiki_id uuid,
  p_raw_source_id uuid,
  p_chunk_ids uuid[]
)
returns integer
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_inserted integer;
begin
  delete from public.wiki_page_evidence e
   where e.workspace_id = p_workspace_id
     and e.wiki_id = p_wiki_id
     and e.raw_source_id = p_raw_source_id;

  insert into public.wiki_page_evidence (wiki_id, chunk_id, workspace_id, raw_source_id)
  select p_wiki_id, c.id, p_workspace_id, p_raw_source_id
    from public.source_chunks c
   where c.workspace_id = p_workspace_id
     and c.raw_source_id = p_raw_source_id
     and c.id = any (coalesce(p_chunk_ids, '{}'))
  -- 다른 원문이 같은 쌍을 이미 가질 수 없지만, 동시 재실행에서 예외로 잡이 죽지 않게 한다.
  on conflict (wiki_id, chunk_id) do nothing;

  get diagnostics v_inserted = row_count;
  return v_inserted;
end;
$$;

revoke all on function public.replace_wiki_page_evidence(uuid, uuid, uuid, uuid[])
  from public, anon, authenticated;
grant execute on function public.replace_wiki_page_evidence(uuid, uuid, uuid, uuid[])
  to service_role;

-- 전역 컴파일 템플릿에 근거 표기를 추가한다. 이미 적용된 0006은 고칠 수 없어 앞으로 나아간다.
-- ⚠️ 워크스페이스가 만든 템플릿은 건드리지 않는다. 그 경우 evidence가 비어도 컴파일은 성공한다.
update public.prompt_templates
   set system_prompt = system_prompt || $prompt$

## 근거 표시

본문의 각 청크 앞에는 `[[src:s1]]` 같은 앵커가 붙어 있습니다.

- 각 페이지에 `evidence` 필드를 추가하고, 그 페이지 내용의 근거가 된 청크 별칭을 배열로 적으세요. 예: `"evidence": ["s1", "s3"]`
- 주어진 앵커만 쓰세요. 없는 별칭을 지어내지 마세요.
- `content` 본문에는 앵커를 쓰지 마세요.$prompt$
 where workspace_id is null
   and target_type = 'compile'
   and system_prompt not like '%## 근거 표시%';

commit;
