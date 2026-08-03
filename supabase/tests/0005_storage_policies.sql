begin;

-- 테스트 픽스처는 고정 UUID를 사용해 실패를 재현하기 쉽게 만듭니다.
insert into auth.users (id, email)
values
  ('10000000-0000-0000-0000-000000000001', 'editor@example.test'),
  ('10000000-0000-0000-0000-000000000002', 'outsider@example.test');

-- 소유자 멤버십은 workspaces_add_owner_member 트리거가 자동으로 만듭니다.
insert into public.workspaces (id, name, owner_id)
values
  (
    '20000000-0000-0000-0000-000000000001',
    '스토리지 정책 A',
    '10000000-0000-0000-0000-000000000001'
  ),
  (
    '20000000-0000-0000-0000-000000000002',
    '스토리지 정책 B',
    '10000000-0000-0000-0000-000000000002'
  );

set local role authenticated;
select set_config(
  'request.jwt.claims',
  json_build_object('sub', '10000000-0000-0000-0000-000000000001')::text,
  true
);

-- 1. 멤버의 정상 3세그먼트 경로는 성공해야 합니다.
insert into storage.objects (bucket_id, name)
values (
  'sources',
  '20000000-0000-0000-0000-000000000001/30000000-0000-0000-0000-000000000001/report.pdf'
);

-- 2. 멤버 경로여도 2세그먼트이면 42501로 거부되어야 합니다.
do $$
begin
  begin
    insert into storage.objects (bucket_id, name)
    values ('sources', '20000000-0000-0000-0000-000000000001/evil.pdf');
    raise exception '2세그먼트 경로가 허용되었습니다';
  exception
    when insufficient_privilege then null;
  end;
end;
$$;

-- 3. 다른 워크스페이스의 경로도 42501로 거부되어야 합니다.
do $$
begin
  begin
    insert into storage.objects (bucket_id, name)
    values (
      'sources',
      '20000000-0000-0000-0000-000000000002/30000000-0000-0000-0000-000000000001/report.pdf'
    );
    raise exception '비멤버 워크스페이스 경로가 허용되었습니다';
  exception
    when insufficient_privilege then null;
  end;
end;
$$;

-- 4. 잘못된 UUID는 22P02가 아니라 정책의 42501 거부여야 합니다.
do $$
begin
  begin
    insert into storage.objects (bucket_id, name)
    values ('sources', 'not-a-uuid/x/y.pdf');
    raise exception '잘못된 UUID 경로가 허용되었습니다';
  exception
    when invalid_text_representation then
      raise exception '잘못된 UUID가 22P02를 일으켰습니다';
    when insufficient_privilege then null;
  end;
end;
$$;

select 'storage_policies: ok' as result;

rollback;
