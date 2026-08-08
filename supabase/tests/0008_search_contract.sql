-- =============================================================================
-- NexusWiki 0008 검증: 검색 함수 계약 (search_chunks 재생성 후)
--
-- 관련 태스크: P2-EMB-01 (소비자는 Phase 4의 5채널 융합)
-- 설계 근거:  03-CONTEXT.md > D-08
--
-- ⚠️ 이 파일은 마이그레이션이 아닙니다. supabase/migrations/ 밖에 있으므로
--    supabase db reset이 적용하지 않으며 마이그레이션 순서에도 들어가지 않습니다.
--    supabase/tests/0007_queue_functions.sql과 같은 자리, 같은 관례입니다.
--
-- 전체가 하나의 트랜잭션이고 마지막이 rollback이므로 픽스처 행은 남지 않습니다.
-- 남기면 raw_sources의 (workspace_id, content_hash) UNIQUE(0001:117)가 다음 실행의
-- 삽입을 막습니다.
--
-- 무엇을 잡는가: `0008`이 search_chunks를 drop 후 재생성했으므로, 재생성이 **성공한
-- 것처럼 보이면서** 계약을 흘린 경우를 잡습니다. definer로 바뀌면 교차 테넌트 검색이
-- 열리고, hnsw GUC가 빠지면 오류 없이 재현율만 떨어지며, ACL을 복원하지 않으면
-- anon이 호출할 수 있게 됩니다 — 셋 다 예외를 내지 않습니다.
--
-- 실행
--   cat supabase/tests/0008_search_contract.sql \
--     | docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1
-- =============================================================================

begin;

-- 픽스처는 고정 UUID를 써서 실패를 재현하기 쉽게 만듭니다.
-- 대역 규약은 0007_queue_functions.sql과 같습니다 (10000000-… 사용자 /
-- 20000000-… 워크스페이스). raw_sources는 40000000-… 대역을 새로 씁니다.
insert into auth.users (id, email)
values ('10000000-0000-0000-0000-000000000021', 'search@example.test');

-- 소유자 멤버십은 workspaces_add_owner_member 트리거가 자동으로 만듭니다.
insert into public.workspaces (id, name, owner_id)
values (
  '20000000-0000-0000-0000-000000000021',
  '검색 계약 테스트',
  '10000000-0000-0000-0000-000000000021'
);

insert into public.raw_sources (
  id, workspace_id, title, source_type, content, content_hash
)
values (
  '40000000-0000-0000-0000-000000000021',
  '20000000-0000-0000-0000-000000000021',
  '검색 계약 픽스처',
  'text',
  '계약 테스트용 원문. 내용 자체는 판정에 쓰이지 않습니다.',
  'search-contract-fixture-hash'
);

-- 임의의 1024차 벡터 30행. 값은 난수가 아니라 n에서 결정론적으로 유도합니다 —
-- 실패했을 때 같은 입력으로 다시 재현할 수 있어야 합니다.
insert into public.source_chunks (
  raw_source_id, workspace_id, chunk_index, content, char_start, char_end, embedding
)
select
  '40000000-0000-0000-0000-000000000021',
  '20000000-0000-0000-0000-000000000021',
  n,
  '계약 테스트 청크 ' || n,
  n * 10,
  n * 10 + 5,
  (
    '['
    || (
      select string_agg(round(((i + n) % 97) / 100.0, 4)::text, ',' order by i)
      from generate_series(1, 1024) as g(i)
    )
    || ']'
  )::extensions.vector(1024)
from generate_series(0, 29) as s(n);


-- -----------------------------------------------------------------------------
-- 계약 1: 오버로드 부재 — public.search_chunks는 정확히 하나다.
--
-- create or replace는 인자 타입이 바뀌면 대체가 아니라 새 오버로드를 만든다.
-- 2개면 0008이 drop을 빠뜨린 것이고, 그 상태에서는 PostgREST가 어느 시그니처를
-- 고를지가 호출마다 달라진다.
-- -----------------------------------------------------------------------------
do $t1$
declare
  v_count int;
begin
  select count(*) into v_count
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
  where n.nspname = 'public' and p.proname = 'search_chunks';

  if v_count <> 1 then
    raise exception 'public.search_chunks가 %개입니다 (기대 1) — drop 누락으로 오버로드가 생겼습니다', v_count;
  end if;
end
$t1$;


-- -----------------------------------------------------------------------------
-- 계약 2·3·4: security invoker · stable · proconfig 4원소
--
-- prosecdef가 true면 본문이 정의자 권한으로 돌아 RLS가 우회되고 교차 테넌트
-- 검색이 열린다. provolatile이 's'가 아니면 플래너 선택이 흔들린다. proconfig의
-- hnsw 3종이 빠지면 오류 없이 검색 재현율만 조용히 떨어진다 (0007:45-52).
-- -----------------------------------------------------------------------------
do $t2$
declare
  v_secdef  boolean;
  v_vol     "char";
  v_config  text[];
begin
  select p.prosecdef, p.provolatile, coalesce(p.proconfig, array[]::text[])
    into v_secdef, v_vol, v_config
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
  where n.nspname = 'public' and p.proname = 'search_chunks';

  if v_secdef then
    raise exception 'search_chunks가 security definer입니다 — RLS가 우회되어 교차 테넌트 검색이 열립니다';
  end if;

  if v_vol <> 's' then
    raise exception 'search_chunks의 provolatile이 %입니다 (기대 s)', v_vol;
  end if;

  if not (v_config @> array[
    'search_path=public',
    'hnsw.iterative_scan=strict_order',
    'hnsw.ef_search=200',
    'hnsw.max_scan_tuples=40000'
  ]) then
    raise exception 'search_chunks의 proconfig에 빠진 항목이 있습니다: %', v_config;
  end if;
end
$t2$;


-- -----------------------------------------------------------------------------
-- 계약 5: 시그니처 차원 — 인자에 vector(1024)가 있고 vector(1536)은 없다.
-- -----------------------------------------------------------------------------
do $t3$
declare
  v_args text;
begin
  select pg_get_function_arguments(p.oid) into v_args
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
  where n.nspname = 'public' and p.proname = 'search_chunks';

  if v_args not like '%vector(1024)%' then
    raise exception 'search_chunks 인자에 vector(1024)가 없습니다: %', v_args;
  end if;
  if v_args like '%vector(1536)%' then
    raise exception 'search_chunks 인자에 vector(1536)가 남아 있습니다: %', v_args;
  end if;
end
$t3$;


-- -----------------------------------------------------------------------------
-- 계약 6: 연산자 수식 — 본문이 operator(extensions.<=>)를 쓴다.
--
-- 수식을 빼면 호출자 search_path에 따라 어느 연산자가 잡힐지가 달라져 결과가
-- 조용히 바뀐다 (0002_search_schema.sql:25-28).
-- -----------------------------------------------------------------------------
do $t4$
declare
  v_src text;
begin
  select p.prosrc into v_src
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
  where n.nspname = 'public' and p.proname = 'search_chunks';

  if v_src not like '%operator(extensions.<=>)%' then
    raise exception 'search_chunks 본문에 operator(extensions.<=>) 수식이 없습니다';
  end if;
end
$t4$;


-- -----------------------------------------------------------------------------
-- 계약 7: ACL — authenticated만 EXECUTE를 갖는다.
--
-- drop function은 0007:386-387이 건 권한을 함께 지운다. 0008이 그 쌍을 복원하지
-- 않으면 Supabase가 새 함수에 주는 기본 실행 권한만 남아 anon이 PostgREST의
-- /rpc/search_chunks 를 부를 수 있게 된다. service_role은 BYPASSRLS라 이 함수의
-- 유일한 격리 수단을 무력화하므로 여기서도 false여야 한다.
-- -----------------------------------------------------------------------------
do $t5$
declare
  v_oid  oid;
  v_auth boolean;
  v_anon boolean;
  v_svc  boolean;
begin
  select p.oid into v_oid
  from pg_proc p
  join pg_namespace n on n.oid = p.pronamespace
  where n.nspname = 'public' and p.proname = 'search_chunks';

  v_auth := has_function_privilege('authenticated', v_oid, 'EXECUTE');
  v_anon := has_function_privilege('anon', v_oid, 'EXECUTE');
  v_svc  := has_function_privilege('service_role', v_oid, 'EXECUTE');

  if not v_auth then
    raise exception 'authenticated가 search_chunks EXECUTE를 갖지 못했습니다 — 0008의 grant 복원이 빠졌습니다';
  end if;
  if v_anon or v_svc then
    raise exception 'search_chunks EXECUTE가 과다 부여됐습니다 (anon=%, service_role=%)', v_anon, v_svc;
  end if;
end
$t5$;


-- -----------------------------------------------------------------------------
-- 계약 8: 컬럼 차원 — 두 embedding 컬럼이 1024차다.
-- -----------------------------------------------------------------------------
do $t6$
declare
  v_chunk text;
  v_wiki  text;
begin
  select format_type(a.atttypid, a.atttypmod) into v_chunk
  from pg_attribute a
  where a.attrelid = 'public.source_chunks'::regclass and a.attname = 'embedding';

  select format_type(a.atttypid, a.atttypmod) into v_wiki
  from pg_attribute a
  where a.attrelid = 'public.wiki_embeddings'::regclass and a.attname = 'embedding';

  if v_chunk not like '%vector(1024)%' then
    raise exception 'source_chunks.embedding 타입이 %입니다 (기대 vector(1024))', v_chunk;
  end if;
  if v_wiki not like '%vector(1024)%' then
    raise exception 'wiki_embeddings.embedding 타입이 %입니다 (기대 vector(1024))', v_wiki;
  end if;
end
$t6$;


-- -----------------------------------------------------------------------------
-- 계약 9: HNSW 인덱스 스캔 — 벡터 최근접 질의가 재생성된 인덱스를 탄다.
--
-- 인덱스가 이름이나 연산자 클래스를 잃으면 질의는 여전히 **성공하고** 순차 스캔으로
-- 떨어진다. 그것은 오류가 아니라 지연으로만 드러나므로 계획을 직접 본다.
-- enable_seqscan을 끄는 것은 인덱스가 존재하고 이 연산자에 쓰일 수 있는지를 묻기
-- 위해서다 — 30행짜리 픽스처에서는 순차 스캔이 언제나 더 싸기 때문이다.
-- -----------------------------------------------------------------------------
do $t7$
declare
  v_vec  text;
  v_plan text;
begin
  select '[' || string_agg(round((i % 89) / 100.0, 4)::text, ',' order by i) || ']'
    into v_vec
  from generate_series(1, 1024) as g(i);

  set local enable_seqscan = off;

  execute format(
    'explain (format json) '
    || 'select c.id from public.source_chunks c '
    || 'where c.workspace_id = %L '
    || 'order by c.embedding operator(extensions.<=>) %L::extensions.vector(1024) '
    || 'limit 20',
    '20000000-0000-0000-0000-000000000021',
    v_vec
  ) into v_plan;

  if v_plan not like '%Index Scan%' or v_plan not like '%source_chunks_embedding_idx%' then
    raise exception 'HNSW 인덱스 스캔이 계획에 없습니다: %', v_plan;
  end if;
end
$t7$;

reset enable_seqscan;

select 'search_contract: ok' as result;
rollback;
