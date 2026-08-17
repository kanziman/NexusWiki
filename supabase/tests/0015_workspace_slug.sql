-- 워크스페이스 슬러그 정본 계약
begin;

insert into auth.users (id, email)
values ('10000000-0000-0000-0000-000000000151', 'workspace-slug@example.test');

insert into public.workspaces (id, name, slug, owner_id)
values (
  '20000000-0000-0000-0000-000000000151',
  '슬러그 계약',
  'slug-contract',
  '10000000-0000-0000-0000-000000000151'
);

do $workspace_slug$
begin
  begin
    insert into public.workspaces (id, name, slug, owner_id)
    values ('20000000-0000-0000-0000-000000000152', '중복 슬러그', 'slug-contract', '10000000-0000-0000-0000-000000000151');
    raise exception '중복 workspace slug가 허용되었습니다';
  exception when unique_violation then null;
  end;

  begin
    insert into public.workspaces (id, name, slug, owner_id)
    values ('20000000-0000-0000-0000-000000000153', '잘못된 슬러그', 'bad/slug', '10000000-0000-0000-0000-000000000151');
    raise exception '경로 구분자를 가진 workspace slug가 허용되었습니다';
  exception when check_violation then null;
  end;

  begin
    insert into public.workspaces (id, name, owner_id)
    values ('20000000-0000-0000-0000-000000000154', '누락된 슬러그', '10000000-0000-0000-0000-000000000151');
    raise exception 'slug 없는 workspace가 허용되었습니다';
  exception when not_null_violation then null;
  end;
end
$workspace_slug$;

rollback;
