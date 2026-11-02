-- #172, #177~#180. 설계: reconcile-interrupted-ask-cost/design.md D1~D6.
-- reserved -> in_flight -> unresolved -> settled. 미전송만 released.
begin;

-- ⚠️ 공급자 호출 전에 영속화하지 않으면 프로세스 종료가 무료 호출로 남습니다.
create table public.ask_cost_calls (
  id uuid primary key,
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  trace_id uuid not null,
  created_at timestamptz not null default now(),
  model text not null check (length(model) between 1 and 200),
  policy_version text not null check (length(policy_version) between 1 and 64),
  reserve_micros bigint not null check (reserve_micros > 0),
  status text not null default 'reserved'
    check (status in ('reserved', 'in_flight', 'unresolved', 'settled', 'released')),
  generation_id text check (length(generation_id) between 1 and 200),
  manual_review boolean not null default false,
  generation_conflict boolean not null default false,
  attempts int not null default 0,
  next_attempt_at timestamptz not null default now() + interval '5 minutes',
  lease_id uuid,
  lease_until timestamptz,
  release_reason text check (release_reason = 'not_sent'),
  unique (workspace_id, id)
);
-- 공급자 식별자를 다른 호출에 붙여 이중 정산할 수 없게 합니다.
create unique index ask_cost_calls_generation_idx on public.ask_cost_calls(generation_id)
  where generation_id is not null;
create index ask_cost_calls_workspace_created_idx
  on public.ask_cost_calls(workspace_id, created_at);
create index ask_cost_calls_retry_idx on public.ask_cost_calls(next_attempt_at)
  where status in ('reserved', 'in_flight', 'unresolved') and not manual_review;

-- 정산은 감사 이력입니다. 비용 하향 보정도 원 사용량을 수정하지 않습니다.
create table public.ask_cost_settlements (
  call_id uuid primary key references public.ask_cost_calls(id) on delete cascade,
  cost_micros bigint not null check (cost_micros >= 0),
  source text not null check (source in ('final_usage', 'generation')),
  created_at timestamptz not null default now()
);
alter table public.ask_cost_calls enable row level security;
alter table public.ask_cost_settlements enable row level security;
revoke all on public.ask_cost_calls, public.ask_cost_settlements
  from public, anon, authenticated, service_role;

-- ⚠️ 복합 FK가 없으면 다른 워크스페이스 관측 행을 제외해 비용을 줄일 수 있습니다.
alter table public.usage_events add column ask_call_id uuid;
alter table public.usage_events add constraint usage_events_ask_call_workspace_fk
  foreign key (workspace_id, ask_call_id)
  references public.ask_cost_calls(workspace_id, id);
create unique index usage_events_ask_call_idx on public.usage_events(ask_call_id)
  where ask_call_id is not null;

-- 공통 비용 투영. 원 관측 행과 호출별 유효 비용을 동시에 합산하지 않습니다.
create view public.effective_usage with (security_invoker = true) as
select u.workspace_id, u.trace_id, u.occurred_at, u.cost_micros as reported_micros,
  0::bigint as pending_micros, u.cost_micros as budget_micros,
  u.metadata ->> 'call' = 'ask' as is_ask
from public.usage_events u where u.ask_call_id is null
union all
select c.workspace_id, c.trace_id, c.created_at,
  coalesce(s.cost_micros, u.cost_micros, 0),
  case when c.status in ('settled', 'released') then 0
    else greatest(c.reserve_micros - coalesce(u.cost_micros, 0), 0) end,
  case when c.status = 'released' then 0
    when s.call_id is not null then s.cost_micros
    else greatest(c.reserve_micros, coalesce(u.cost_micros, 0)) end,
  true
from public.ask_cost_calls c
left join public.ask_cost_settlements s on s.call_id = c.id
left join public.usage_events u on u.ask_call_id = c.id;
revoke all on public.effective_usage from public, anon, authenticated, service_role;

create or replace function public.sum_usage_events_since(p_workspace_id uuid, p_since timestamptz)
returns bigint language sql stable security definer set search_path = public as $$
  select coalesce(sum(e.budget_micros), 0)::bigint from public.effective_usage e
  where e.workspace_id = p_workspace_id and e.occurred_at >= p_since;
$$;
revoke all on function public.sum_usage_events_since(uuid, timestamptz)
  from public, anon, authenticated;
grant execute on function public.sum_usage_events_since(uuid, timestamptz) to service_role;
comment on function public.sum_usage_events_since(uuid, timestamptz) is
  '워커 전용 공통 예산 집계. 원 관측액과 예약 또는 확정액을 중복 합산하지 않는다.';

create function public.reserve_ask_cost(p_workspace_id uuid, p_call_id uuid, p_trace_id uuid,
  p_model text, p_policy_version text, p_reserve_micros bigint)
returns setof public.ask_cost_calls language plpgsql security definer set search_path = public as $$
declare v_cap bigint; v public.ask_cost_calls;
begin
  select monthly_budget_micros into v_cap from public.workspaces
    where id = p_workspace_id for update;
  if not found then raise exception 'workspace unavailable' using errcode = '42501'; end if;
  select * into v from public.ask_cost_calls where id = p_call_id;
  if found then
    if v.workspace_id <> p_workspace_id or v.trace_id <> p_trace_id
       or v.model <> p_model or v.policy_version <> p_policy_version
       or v.reserve_micros <> p_reserve_micros then
      raise exception 'call mismatch' using errcode = '42501';
    end if;
    return next v; return;
  end if;
  if p_reserve_micros <= 0 then raise exception 'invalid reservation'; end if;
  if public.sum_usage_events_since(p_workspace_id, date_trunc('month', now(), 'UTC'))
      + p_reserve_micros > v_cap then
    raise exception 'budget exceeded' using errcode = 'NW402';
  end if;
  insert into public.ask_cost_calls(id, workspace_id, trace_id, model, policy_version, reserve_micros)
    values(p_call_id, p_workspace_id, p_trace_id, p_model, p_policy_version, p_reserve_micros)
    returning * into v;
  return next v;
end $$;

-- 전이를 한 곳에서 검사해 오래된 임대 응답이 새 상태를 바꾸지 못하게 합니다.
create function public.update_ask_cost(p_workspace_id uuid, p_call_id uuid, p_action text,
  p_generation_id text default null, p_cost_micros bigint default null,
  p_source text default 'final_usage', p_lease_id uuid default null)
returns boolean language plpgsql security definer set search_path = public as $$
declare c public.ask_cost_calls;
begin
  -- 예약과 같은 잠금 순서로 집계와 정산을 직렬화합니다.
  perform 1 from public.workspaces where id = p_workspace_id for update;
  select * into c from public.ask_cost_calls
    where id = p_call_id and workspace_id = p_workspace_id for update;
  if not found then raise exception 'call unavailable' using errcode = '42501'; end if;
  if p_lease_id is not null and (c.lease_id is distinct from p_lease_id
      or c.lease_until <= now()) then return false; end if;
  if c.status in ('settled', 'released') then return false; end if;
  if p_action = 'start' then
    if c.status <> 'reserved' then return false; end if;
    update public.ask_cost_calls set status = 'in_flight' where id = c.id;
  elsif p_action = 'generation' then
    if c.generation_id is not null and c.generation_id <> p_generation_id then
      update public.ask_cost_calls set generation_conflict = true, manual_review = true,
        status = 'unresolved' where id = c.id;
    else
      begin
        update public.ask_cost_calls set generation_id = p_generation_id where id = c.id;
      exception when unique_violation then
        update public.ask_cost_calls set generation_conflict = true, manual_review = true,
          status = 'unresolved' where id = c.id;
      end;
    end if;
  elsif p_action = 'release' then
    if c.status <> 'reserved' then return false; end if;
    update public.ask_cost_calls set status = 'released', release_reason = 'not_sent' where id = c.id;
  elsif p_action = 'settle' then
    if c.status = 'reserved' or c.generation_conflict then return false; end if;
    if p_source = 'generation' and (p_lease_id is null or c.generation_id is null) then
      return false;
    end if;
    insert into public.ask_cost_settlements(call_id, cost_micros, source)
      values(c.id, p_cost_micros, p_source);
    update public.ask_cost_calls set status = 'settled', lease_id = null, lease_until = null
      where id = c.id;
  elsif p_action = 'retry' then
    update public.ask_cost_calls set status = 'unresolved', attempts = attempts + 1,
      manual_review = manual_review or generation_id is null or attempts + 1 >= 8,
      next_attempt_at = now() + make_interval(secs => least(3600, 30 * power(2, least(attempts, 7)))::int),
      lease_id = null, lease_until = null where id = c.id;
  elsif p_action = 'unresolved' then
    update public.ask_cost_calls set status = 'unresolved' where id = c.id;
  else raise exception 'unknown action';
  end if;
  return true;
end $$;

create function public.claim_ask_costs(p_limit int default 10)
returns setof public.ask_cost_calls language sql security definer set search_path = public as $$
  update public.ask_cost_calls c set lease_id = gen_random_uuid(),
    lease_until = now() + interval '180 seconds', status = 'unresolved'
  where c.id in (
    select a.id from public.ask_cost_calls a
    where a.status in ('reserved', 'in_flight', 'unresolved') and not a.manual_review
      and a.next_attempt_at <= now() and (a.lease_until is null or a.lease_until < now())
    order by a.next_attempt_at limit least(greatest(p_limit, 1), 5) for update skip locked
  ) returning c.*;
$$;

-- RLS를 우회하는 함수 안에서도 화면과 같은 접근 권한을 검사합니다.
create function public.ask_cost_snapshot(p_workspace_id uuid, p_since timestamptz,
  p_trace_id uuid default null, p_ask_only boolean default false)
returns table(reported_micros bigint, pending_micros bigint, budget_micros bigint,
  unresolved_count bigint, manual_review_count bigint, over_reserve_count bigint)
language plpgsql stable security definer set search_path = public as $$
declare
  v_since timestamptz := case when p_trace_id is null then date_trunc('day', p_since, 'UTC')
    else p_since end;
begin
  if not public.has_workspace_role(p_workspace_id, 'viewer') then
    raise exception 'forbidden' using errcode = '42501';
  end if;
  if p_trace_id is not null then
    if not exists (select 1 from public.ask_messages m
      join public.ask_threads t on t.id = m.thread_id
      where m.workspace_id = p_workspace_id and m.trace_id = p_trace_id
        and t.user_id = auth.uid()) then
      raise exception 'forbidden' using errcode = '42501';
    end if;
  elsif p_ask_only and not public.has_workspace_role(p_workspace_id, 'editor') then
    raise exception 'forbidden' using errcode = '42501';
  end if;
  return query select
    coalesce(sum(e.reported_micros), 0)::bigint,
    coalesce(sum(e.pending_micros), 0)::bigint,
    coalesce(sum(e.budget_micros), 0)::bigint,
    (select count(*) from public.ask_cost_calls c where c.workspace_id = p_workspace_id
      and c.created_at >= v_since and (p_trace_id is null or c.trace_id = p_trace_id)
      and (p_trace_id is not null or public.has_workspace_role(p_workspace_id, 'editor'))
      and c.status in ('reserved', 'in_flight', 'unresolved')),
    (select count(*) from public.ask_cost_calls c where c.workspace_id = p_workspace_id
      and c.created_at >= v_since and (p_trace_id is null or c.trace_id = p_trace_id)
      and (p_trace_id is not null or public.has_workspace_role(p_workspace_id, 'editor'))
      and c.manual_review and c.status = 'unresolved'),
    (select count(*) from public.ask_cost_calls c join public.ask_cost_settlements s on s.call_id = c.id
      where c.workspace_id = p_workspace_id and c.created_at >= v_since
      and (p_trace_id is not null or public.has_workspace_role(p_workspace_id, 'editor'))
      and (p_trace_id is null or c.trace_id = p_trace_id) and s.cost_micros > c.reserve_micros)
  from public.effective_usage e where e.workspace_id = p_workspace_id
    and e.occurred_at >= v_since and (p_trace_id is null or e.trace_id = p_trace_id)
    and (not p_ask_only or e.is_ask);
end $$;

-- 호출별 투영도 작성자 게이트를 함수 안에서 검사합니다. generation ID는 반환하지 않습니다.
create function public.ask_cost_trace_calls(p_workspace_id uuid, p_trace_id uuid)
returns table(ask_call_id uuid, model text, cost_micros bigint, observed_cost_micros bigint,
  pending_micros bigint, budget_micros bigint, accounting_status text,
  prompt_tokens int, completion_tokens int, total_tokens int, duration_ms int,
  occurred_at timestamptz)
language plpgsql stable security definer set search_path = public as $$
begin
  if p_trace_id is null then raise exception 'forbidden' using errcode = '42501'; end if;
  perform public.ask_cost_snapshot(p_workspace_id, '1970-01-01', p_trace_id);
  return query select c.id, c.model, coalesce(s.cost_micros, u.cost_micros, 0),
    coalesce(u.cost_micros, 0),
    case when c.status in ('settled', 'released') then 0::bigint
      else greatest(c.reserve_micros - coalesce(u.cost_micros, 0), 0) end,
    case when c.status = 'released' then 0::bigint when s.call_id is not null then s.cost_micros
      else greatest(c.reserve_micros, coalesce(u.cost_micros, 0)) end,
    case when c.manual_review and c.status = 'unresolved' then 'manual_review' else c.status end,
    u.prompt_tokens, u.completion_tokens, u.total_tokens, u.duration_ms, c.created_at
    from public.ask_cost_calls c
    left join public.usage_events u on u.ask_call_id = c.id
    left join public.ask_cost_settlements s on s.call_id = c.id
    where c.workspace_id = p_workspace_id and c.trace_id = p_trace_id and c.status <> 'released'
    order by c.created_at;
end $$;
revoke all on function public.ask_cost_trace_calls(uuid, uuid) from public, anon, service_role;
grant execute on function public.ask_cost_trace_calls(uuid, uuid) to authenticated;
comment on function public.ask_cost_trace_calls(uuid, uuid) is
  '현재 멤버인 Ask 작성자 전용 호출별 관측액·정산액·점유액 투영. 공급자 ID는 노출하지 않는다.';

revoke all on function public.reserve_ask_cost(uuid, uuid, uuid, text, text, bigint)
  from public, anon, authenticated;
revoke all on function public.update_ask_cost(uuid, uuid, text, text, bigint, text, uuid)
  from public, anon, authenticated;
revoke all on function public.claim_ask_costs(int) from public, anon, authenticated;
grant execute on function public.reserve_ask_cost(uuid, uuid, uuid, text, text, bigint),
  public.update_ask_cost(uuid, uuid, text, text, bigint, text, uuid), public.claim_ask_costs(int)
  to service_role;
revoke all on function public.ask_cost_snapshot(uuid, timestamptz, uuid, boolean)
  from public, anon, service_role;
grant execute on function public.ask_cost_snapshot(uuid, timestamptz, uuid, boolean) to authenticated;
comment on function public.reserve_ask_cost(uuid, uuid, uuid, text, text, bigint) is
  '워커 전용 원자적 Ask 예약. 워크스페이스 잠금으로 동시 초과 승인을 막는다.';
comment on function public.update_ask_cost(uuid, uuid, text, text, bigint, text, uuid) is
  '워커 전용 전송·ID·정산·재시도 전이. 기존 usage는 수정하지 않는다.';
comment on function public.claim_ask_costs(int) is '워커 전용 만료 호출 임대. 최대 5건, 임대 180초.';
comment on function public.ask_cost_snapshot(uuid, timestamptz, uuid, boolean) is
  '요청자 JWT 비용 투영. trace는 현재 멤버인 작성자, Ask 집계는 editor만 조회한다.';

-- 기존 인큐도 미확정 Ask의 예산 점유를 반영합니다.
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

  select public.sum_usage_events_since(p_workspace_id,
    date_trunc('month', now(), 'UTC')) into v_spent;

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

-- 기존 집계 RPC를 직접 호출해도 정산 후 공급자 비용이 일치해야 합니다.
create or replace function public.ask_trace_aggregate(
  p_workspace_id uuid,
  p_since        timestamptz
)
returns table (
  turn_count           bigint,
  resolved_count       bigint,
  no_evidence_count    bigint,
  error_count          bigint,
  decision_counts      jsonb,
  p50_total_ms         int,
  p95_total_ms         int,
  total_cost_micros    bigint,
  incomplete_call_count bigint
)
language plpgsql
stable
security definer
set search_path = public
as $fn$
declare
  -- ⚠️ UTC 일 단위로 내립니다. 경계를 조금씩 옮기며 차이를 보면 개별 턴의 시각, 상태, 결정, 지연을
  --    분리할 수 있어 "작성자를 드러내지 않는 집계"가 무너집니다. 멤버가 적을수록 위험합니다.
  v_since constant timestamptz := date_trunc('day', p_since, 'UTC');
begin
  -- ⚠️ 이 검사가 빠지면 BYPASSRLS처럼 동작해 비멤버가 다른 테넌트의 집계를 읽습니다.
  if not public.has_workspace_role(p_workspace_id, 'editor') then
    raise exception '워크스페이스에 대한 편집 권한이 없습니다'
      using errcode = '42501';
  end if;

  return query
  with turns as (
    select m.status, m.control_report
    from public.ask_messages m
    where m.workspace_id = p_workspace_id
      and m.created_at >= v_since
      and m.status <> 'streaming'
  ),
  durations as (
    -- ⚠️ control_report는 작성자가 수정할 수 있습니다. 타입을 확인하지 않고 캐스팅하면 한 사람이
    --    넣은 문자열 때문에, 범위를 확인하지 않으면 `1e20` 같은 수가 아래 `::int`에서 22003을 내어
    --    워크스페이스 전체의 집계가 실패합니다. 하루를 넘는 턴은 없으므로 그 밖의 값은 버립니다.
    --    `case`로 나누는 이유는 where 조건의 평가 순서가 보장되지 않아 문자열이 먼저 캐스팅될 수
    --    있기 때문입니다.
    select v.total_ms
    from (
      select case
        when jsonb_typeof(t.control_report -> 'total_ms') = 'number'
          then (t.control_report ->> 'total_ms')::numeric
      end as total_ms
      from turns t
    ) v
    where v.total_ms between 0 and 86400000
  ),
  decisions as (
    -- 알려진 값만 셉니다. 임의의 문자열이 집계 키로 다른 멤버에게 전달되면 안 됩니다.
    select t.control_report -> 'route' ->> 'decision' as decision, count(*) as n
    from turns t
    where t.control_report -> 'route' ->> 'decision'
      in ('NO_EVIDENCE', 'LOOKUP', 'SINGLE_KIND', 'STANDARD')
    group by 1
  ),
  usage as (
    select
      (select coalesce(sum(e.reported_micros), 0)::bigint
       from public.effective_usage e where e.workspace_id = p_workspace_id
         and e.occurred_at >= v_since and e.is_ask) as total_cost_micros,
      count(*) filter (where u.metadata ->> 'incomplete' = 'true') as incomplete_call_count
    from public.usage_events u
    where u.workspace_id = p_workspace_id
      and u.occurred_at >= v_since
      and u.metadata ->> 'call' = 'ask'
  )
  select
    (select count(*) from turns),
    (select count(*) from turns t where t.status = 'resolved'),
    (select count(*) from turns t where t.status = 'no-evidence'),
    (select count(*) from turns t where t.status = 'error'),
    (select coalesce(jsonb_object_agg(d.decision, d.n), '{}'::jsonb) from decisions d),
    (select percentile_cont(0.5) within group (order by d.total_ms)::int from durations d),
    (select percentile_cont(0.95) within group (order by d.total_ms)::int from durations d),
    usage.total_cost_micros,
    usage.incomplete_call_count
  from usage;
end
$fn$;

notify pgrst, 'reload schema';
commit;
