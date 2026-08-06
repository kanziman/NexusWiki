-- =============================================================================
-- NexusWiki 스파이크 0002: SECURITY INVOKER 검색 함수 2종 (RPC 경로 판정용)
--
-- 관련 태스크: P2-BE-01 (소비자는 scripts/spike_db_transport.py)
-- 설계 근거:  02-CONTEXT.md > D-01 (판정은 EXPLAIN 계획 + 실제 반환 행 수)
--             02-CONTEXT.md > D-03 (GUC 3종 · HNSW Index Scan · k행, 셋 다여야 RPC)
--             02-CONTEXT.md > D-04 (RPC 경로의 RLS 유지 수단은 요청자 JWT + INVOKER)
--
-- ⚠️ 마이그레이션이 아니다. 0007이 채택할 시그니처의 원형이며(02-06-PLAN 섹션 1),
--    여기서 판정에 쓴 EXPLAIN 관측 장치는 Phase 4 RTV-08 회귀 테스트로 이어진다.
--    버리는 프로토타입이 아니다.
--
-- 두 함수의 인자와 GUC modifier 블록은 완전히 동일해야 한다. 하나라도 어긋나면
-- 관측 함수가 검색 함수와 다른 실행 환경을 보게 되어 판정이 그 자체로 무효가 된다.
--
-- 실행
--   cat supabase/spike/0002_search_fn_rpc.sql \
--     | docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 0. pgvector 라이브러리 적재 (GUC 등록 선행)
--
-- ⚠️ hnsw.* GUC는 vector.so 가 백엔드에 적재된 뒤에야 정식 등록된다. 적재 전에는
--    미지의 placeholder 변수라 `create function ... set hnsw.iterative_scan` 이
--    "permission denied to set parameter" 로 거부된다 — Supabase 의 postgres 롤은
--    superuser 가 아니고 `load 'vector'` 도 허용되지 않기 때문이다.
--    벡터 표현식을 한 번 평가하면 입력 함수가 라이브러리를 적재하며 GUC가 등록된다.
-- -----------------------------------------------------------------------------
select '[1,2,3]'::extensions.vector as pgvector_warmup;


-- -----------------------------------------------------------------------------
-- 0b. authenticated 에 SELECT 부여 (스파이크 국소 조치)
--
-- ⚠️ 이 스파이크가 드러낸 사실: 이 데이터베이스에서 anon · authenticated ·
--    service_role 은 public 스키마 9개 테이블에 대해 arwd(SELECT/INSERT/UPDATE/DELETE)
--    를 **하나도 갖고 있지 않다**. pg_default_acl 의
--    `postgres|public|r` 항목이 세 롤에 Dxtm 만 준다.
--
--    RLS 정책은 이미 가진 권한을 좁힐 뿐 없는 권한을 만들어 주지 않는다. 따라서
--    0004의 정책 20여 개는 현재 상태에서 전부 무력하며, 요청자 JWT 경로도
--    service_role 워커 경로도 실제 질의 시 42501 로 떨어진다.
--    (0004 파일 머리말의 "authenticated 는 이미 전권 GRANT 를 가진다"는 전제가
--     현재 Supabase CLI 기본값에서는 성립하지 않는다.)
--
--    여기서는 스파이크를 진행시키기 위한 최소 권한만 국소적으로 부여한다.
--    영구 조치는 마이그레이션 0007 의 몫이며(02-06-PLAN), 그때 9개 테이블 · 3개 롤
--    전체 범위를 정해야 한다. 이 파일의 grant 를 영구 해법으로 오해하지 말 것.
-- -----------------------------------------------------------------------------
grant select on table public.source_chunks to authenticated;


-- -----------------------------------------------------------------------------
-- 1. spike_search_chunks — 실제 검색 경로
--
-- security invoker  — 요청자 JWT의 authenticated 롤로 본문이 실행되어 RLS가 그대로
--                     걸린다. definer 로 두면 RLS가 우회되어 "격리된 상태에서 k행이
--                     채워지는가"라는 질문 자체가 성립하지 않는다 (T-02-02).
-- stable            — 빠뜨리면 호출마다 재평가되는 계약이 되어 플래너 선택이 흔들린다.
-- set search_path   — definer 가 아니어도 고정한다. 함수가 어떤 호출자 아래에서도
--                     같은 테이블을 보게 하려는 것이며 0004의 헬퍼 3종과 같은 규약이다.
-- set hnsw.*        — 이 세 줄이 RPC 경로 판정의 전부다. 함수 정의에 박아 두면 호출자가
--                     잊을 수 없다는 것이 RPC 안의 유일한 구조적 이점이다.
--
-- ⚠️ search_path 에 extensions 가 없으므로 pgvector 연산자를 수식 없이 쓰면 함수 생성이
--    실패하거나(운 좋은 경우) 호출자 search_path 에 따라 조용히 달라진다.
--    operator(extensions.<=>) 로 못 박는다. 근거: 0002_search_schema.sql:25-28.
-- -----------------------------------------------------------------------------
create or replace function public.spike_search_chunks(
  p_workspace_id uuid,
  p_query        extensions.vector(1536),
  p_k            int
)
returns table (
  id          uuid,
  chunk_index int,
  distance    double precision
)
language sql
security invoker
stable
set search_path = public
set hnsw.iterative_scan = 'strict_order'
set hnsw.ef_search = '200'
set hnsw.max_scan_tuples = '40000'
as $$
  select
    c.id,
    c.chunk_index,
    (c.embedding operator(extensions.<=>) p_query)::double precision as distance
  from public.source_chunks c
  where c.workspace_id = p_workspace_id
    and c.embedding is not null
  order by c.embedding operator(extensions.<=>) p_query
  limit p_k;
$$;

comment on function public.spike_search_chunks(uuid, extensions.vector, int) is
  '워크스페이스 한정 벡터 최근접 검색(스파이크). 요청자 JWT로만 호출하며 RLS가 격리를 강제한다.';

grant execute on function public.spike_search_chunks(uuid, extensions.vector, int) to authenticated;


-- -----------------------------------------------------------------------------
-- 2. spike_explain_search_chunks — 판정 3조건을 한 번의 왕복으로 관측
--
-- ⚠️ current_setting() 만 보면 "GUC가 설정되었다"만 알 뿐 "플래너가 실제로 그것을
--    따랐다"는 알 수 없다. 전자만 확인하면 Phase 4에서 조용히 seq scan 으로 이탈해도
--    아무도 알아채지 못한다. 그래서 계획 트리와 실제 반환 행 수를 함께 돌려준다.
--    근거: 02-CONTEXT.md > D-01.
--
-- volatile 인 이유: EXPLAIN 은 유틸리티 문이라 stable 함수의 read-only SPI 컨텍스트에서
-- 실행할 수 없다. 판정에 영향을 주지 않는 modifier 이며, 인자와 GUC 3종은 위 함수와
-- 글자 그대로 같다.
-- -----------------------------------------------------------------------------
create or replace function public.spike_explain_search_chunks(
  p_workspace_id uuid,
  p_query        extensions.vector(1536),
  p_k            int
)
returns jsonb
language plpgsql
security invoker
volatile
set search_path = public
set hnsw.iterative_scan = 'strict_order'
set hnsw.ef_search = '200'
set hnsw.max_scan_tuples = '40000'
as $fn$
declare
  v_plan jsonb;
  v_rows int;
begin
  execute format(
    'explain (analyze, buffers, format json)'
    ' select c.id, c.chunk_index'
    ' from public.source_chunks c'
    ' where c.workspace_id = %L'
    '   and c.embedding is not null'
    ' order by c.embedding operator(extensions.<=>) %L::extensions.vector(1536)'
    ' limit %s',
    p_workspace_id,
    p_query::text,
    p_k
  )
  into v_plan;

  -- 계획이 아니라 같은 조건의 실제 호출에서 행 수를 센다. 사후 필터링 때문에
  -- k 보다 적게 돌아올 수 있고, 바로 그 값이 D-03의 세 번째 조건이다.
  select count(*) into v_rows
  from public.spike_search_chunks(p_workspace_id, p_query, p_k);

  return jsonb_build_object(
    'iterative_scan',  current_setting('hnsw.iterative_scan', true),
    'ef_search',       current_setting('hnsw.ef_search', true),
    'max_scan_tuples', current_setting('hnsw.max_scan_tuples', true),
    'requested_k',     p_k,
    'returned_rows',   v_rows,
    'plan',            v_plan
  );
end
$fn$;

comment on function public.spike_explain_search_chunks(uuid, extensions.vector, int) is
  '검색 함수와 동일한 인자·GUC 아래에서 EXPLAIN 계획·GUC 실측값·실제 반환 행 수를 한 번에 반환한다(스파이크 판정용).';

grant execute on function public.spike_explain_search_chunks(uuid, extensions.vector, int) to authenticated;


-- -----------------------------------------------------------------------------
-- 3. PostgREST 스키마 캐시 갱신
--
-- 갱신하지 않으면 러너가 PGRST202(함수를 찾을 수 없음)를 받는다.
-- -----------------------------------------------------------------------------
notify pgrst, 'reload schema';
