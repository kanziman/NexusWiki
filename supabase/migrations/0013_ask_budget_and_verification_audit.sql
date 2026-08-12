begin;

-- Ask preflight must aggregate in PostgreSQL: a capped PostgREST row fetch can
-- silently overlook spend once a workspace has more than one page of events.
create or replace function public.sum_usage_events_since(
  p_workspace_id uuid,
  p_since timestamptz
)
returns bigint
language sql
stable
security invoker
set search_path = public
as $$
  select coalesce(sum(u.cost_micros), 0)
  from public.usage_events u
  where u.workspace_id = p_workspace_id
    and u.occurred_at >= p_since;
$$;

revoke all on function public.sum_usage_events_since(uuid, timestamptz)
  from public, anon, authenticated, service_role;
grant execute on function public.sum_usage_events_since(uuid, timestamptz) to service_role;

comment on function public.sum_usage_events_since(uuid, timestamptz) is
  'Ask preflight service-role aggregate. It sums every usage_events row since the caller-supplied UTC boundary; fetching a capped page of rows is unsafe at scale.';

create or replace function public.stamp_wiki_verification()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  if new.verification_status is distinct from old.verification_status then
    if auth.uid() is not null then
      new.verified_by := auth.uid();
      new.verified_at := now();
    else
      new.verified_by := old.verified_by;
      new.verified_at := old.verified_at;
    end if;
  end if;
  return new;
end;
$$;

comment on function public.stamp_wiki_verification() is
  'QC-02: authenticated human verification transitions receive DB-stamped verifier audit fields. Automated service-role dispute transitions preserve OLD.verified_by and OLD.verified_at, keeping the durable human audit record intact.';

notify pgrst, 'reload schema';

commit;
