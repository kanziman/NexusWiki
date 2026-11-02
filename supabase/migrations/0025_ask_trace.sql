-- =============================================================================
-- NexusWiki 0025: Ask 턴의 trace와 본문 없는 통제 보고서
--
-- 관련 이슈: #163
-- 설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D1, D3
-- 계약:     openspec/changes/ai-control-flow-accounting/specs/ai-request-tracing/spec.md
--
-- 컬럼과 트리거를 추가하고 함수 세 개를 고칩니다. start_ask_turn과 finalize_ask_turn은 기본값이 있는
-- 인자만 늘렸고, enqueue_source_job은 시그니처가 같습니다. 이전 버전 코드의 이름 있는 호출은 그대로
-- 동작하며, 작성자의 직접 쓰기는 좁아집니다(UPDATE 컬럼 제한, 이미 쓰인 trace의 INSERT 거부).
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

-- ⚠️ 작성자 UPDATE를 종결에 필요한 컬럼으로 좁힙니다. 테이블 단위로 두면 `trace_id`를 다른 멤버의
--    값으로 바꿔 Control Room 게이트를 통과하고, 재전달로 그 trace의 합계를 부풀릴 수 있습니다.
--    finalize_ask_turn은 security invoker이므로 아래 네 컬럼만 쓰도록 유지해야 합니다.
revoke update on table public.ask_messages from authenticated;
grant update (answer_text, citations, status, control_report)
  on table public.ask_messages to authenticated;

-- ⚠️ 이미 쓰인 trace로 새 턴을 만들 수 없습니다. 멤버는 usage_events에서 다른 멤버의 trace를 읽을 수
--    있으므로, 막지 않으면 그 값으로 자기 턴을 만들어 Control Room 게이트를 통과하고 재전달로 그
--    trace의 표시 합계를 부풀립니다.
--    함수가 아니라 트리거에 두는 이유: start_ask_turn은 security invoker라 authenticated의 INSERT
--    권한을 회수할 수 없고, 작성자는 RPC 없이 ask_messages에 직접 INSERT할 수 있습니다.
--    API는 요청마다 새 값을 발급하고 재전달은 INSERT에 닿지 않으므로 정상 경로를 막지 않습니다.
--    security invoker이므로 요청자에게 보이는 행만 확인해 새로운 존재 탐지 경로가 생기지 않습니다.
--    두 조회 모두 (workspace_id, trace_id) 인덱스를 씁니다.
create function public.ask_messages_reject_used_trace()
returns trigger
language plpgsql
security invoker
set search_path = public
as $fn$
begin
  if new.trace_id is not null and (
    exists (
      select 1 from public.usage_events u
       where u.workspace_id = new.workspace_id and u.trace_id = new.trace_id
    )
    or exists (
      select 1 from public.jobs j
       where j.workspace_id = new.workspace_id and j.trace_id = new.trace_id
    )
  ) then
    raise exception 'trace already in use' using errcode = '42501';
  end if;
  return new;
end
$fn$;

create trigger ask_messages_reject_used_trace
  before insert on public.ask_messages
  for each row execute function public.ask_messages_reject_used_trace();

-- 트리거 실행에는 EXECUTE 권한이 필요하지 않습니다. RPC로 직접 부를 이유가 없어 회수합니다.
revoke all on function public.ask_messages_reject_used_trace() from public, anon, authenticated, service_role;

comment on column public.ask_messages.trace_id is
  '이 턴을 시작한 요청의 trace. 같은 client_turn_id의 재전달은 원래 값을 유지하며, 작성자가 UPDATE할 수 없다.';
comment on column public.ask_messages.control_report is
  '구간 시간, Router 결정, 인용 지표. ⚠️ 질문·프롬프트·답변 본문을 싣지 않는다. 작성자가 수정할 수 있어 권위 있는 값이 아니다.';


-- -----------------------------------------------------------------------------
-- 1-1. enqueue_source_job — Ask 턴의 trace로 잡을 만들지 못하게 한다
--
-- ⚠️ 이 검사를 0023에 두지 않습니다. plpgsql 식은 인자가 null이어도 통째로 계획되어, 위 컬럼이 없는
--    구간에서는 모든 호출이 42703으로 실패합니다. 마이그레이션은 파일마다 따로 커밋되므로 그 구간이
--    실제로 열립니다. 시그니처가 같아 권한과 설명은 유지됩니다.
-- -----------------------------------------------------------------------------
create or replace function public.enqueue_source_job(
  p_workspace_id  uuid,
  p_raw_source_id uuid,
  p_trace_id      uuid default null
)
returns setof public.jobs
language plpgsql
volatile
security definer
set search_path = public
as $fn$
declare
  v_spent bigint;
  v_cap   bigint;
  v_job   public.jobs;
begin
  if not public.has_workspace_role(p_workspace_id, 'editor') then
    raise exception '워크스페이스에 대한 편집 권한이 없습니다'
      using errcode = '42501';
  end if;

  if not exists (
    select 1 from public.raw_sources r
    where r.id = p_raw_source_id
      and r.workspace_id = p_workspace_id
  ) then
    raise exception '워크스페이스에 대한 편집 권한이 없습니다'
      using errcode = '42501';
  end if;

  -- ⚠️ 다른 멤버의 Ask trace로 잡을 만들 수 없습니다. 막지 않으면 Control Room의 수집 분기를 지나
  --    "다른 멤버의 Ask trace는 403"이 무너집니다. Ask 턴의 값만 확인합니다. 영상 배치 등록은 한
  --    요청의 잡들이 같은 trace를 공유하므로, 잡이나 사용량에 있다는 이유로 거부하면 정상 경로가
  --    막힙니다.
  if p_trace_id is not null and exists (
    select 1 from public.ask_messages m
    where m.workspace_id = p_workspace_id
      and m.trace_id = p_trace_id
  ) then
    raise exception '이 요청 식별자는 쓸 수 없습니다'
      using errcode = '42501';
  end if;

  select coalesce(sum(u.cost_micros), 0) into v_spent
  from public.usage_events u
  where u.workspace_id = p_workspace_id
    and u.occurred_at >= (date_trunc('month', now() at time zone 'utc') at time zone 'utc');

  select w.monthly_budget_micros into v_cap
  from public.workspaces w
  where w.id = p_workspace_id;

  if v_spent >= v_cap then
    raise exception '월 비용 상한 초과 (사용 %, 상한 %)', v_spent, v_cap
      using errcode = 'NW402';
  end if;

  insert into public.jobs (workspace_id, type, payload, trace_id)
  values (
    p_workspace_id,
    'parse',
    jsonb_build_object(
      'target_id',     p_raw_source_id::text,
      'raw_source_id', p_raw_source_id::text
    ),
    p_trace_id
  )
  on conflict do nothing
  returning * into v_job;

  -- 중복 인큐는 기존 잡을 그대로 돌려줍니다. 기존 잡의 trace를 덮어쓰지 않습니다.
  if not found then
    select * into v_job
    from public.jobs j
    where j.workspace_id = p_workspace_id
      and j.type = 'parse'
      and j.payload ->> 'target_id' = p_raw_source_id::text
      and j.status in ('queued', 'running', 'failed')
    limit 1;
  end if;

  if v_job.id is null then
    return;
  end if;

  return next v_job;
end
$fn$;


comment on function public.enqueue_source_job(uuid, uuid, uuid) is
  '사용자 경로의 유일한 parse 잡 인큐 통로. editor 이상 멤버십과 raw_source 소유권을 확인하고(위반은 42501), 같은 워크스페이스의 Ask 턴에 쓰인 trace를 거부하며(42501), 이번 달 usage_events 합이 workspaces.monthly_budget_micros 이상이면 NW402으로 거부한다. 같은 대상으로 다시 부르면 새 잡을 만들지 않고 기존 잡을 돌려주며 기존 trace를 바꾸지 않는다. authenticated 전용 — service_role에는 EXECUTE를 주지 않는다.';


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
