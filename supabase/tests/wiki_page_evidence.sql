-- #191 페이지 근거 청크의 멱등성과 격리. 마지막에 모두 롤백한다.
begin;

insert into auth.users(id, email) values
  ('10000000-0000-0000-0000-000000000301', 'owner-0030@example.test'),
  ('10000000-0000-0000-0000-000000000302', 'outsider-0030@example.test');

insert into public.workspaces(id, owner_id, name, slug) values
  ('20000000-0000-0000-0000-000000000301', '10000000-0000-0000-0000-000000000301', '근거 A', 'evidence-a-0030'),
  ('20000000-0000-0000-0000-000000000302', '10000000-0000-0000-0000-000000000302', '근거 B', 'evidence-b-0030');

insert into public.raw_sources(id, workspace_id, title, source_type, content, content_hash) values
  ('30000000-0000-0000-0000-000000000301', '20000000-0000-0000-0000-000000000301', '원문1', 'text', '가', 'h-a1'),
  ('30000000-0000-0000-0000-000000000303', '20000000-0000-0000-0000-000000000301', '원문2', 'text', '다', 'h-a2'),
  ('30000000-0000-0000-0000-000000000302', '20000000-0000-0000-0000-000000000302', '원문B', 'text', '나', 'h-b1');

insert into public.source_chunks(id, workspace_id, raw_source_id, chunk_index, content, char_start, char_end) values
  ('40000000-0000-0000-0000-000000000301', '20000000-0000-0000-0000-000000000301', '30000000-0000-0000-0000-000000000301', 0, '가', 0, 1),
  ('40000000-0000-0000-0000-000000000303', '20000000-0000-0000-0000-000000000301', '30000000-0000-0000-0000-000000000303', 0, '다', 0, 1),
  ('40000000-0000-0000-0000-000000000302', '20000000-0000-0000-0000-000000000302', '30000000-0000-0000-0000-000000000302', 0, '나', 0, 1);

insert into public.wiki_pages(id, workspace_id, slug, title, category, content) values
  ('50000000-0000-0000-0000-000000000301', '20000000-0000-0000-0000-000000000301', 'page-0030', '페이지', 'concepts', '본문');

set local role service_role;

do $$
declare
  v integer;
  c constant uuid := '40000000-0000-0000-0000-000000000301';
  w constant uuid := '50000000-0000-0000-0000-000000000301';
  ws constant uuid := '20000000-0000-0000-0000-000000000301';
  r1 constant uuid := '30000000-0000-0000-0000-000000000301';
  r2 constant uuid := '30000000-0000-0000-0000-000000000303';
begin
  perform public.replace_wiki_page_evidence(ws, w, r1, array[c]);
  perform public.replace_wiki_page_evidence(ws, w, r1, array[c]);
  select count(*) into v from public.wiki_page_evidence where wiki_id = w;
  assert v = 1, '재실행해도 행이 늘면 안 된다';

  perform public.replace_wiki_page_evidence(ws, w, r2, array['40000000-0000-0000-0000-000000000303'::uuid]);
  perform public.replace_wiki_page_evidence(ws, w, r1, '{}');
  select count(*) into v from public.wiki_page_evidence where wiki_id = w;
  assert v = 1, '다른 원문의 근거는 지우면 안 된다';
  perform public.replace_wiki_page_evidence(ws, w, r1, array[c]);

  -- 다른 워크스페이스의 청크는 함수가 걸러야 한다.
  select public.replace_wiki_page_evidence(ws, w, r1, array['40000000-0000-0000-0000-000000000302'::uuid]) into v;
  assert v = 0, '다른 워크스페이스 청크를 근거로 넣으면 안 된다';
  perform public.replace_wiki_page_evidence(ws, w, r1, array[c]);
end $$;

reset role;

-- 멤버는 읽고, 비멤버는 0행을 받는다.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"10000000-0000-0000-0000-000000000301","role":"authenticated"}', true);
do $$
declare v integer;
begin
  select count(*) into v from public.wiki_page_evidence;
  assert v = 2, '멤버는 근거를 읽어야 한다';
end $$;

select set_config('request.jwt.claims', '{"sub":"10000000-0000-0000-0000-000000000302","role":"authenticated"}', true);
do $$
declare v integer;
begin
  select count(*) into v from public.wiki_page_evidence;
  assert v = 0, '비멤버는 0행이어야 한다';
end $$;

do $$
begin
  perform public.replace_wiki_page_evidence(gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), '{}');
  raise exception '사용자가 쓰기 RPC를 호출할 수 있으면 안 된다';
exception when insufficient_privilege then
  null;
end $$;

do $$
begin
  insert into public.wiki_page_evidence(wiki_id, chunk_id, workspace_id, raw_source_id)
  values (gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), gen_random_uuid());
  raise exception '사용자가 근거를 쓸 수 있으면 안 된다';
exception when insufficient_privilege then
  null;
end $$;

reset role;
rollback;
