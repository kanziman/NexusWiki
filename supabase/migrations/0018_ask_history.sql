-- =============================================================================
-- NexusWiki 0018: Ask 대화 스레드 이력
--
-- 관련: openspec/changes/ask-thread-history/design.md
--       GitHub #76 / #77
-- =============================================================================

-- -----------------------------------------------------------------------------
-- ask_threads: 작성자 소유 대화 세션
-- -----------------------------------------------------------------------------
create table public.ask_threads (
  id           uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  -- 기본값을 auth.uid()로 두면 API가 JWT sub를 파싱하지 않아도 된다.
  -- with check가 user_id = auth.uid()이므로 다른 사용자를 넣을 수 없다.
  user_id      uuid not null default auth.uid() references auth.users (id) on delete cascade,
  title        text not null check (char_length(btrim(title)) between 1 and 100),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  -- ask_messages가 (thread_id, workspace_id) 복합 FK로 테넌트 짝을 강제하려면
  -- 부모에도 같은 유니크가 필요하다. 없으면 다른 워크스페이스 id를 짝지을 수 있다.
  unique (id, workspace_id)
);

create index ask_threads_user_workspace_updated_idx
  on public.ask_threads (user_id, workspace_id, updated_at desc);

create trigger ask_threads_set_updated_at
  before update on public.ask_threads
  for each row execute function public.set_updated_at();

alter table public.ask_threads enable row level security;

-- ⚠️ SELECT에도 멤버십을 건다. 0017 bookmarks는 user_id만 보는데, 스펙은
--    멤버십을 잃은 작성자의 이전 스레드 조회를 금지한다.
create policy ask_threads_select_own
  on public.ask_threads
  for select to authenticated
  using (
    user_id = (select auth.uid())
    and public.is_workspace_member(workspace_id)
  );

create policy ask_threads_insert_own
  on public.ask_threads
  for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and public.is_workspace_member(workspace_id)
  );

create policy ask_threads_update_own
  on public.ask_threads
  for update to authenticated
  using (
    user_id = (select auth.uid())
    and public.is_workspace_member(workspace_id)
  )
  with check (
    user_id = (select auth.uid())
    and public.is_workspace_member(workspace_id)
  );

create policy ask_threads_delete_own
  on public.ask_threads
  for delete to authenticated
  using (
    user_id = (select auth.uid())
    and public.is_workspace_member(workspace_id)
  );

grant select, insert, update, delete on table public.ask_threads to authenticated;

-- -----------------------------------------------------------------------------
-- ask_messages: 논리 턴 한 행 (질문+최종 답)
-- -----------------------------------------------------------------------------
create table public.ask_messages (
  id             uuid primary key default gen_random_uuid(),
  thread_id      uuid not null,
  workspace_id   uuid not null,
  client_turn_id uuid not null,
  question       text not null,
  answer_text    text not null default '',
  citations      jsonb not null default '{"text":"","resolved":[]}'::jsonb,
  status         text not null check (status in ('resolved', 'no-evidence', 'error')),
  created_at     timestamptz not null default now(),
  unique (thread_id, client_turn_id),
  constraint ask_messages_thread_fkey
    foreign key (thread_id, workspace_id)
    references public.ask_threads (id, workspace_id) on delete cascade
);

create index ask_messages_thread_created_idx
  on public.ask_messages (thread_id, created_at);

alter table public.ask_messages enable row level security;

create policy ask_messages_select_own
  on public.ask_messages
  for select to authenticated
  using (
    exists (
      select 1
      from public.ask_threads t
      where t.id = ask_messages.thread_id
        and t.workspace_id = ask_messages.workspace_id
        and t.user_id = (select auth.uid())
        and public.is_workspace_member(t.workspace_id)
    )
  );

create policy ask_messages_insert_own
  on public.ask_messages
  for insert to authenticated
  with check (
    exists (
      select 1
      from public.ask_threads t
      where t.id = ask_messages.thread_id
        and t.workspace_id = ask_messages.workspace_id
        and t.user_id = (select auth.uid())
        and public.is_workspace_member(t.workspace_id)
    )
  );

-- 메시지 행은 갱신·삭제하지 않는다. 스레드 삭제가 cascade로 지운다.
grant select, insert on table public.ask_messages to authenticated;

create or replace function public.touch_ask_thread_on_message()
returns trigger
language plpgsql
as $$
begin
  update public.ask_threads
     set updated_at = now()
   where id = new.thread_id
     and workspace_id = new.workspace_id;
  return new;
end;
$$;

create trigger ask_messages_touch_thread
  after insert on public.ask_messages
  for each row execute function public.touch_ask_thread_on_message();

-- -----------------------------------------------------------------------------
-- persist_ask_turn: citations 직후·done 직전 한 트랜잭션
-- -----------------------------------------------------------------------------
-- security invoker — RLS가 그대로 평가된다. definer로 올리면 격리 정책이 장식이 된다.
create or replace function public.persist_ask_turn(
  p_workspace_id uuid,
  p_thread_id uuid,
  p_client_turn_id uuid,
  p_question text,
  p_answer_text text,
  p_citations jsonb,
  p_status text
)
returns table (
  thread_id uuid,
  message_id uuid
)
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_thread_id uuid;
  v_title text;
  v_message_id uuid;
begin
  if p_status not in ('resolved', 'no-evidence', 'error') then
    raise exception 'invalid ask message status' using errcode = '23514';
  end if;

  v_title := left(btrim(p_question), 80);
  if char_length(v_title) = 0 then
    v_title := '새 대화';
  end if;

  if p_thread_id is null then
    insert into public.ask_threads (workspace_id, title)
    values (p_workspace_id, v_title)
    returning id into v_thread_id;
  else
    select t.id
      into v_thread_id
      from public.ask_threads t
     where t.id = p_thread_id
       and t.workspace_id = p_workspace_id;
    -- ⚠️ 0행은 RLS가 가렸거나 id가 틀린 경우다. 존재를 404로 구분하지 않는다.
    if v_thread_id is null then
      raise exception 'ask thread not visible' using errcode = '42501';
    end if;
  end if;

  insert into public.ask_messages (
    thread_id,
    workspace_id,
    client_turn_id,
    question,
    answer_text,
    citations,
    status
  )
  values (
    v_thread_id,
    p_workspace_id,
    p_client_turn_id,
    p_question,
    coalesce(p_answer_text, ''),
    coalesce(p_citations, '{"text":"","resolved":[]}'::jsonb),
    p_status
  )
  on conflict (thread_id, client_turn_id) do nothing
  returning id into v_message_id;

  if v_message_id is null then
    select m.id
      into v_message_id
      from public.ask_messages m
     where m.thread_id = v_thread_id
       and m.client_turn_id = p_client_turn_id;
  end if;

  return query select v_thread_id, v_message_id;
end;
$$;

comment on function public.persist_ask_turn(uuid, uuid, uuid, text, text, jsonb, text) is
  'Ask 완료 턴을 작성자 소유 스레드에 멱등 저장한다. 호출자는 authenticated + 요청자 JWT. '
  'done 이벤트는 이 함수가 성공한 뒤에만 보낸다.';

revoke all on function public.persist_ask_turn(uuid, uuid, uuid, text, text, jsonb, text) from public;
grant execute on function public.persist_ask_turn(uuid, uuid, uuid, text, text, jsonb, text) to authenticated;
