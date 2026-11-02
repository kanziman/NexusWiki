-- =============================================================================
-- NexusWiki 0029: Ask 턴의 fallback 종결 상태
--
-- 관련 이슈: #188, #190
-- 설계 근거: openspec/changes/ai-control-output-contract/design.md > D7
-- 계약:     openspec/changes/ai-control-output-contract/specs/grounded-answering/spec.md
--
-- ⚠️ 코드보다 먼저 적용해야 한다. 이 상태를 모르는 DB에 새 코드가 쓰면 finalize가 23514로
--    실패하고 턴이 streaming에 남는다.
-- 이전 코드는 fallback을 쓰지 않으므로 이 마이그레이션만 먼저 나가도 호환된다.
-- =============================================================================

begin;

alter table public.ask_messages
  drop constraint ask_messages_status_check;

-- resolved로 저장하면 품질 지표가 거짓이 되고, error로 저장하면 근거를 보여줄 수 없다.
alter table public.ask_messages
  add constraint ask_messages_status_check
  check (status in ('streaming', 'resolved', 'no-evidence', 'error', 'fallback'));

-- 시그니처가 같으므로 create or replace로 권한을 그대로 유지한다.
create or replace function public.finalize_ask_turn(
  p_workspace_id uuid,
  p_thread_id uuid,
  p_client_turn_id uuid,
  p_answer_text text,
  p_citations jsonb,
  p_status text,
  p_control_report jsonb default null
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
  if p_status not in ('resolved', 'no-evidence', 'error', 'fallback') then
    raise exception 'invalid ask message status' using errcode = '23514';
  end if;

  update public.ask_messages m
     set answer_text = coalesce(p_answer_text, ''),
         citations = coalesce(p_citations, '{"text":"","resolved":[]}'::jsonb),
         status = p_status,
         control_report = p_control_report
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

commit;
