-- #198 개정 이력과 제안 테이블의 쓰기 차단. 마지막에 모두 롤백한다.
begin;

insert into auth.users(id, email) values
  ('10000000-0000-0000-0000-000000000331', 'owner-0033@example.test');
insert into public.workspaces(id, owner_id, name, slug) values
  ('20000000-0000-0000-0000-000000000331', '10000000-0000-0000-0000-000000000331', '쓰기 통제', 'write-control-0033');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"10000000-0000-0000-0000-000000000331","role":"authenticated"}', true);

do $$
begin
  insert into public.wiki_page_revisions(workspace_id, wiki_id, job_id, risk_level, reason, previous_title, previous_content)
  values ('20000000-0000-0000-0000-000000000331', gen_random_uuid(), gen_random_uuid(), 'low', 'x', 't', 'c');
  raise exception '사용자가 개정 이력을 쓸 수 있으면 안 된다';
exception when insufficient_privilege then null;
end $$;

do $$
begin
  update public.wiki_write_proposals set status = 'applied';
  raise exception '사용자가 제안 상태를 직접 바꿀 수 있으면 안 된다';
exception when insufficient_privilege then null;
end $$;

do $$
begin
  perform public.upsert_wiki_write_proposal(
    gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), 'r', 't', 'concepts', '[]', 'high', 'c', '{}'
  );
  raise exception '사용자가 제안을 만들 수 있으면 안 된다';
exception when insufficient_privilege then null;
end $$;

reset role;
set local role anon;
do $$
begin
  perform public.decide_wiki_write_proposal(gen_random_uuid(), gen_random_uuid(), 'approved');
  raise exception 'anon이 승인 RPC를 호출할 수 있으면 안 된다';
exception when insufficient_privilege then null;
end $$;

reset role;
rollback;
