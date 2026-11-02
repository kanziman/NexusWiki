-- =============================================================================
-- NexusWiki 0025: Ask 턴의 trace와 본문 없는 통제 보고서
--
-- 관련 이슈: #163
-- 설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D1, D3
-- 계약:     openspec/changes/ai-control-flow-accounting/specs/ai-request-tracing/spec.md
--
-- 추가 전용입니다. 두 함수는 기본값이 있는 인자만 늘렸으므로 이전 버전 코드의 이름 있는 호출이
-- 그대로 동작합니다.
-- =============================================================================

begin;


-- -----------------------------------------------------------------------------
-- 1. 컬럼
--
-- ⚠️ control_report는 작성자 RLS 아래에 둡니다. 다른 멤버에게 보이는 usage_events에 두면
--    누가 어떤 경로의 질문을 했는지가 드러나 스레드 비공개 계약이 약해집니다.
--
-- ⚠️ 작성자는 자기 행을 직접 UPDATE할 수 있으므로 이 값은 위조될 수 있습니다. 월 상한은 이
--    값을 읽지 않으며, 집계의 결정 분포는 참고 수치로만 표시합니다. 크기 제약은 남용을 막습니다.
-- -----------------------------------------------------------------------------
alter table public.ask_messages
  add column trace_id uuid,
  add column control_report jsonb,
  add constraint ask_messages_control_report_shape check (
    control_report is null
    or (jsonb_typeof(control_report) = 'object' and pg_column_size(control_report) <= 32768)
  );

create index ask_messages_workspace_trace_idx
  on public.ask_messages (workspace_id, trace_id)
  where trace_id is not null;

comment on column public.ask_messages.trace_id is
  '이 턴을 시작한 요청의 trace. 같은 client_turn_id의 재전달은 원래 값을 유지한다.';
comment on column public.ask_messages.control_report is
  '구간 시간, Router 결정, 인용 지표. ⚠️ 질문·프롬프트·답변 본문을 싣지 않는다. 작성자가 수정할 수 있어 권위 있는 값이 아니다.';


-- -----------------------------------------------------------------------------
-- 2. start_ask_turn — 저장된 trace를 돌려준다
--
-- 재전달은 기존 턴을 돌려주므로, API가 돌려받은 값으로 다시 묶어야 사용량과 턴이 같은 trace에
-- 모입니다. 반환 형태가 바뀌어 create or replace를 쓸 수 없고, 권한도 다시 부여합니다.
-- -----------------------------------------------------------------------------
drop function public.start_ask_turn(uuid, uuid, uuid, text);

create function public.start_ask_turn(
  p_workspace_id uuid,
  p_thread_id uuid,
  p_client_turn_id uuid,
  p_question text,
  p_trace_id uuid default null
)
returns table (
  thread_id uuid,
  message_id uuid,
  trace_id uuid
)
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_thread_id uuid;
  v_message_id uuid;
  v_trace_id uuid;
  v_title text;
begin
  -- 같은 client_turn_id의 동시 재전달은 새 스레드를 둘 만들 수 있다. 행이 아직
  -- 없을 때도 직렬화하려면 행 잠금 대신 결정적 advisory 잠금을 잡아야 한다.
  perform pg_advisory_xact_lock(
    hashtextextended(p_workspace_id::text || ':' || p_client_turn_id::text, 0)
  );

  select m.thread_id, m.id, m.trace_id
    into v_thread_id, v_message_id, v_trace_id
    from public.ask_messages m
   where m.workspace_id = p_workspace_id
     and m.client_turn_id = p_client_turn_id;

  if v_message_id is not null then
    thread_id := v_thread_id;
    message_id := v_message_id;
    trace_id := v_trace_id;
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

  insert into public.ask_messages as m (
    thread_id,
    workspace_id,
    client_turn_id,
    question,
    status,
    trace_id
  )
  values (
    v_thread_id,
    p_workspace_id,
    p_client_turn_id,
    p_question,
    'streaming',
    p_trace_id
  )
  returning m.id into v_message_id;

  thread_id := v_thread_id;
  message_id := v_message_id;
  trace_id := p_trace_id;
  return next;
end;
$$;


-- -----------------------------------------------------------------------------
-- 3. finalize_ask_turn — 통제 보고서를 함께 저장한다
-- -----------------------------------------------------------------------------
drop function public.finalize_ask_turn(uuid, uuid, uuid, text, jsonb, text);

create function public.finalize_ask_turn(
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
  if p_status not in ('resolved', 'no-evidence', 'error') then
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

-- ⚠️ 새로 만든 함수에는 기본 권한이 다시 붙습니다. 회수하지 않으면 anon이 실행할 수 있습니다.
revoke all on function public.start_ask_turn(uuid, uuid, uuid, text, uuid) from public, anon, service_role;
grant execute on function public.start_ask_turn(uuid, uuid, uuid, text, uuid) to authenticated;
revoke all on function public.finalize_ask_turn(uuid, uuid, uuid, text, jsonb, text, jsonb) from public, anon, service_role;
grant execute on function public.finalize_ask_turn(uuid, uuid, uuid, text, jsonb, text, jsonb) to authenticated;


notify pgrst, 'reload schema';

commit;
