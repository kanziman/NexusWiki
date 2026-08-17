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
insert into public.workspaces (id, name, slug, owner_id)
values (
  '20000000-0000-0000-0000-000000000021',
  '검색 계약 테스트',
  'search-contract',
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
-- 계약 5: 질의 차원 — 1024차 질의는 통과하고 1536차 질의는 거부된다.
--
-- ⚠️ 이 계약을 시그니처로 물을 수는 없다. Postgres는 함수 **인자**의 typmod를
--    저장하지 않으므로 `0008`이 선언한 extensions.vector(1024)는 카탈로그에
--    `p_query vector`로만 남는다 (pg_get_function_arguments로 확인 가능).
--    0007:386이 revoke 대상을 `extensions.vector`로만 수식한 것도 같은 이유이며,
--    그것이 이 함수의 실제 시그니처다.
--
--    차원을 실제로 강제하는 것은 컬럼 타입(계약 8)이고 그 강제는 호출 시점에만
--    나타난다. 그래서 여기서는 카탈로그가 아니라 **행동**을 단언한다 — 이것이
--    "질의 벡터가 1024차여야 한다"에 대해 관측 가능한 유일한 형태다.
-- -----------------------------------------------------------------------------
do $t3$
declare
  v_rows     int;
  v_1024     text;
  v_1536     text;
  v_rejected boolean := false;
begin
  select '[' || string_agg('0.01', ',') || ']' into v_1024 from generate_series(1, 1024);
  select '[' || string_agg('0.01', ',') || ']' into v_1536 from generate_series(1, 1536);

  execute format(
    'select count(*) from public.search_chunks(%L, %L::extensions.vector, 5)',
    '20000000-0000-0000-0000-000000000021',
    v_1024
  ) into v_rows;

  if v_rows <> 5 then
    raise exception '1024차 질의가 %행을 돌려줬습니다 (기대 5)', v_rows;
  end if;

  begin
    execute format(
      'select count(*) from public.search_chunks(%L, %L::extensions.vector, 5)',
      '20000000-0000-0000-0000-000000000021',
      v_1536
    ) into v_rows;
  exception
    when others then
      v_rejected := true;
  end;

  if not v_rejected then
    raise exception '1536차 질의가 거부되지 않았습니다 — 컬럼의 차원 강제가 사라졌습니다';
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
--
-- ⚠️ 이 단언은 **의도**이고, 지금 클라우드는 그 의도를 만족하지 않는다. 이 러너는
--    로컬 스택에서만 돌기 때문에 여기서는 green이다. 클라우드의 pg_default_acl에는
--    postgres 소유 public 함수에 anon·authenticated·service_role EXECUTE를 주는
--    항목이 있고 로컬에는 없다. 그래서 0008의 `revoke ... from public, anon`이
--    클라우드에서 service_role의 기본 부여를 걷어내지 못했다 (실측:
--    docs/ops/migration-0008-record.md § 한계와 되돌리기). 0007이 만든 상태를
--    0008이 그대로 재현한 것이며, 정정은 0009의 revoke 한 줄이 맡는다.
--    ⚠️ 그때까지 "로컬에서 green이므로 클라우드도 그렇다"고 읽지 말 것.
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
-- 인덱스가 이름이나 연산자 클래스를 잃으면 질의는 여전히 **성공하고** 순차 스캔이나
-- 정렬로 떨어진다. 그것은 오류가 아니라 지연으로만 드러나므로 계획을 직접 본다.
--
-- ⚠️ enable_seqscan과 enable_sort를 끄는 것은 "이 계획이 운영에서 나온다"를 묻는
--    것이 아니라 **"인덱스가 이 컬럼·이 연산자에 쓰일 수 있는가"**를 묻기 위해서다.
--    30행짜리 픽스처에서는 workspace_id btree(0002:108) + Sort가 언제나 더 싸므로,
--    두 GUC 없이는 인덱스가 멀쩡해도 계획에 나타나지 않는다. 이 단언이 답하는
--    질문은 재생성된 source_chunks_embedding_idx가 이름과 연산자 클래스를
--    유지했는가이며, 융합 질의의 실제 계획 판정은 Phase 4(RTV-04)의 일이다.
-- -----------------------------------------------------------------------------
do $t7$
declare
  v_vec     text;
  v_plan    text;
  v_indexes text;
begin
  select '[' || string_agg(round((i % 89) / 100.0, 4)::text, ',' order by i) || ']'
    into v_vec
  from generate_series(1, 1024) as g(i);

  set local enable_seqscan = off;
  set local enable_sort = off;

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
    -- 계획 전문에는 1024차 질의 벡터가 그대로 들어 있어 그대로 인쇄하면 실패
    -- 메시지를 읽을 수 없다. 판정에 필요한 것은 어떤 인덱스가 쓰였는가뿐이다.
    select array_to_string(
      array(select m[1] from regexp_matches(v_plan, '"Index Name": "([^"]+)"', 'g') as m),
      ', '
    ) into v_indexes;

    raise exception
      'HNSW 인덱스 스캔이 계획에 없습니다 (사용된 인덱스: %) — source_chunks_embedding_idx가 이름이나 연산자 클래스를 잃었는지 확인할 것',
      coalesce(nullif(v_indexes, ''), '없음');
  end if;
end
$t7$;

reset enable_seqscan;
reset enable_sort;

select 'search_contract: ok' as result;
rollback;
