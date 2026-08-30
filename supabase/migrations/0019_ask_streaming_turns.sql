-- =============================================================================
-- NexusWiki 0019: Ask 진행 중 턴과 라우트 복귀
-- =============================================================================

alter table public.ask_messages
  drop constraint ask_messages_status_check;

alter table public.ask_messages
  add constraint ask_messages_status_check
  check (status in ('streaming', 'resolved', 'no-evidence', 'error'));

-- 같은 클라이언트 턴의 최초 생성 요청이 재전달되어도 새 스레드를 만들지 않는다.
alter table public.ask_messages
  add constraint ask_messages_workspace_turn_key unique (workspace_id, client_turn_id);

-- 진행 중 메시지는 완료 경로에서만 갱신한다. 정책이 없으면 security invoker RPC도
-- RLS에 막혀 최종 답변을 저장하지 못한다.
create policy ask_messages_update_own
  on public.ask_messages
  for update to authenticated
  using (
    exists (
      select 1
      from public.ask_threads t
      where t.id = ask_messages.thread_id
        and t.workspace_id = ask_messages.workspace_id
        and t.user_id = (select auth.uid())
        and public.is_workspace_member(t.workspace_id)
    )
  )
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

grant update on table public.ask_messages to authenticated;

create or replace function public.start_ask_turn(
  p_workspace_id uuid,
  p_thread_id uuid,
  p_client_turn_id uuid,
  p_question text
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
  v_message_id uuid;
  v_title text;
begin
  -- 같은 client_turn_id의 동시 재전달은 새 스레드를 둘 만들 수 있다. 행이 아직
  -- 없을 때도 직렬화하려면 행 잠금 대신 결정적 advisory 잠금을 잡아야 한다.
  perform pg_advisory_xact_lock(
    hashtextextended(p_workspace_id::text || ':' || p_client_turn_id::text, 0)
  );

  select m.thread_id, m.id
    into v_thread_id, v_message_id
    from public.ask_messages m
   where m.workspace_id = p_workspace_id
     and m.client_turn_id = p_client_turn_id;

  if v_message_id is not null then
    thread_id := v_thread_id;
    message_id := v_message_id;
    return next;
    return;
  end if;

  if p_thread_id is null then
    v_title := left(btrim(p_question), 80);
    if char_length(v_title) = 0 then
      v_title := '새 대화';
    end if;
    insert into public.ask_threads (workspace_id, title)
    values (p_workspace_id, v_title)
    returning id into v_thread_id;
  else
    select t.id
      into v_thread_id
      from public.ask_threads t
     where t.id = p_thread_id
       and t.workspace_id = p_workspace_id;
    if v_thread_id is null then
      raise exception 'ask thread not visible' using errcode = '42501';
    end if;
  end if;

  insert into public.ask_messages (
    thread_id,
    workspace_id,
    client_turn_id,
    question,
    status
  )
  values (
    v_thread_id,
    p_workspace_id,
    p_client_turn_id,
    p_question,
    'streaming'
  )
  returning id into v_message_id;

  thread_id := v_thread_id;
  message_id := v_message_id;
  return next;
end;
$$;

create or replace function public.finalize_ask_turn(
  p_workspace_id uuid,
  p_thread_id uuid,
  p_client_turn_id uuid,
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
  v_message_id uuid;
begin
  if p_status not in ('resolved', 'no-evidence', 'error') then
    raise exception 'invalid ask message status' using errcode = '23514';
  end if;

  update public.ask_messages m
     set answer_text = coalesce(p_answer_text, ''),
         citations = coalesce(p_citations, '{"text":"","resolved":[]}'::jsonb),
         status = p_status
   where m.thread_id = p_thread_id
     and m.workspace_id = p_workspace_id
     and m.client_turn_id = p_client_turn_id
     and m.status = 'streaming'
  returning m.id into v_message_id;

  if v_message_id is null then
    select m.id
      into v_message_id
      from public.ask_messages m
     where m.thread_id = p_thread_id
       and m.workspace_id = p_workspace_id
       and m.client_turn_id = p_client_turn_id
       and m.status = p_status;
    if v_message_id is null then
      raise exception 'ask turn not visible or not streaming' using errcode = '42501';
    end if;
  end if;

  update public.ask_threads
     set updated_at = now()
   where id = p_thread_id
     and workspace_id = p_workspace_id;

  thread_id := p_thread_id;
  message_id := v_message_id;
  return next;
end;
$$;

revoke all on function public.start_ask_turn(uuid, uuid, uuid, text) from public;
grant execute on function public.start_ask_turn(uuid, uuid, uuid, text) to authenticated;
revoke all on function public.finalize_ask_turn(uuid, uuid, uuid, text, jsonb, text) from public;
grant execute on function public.finalize_ask_turn(uuid, uuid, uuid, text, jsonb, text) to authenticated;
