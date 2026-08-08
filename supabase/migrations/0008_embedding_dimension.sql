-- =============================================================================
-- NexusWiki 0008: 임베딩 차원 1024 보정
--
-- 관련 태스크: P2-EMB-01
-- 설계 근거:  checklists.json > decisions.embedding_model  (차원 1024의 출처)
--             03-CONTEXT.md > D-01                          (0008이 담는 범위)
--             03-CONTEXT.md > D-06                          (0002:76 무효 주석 처리)
--             03-CONTEXT.md > D-07                          (단일 트랜잭션)
--             03-CONTEXT.md > D-08                          (재생성 시 옮겨야 하는 계약)
--
-- 0002_search_schema.sql:76의 `text-embedding-3-small(1536차원).` 주석은 이
-- 마이그레이션 이후 사실이 아닙니다. 0002는 로컬과 클라우드 양쪽에 이미 적용되어
-- 소급 수정이 불가하므로 그 자리에는 거짓이 그대로 남습니다. 임베딩 모델과 차원의
-- 유일한 근거는 checklists.json > decisions.embedding_model 입니다.
--
-- 바뀌는 것 (전부 **기존 객체 변경**입니다 — 새 함수·새 테이블은 0009+로 갑니다)
--
--   source_chunks.embedding        vector(1536) ──> vector(1024)
--   wiki_embeddings.embedding      vector(1536) ──> vector(1024)
--   source_chunks_embedding_idx    drop ──> create  (이름·연산자 클래스 동일)
--   wiki_embeddings_embedding_idx  drop ──> create  (이름·연산자 클래스 동일)
--   public.search_chunks           drop ──> create  (p_query가 vector(1024))
--
-- ⚠️ 지금 두 embedding 컬럼의 행이 0개라 alter ... type이 using 절 없이 끝납니다.
--    이 창은 이 페이즈가 첫 임베딩을 만드는 순간 닫힙니다 — 그 뒤에 차원을 건드리면
--    되돌릴 비용이 0에서 전체 재임베딩으로 점프합니다. 0007 섹션 7이
--    tsv_tokenizer_version에 대해 같은 논거로 같은 선택을 했습니다.
--
-- ⚠️ 파일 전체가 begin/commit 하나입니다. 부분 적용이 남기는 상태는 "컬럼은 1024인데
--    인덱스나 함수 시그니처는 1536"이고, 그것은 오류가 아니라 조용한 불일치로
--    나타납니다 — 삽입은 차원 불일치로 거부되고 검색 호출은 사라진 1536 오버로드를
--    계속 찾습니다. 트랜잭션이 그 조합을 구조적으로 만들 수 없게 합니다.
--
-- ⚠️ drop function은 ACL을 함께 지웁니다. 0007:386-387의 revoke/grant 쌍을 이 파일
--    안에서 다시 실행하지 않으면 Supabase가 새 함수에 주는 기본 실행 권한만 남아
--    anon이 PostgREST의 /rpc/search_chunks 를 부를 수 있게 됩니다.
-- =============================================================================

begin;


-- -----------------------------------------------------------------------------
-- 1. pgvector warmup
--
-- ⚠️ 0007:54-58과 같은 이유로 이 한 줄이 먼저 와야 합니다. hnsw.* GUC는 vector.so가
--    백엔드에 적재된 뒤에야 등록되며, 적재 전에는 미지의 placeholder라 섹션 5의
--    함수 정의에 있는 set 절이 "permission denied to set parameter"로 거부됩니다.
--    Supabase의 postgres 롤은 superuser가 아니라 load 'vector'도 쓸 수 없습니다.
--    벡터 표현식을 한 번 평가하면 입력 함수가 라이브러리를 적재합니다.
-- -----------------------------------------------------------------------------
select '[1,2,3]'::extensions.vector as pgvector_warmup;


-- -----------------------------------------------------------------------------
-- 2. search_chunks 제거 후 재생성 — 선언부의 차원은 강제력이 없다
--
-- ⚠️ Postgres는 함수 **인자**의 typmod를 저장하지 않습니다. 선언을
--    `p_query extensions.vector(1024)`로 써도 카탈로그에는 `p_query vector`만
--    남고(pg_get_function_arguments가 그렇게 돌려줍니다), 길이 지정자는 인자에
--    대해 강제되지 않습니다. 0007:386이 revoke 대상을 `extensions.vector`로만
--    수식한 것도 같은 이유입니다 — 그것이 이 함수의 실제 시그니처입니다.
--
--    따라서 (a) 1536과 1024가 서로 다른 오버로드로 공존하는 일은 애초에 없고,
--    (b) 이 파일이 선언부에 쓰는 1024는 **문서이지 계약이 아닙니다**. 차원을
--    실제로 강제하는 것은 섹션 4의 컬럼 타입이며, 그 강제는 호출 시점에만
--    나타납니다. 그래서 supabase/tests/0008_search_contract.sql은 시그니처를
--    읽는 대신 1024차 질의가 통과하고 1536차 질의가 거부되는지를 단언합니다.
--
-- 그래도 replace가 아니라 drop 후 create를 하는 이유는 D-01(4)가 지시한 형태를
-- 지키면서 "이 파일 이후 public.search_chunks는 정확히 하나"를 무조건 참으로
-- 만들기 위해서입니다. 대가는 ACL이며 — drop이 0007:386-387이 건 EXECUTE를 함께
-- 지웁니다 — 섹션 7이 같은 트랜잭션 안에서 복원합니다.
-- -----------------------------------------------------------------------------
drop function public.search_chunks(uuid, extensions.vector, int);


-- -----------------------------------------------------------------------------
-- 3. HNSW 인덱스 제거 — 컬럼 타입 변경보다 먼저 내려야 한다
--
-- 인덱스가 붙은 채로 벡터 컬럼의 차원을 바꾸면 인덱스 재구축이 옛 차원 전제에서
-- 일어납니다. 이름과 연산자 클래스를 그대로 되살리는 것은 섹션 5의 몫입니다.
-- -----------------------------------------------------------------------------
drop index public.source_chunks_embedding_idx;
drop index public.wiki_embeddings_embedding_idx;


-- -----------------------------------------------------------------------------
-- 4. 컬럼 차원 변경 — 1536 → 1024
--
-- 0002의 원본 파일은 수정하지 않습니다. 0002는 이미 로컬과 클라우드 양쪽에
-- 적용되었고 마이그레이션 번호가 곧 적용 순서라는 규약상 소급 편집은 두 원장을
-- 어긋나게 합니다. 정정은 앞으로 나아가는 방식으로만 합니다 (0007:304-306).
--
-- ⚠️ using 절의 캐스트는 행이 있을 때 차원 불일치로 실패합니다. 지금 두 컬럼의
--    행이 0개라 캐스트가 한 번도 평가되지 않고 끝납니다. 이 사실이 이 마이그레이션이
--    Phase 3의 첫 플랜에 있어야 하는 이유 전부입니다 (03-CONTEXT.md > D-02).
-- -----------------------------------------------------------------------------
alter table public.source_chunks
  alter column embedding type extensions.vector(1024)
    using embedding::extensions.vector(1024);

alter table public.wiki_embeddings
  alter column embedding type extensions.vector(1024)
    using embedding::extensions.vector(1024);

comment on column public.source_chunks.embedding is
  '원문 청크의 dense 임베딩. 차원과 모델의 근거는 checklists.json > decisions.embedding_model이며 0002:76의 주석은 무효다.';
comment on column public.wiki_embeddings.embedding is
  '위키 청크의 dense 임베딩. 차원과 모델의 근거는 checklists.json > decisions.embedding_model이며 0002:76의 주석은 무효다.';


-- -----------------------------------------------------------------------------
-- 5. HNSW 인덱스 재생성 — 0002:115 · 0002:152와 같은 이름, 같은 연산자 클래스
--
-- 이름이 달라지면 0002의 주석과 앞으로의 EXPLAIN 단언이 가리키는 대상이 사라지고,
-- 연산자 클래스가 달라지면 <=> 질의가 인덱스를 쓰지 못한 채 조용히 순차 스캔으로
-- 떨어집니다 — 오류가 아니라 지연으로만 드러나는 종류의 회귀입니다.
-- -----------------------------------------------------------------------------
create index source_chunks_embedding_idx
  on public.source_chunks using hnsw (embedding extensions.vector_cosine_ops);

create index wiki_embeddings_embedding_idx
  on public.wiki_embeddings using hnsw (embedding extensions.vector_cosine_ops);


-- -----------------------------------------------------------------------------
-- 6. search_chunks 재생성 — 0007:70-104와 글자 그대로 같고 p_query 타입만 다르다
--
-- 옮겨야 하는 계약은 일곱입니다 (03-CONTEXT.md > D-08). 각각이 빠졌을 때의 실패
-- 양상은 0007:45-62의 주석이 이미 서술했으므로 여기서 되풀이하지 않고, 계약이
-- 살아 있는지는 supabase/tests/0008_search_contract.sql이 pg_proc으로 단언합니다.
--
--   security invoker            definer면 RLS가 우회되어 교차 테넌트 검색이 열린다
--   stable                      빠지면 플래너 선택이 흔들린다
--   set search_path = public    0004의 헬퍼 3종과 같은 규약
--   set hnsw.* 3종              빠져도 오류가 없고 검색 재현율만 조용히 떨어진다
--   operator(extensions.<=>)    수식이 없으면 호출자 search_path에 결과가 좌우된다
--   pgvector warmup             섹션 1
--   ACL 방향                    섹션 7
-- -----------------------------------------------------------------------------
create or replace function public.search_chunks(
  p_workspace_id uuid,
  p_query        extensions.vector(1024),
  p_k            int default 20
)
returns table (
  id            uuid,
  raw_source_id uuid,
  chunk_index   int,
  content       text,
  distance      double precision
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
    c.raw_source_id,
    c.chunk_index,
    c.content,
    (c.embedding operator(extensions.<=>) p_query)::double precision as distance
  from public.source_chunks c
  where c.workspace_id = p_workspace_id
    and c.embedding is not null
  order by c.embedding operator(extensions.<=>) p_query
  limit p_k;
$$;

comment on function public.search_chunks(uuid, extensions.vector, int) is
  '워크스페이스 한정 원문 청크 벡터 최근접 검색. 요청자 JWT(authenticated)로만 호출하며 격리는 RLS가 강제한다. service_role로 부르면 BYPASSRLS라 격리가 사라지므로 EXECUTE를 주지 않는다.';


-- -----------------------------------------------------------------------------
-- 7. ACL 복원 — drop이 지운 0007:386-387을 같은 마이그레이션에서 되돌린다
--
-- ⚠️ 이 두 줄이 없으면 격리가 아니라 공개가 기본값이 됩니다. Supabase는 public
--    스키마의 새 함수에 기본 실행 권한을 주므로, 복원하지 않으면 anon이 PostgREST의
--    /rpc/search_chunks 를 그대로 부를 수 있습니다.
--
-- 검색 함수만 방향이 반대인 이유는 0007:382-385에 있습니다 — security invoker +
-- 요청자 JWT가 이 함수의 격리 수단이므로 authenticated가 부르는 것이 정상 경로이고,
-- BYPASSRLS인 service_role이 부르면 워크스페이스 필터가 애플리케이션 코드 한 줄에만
-- 의존하게 됩니다.
--
-- 0007 섹션 8의 **테이블** revoke/grant 매트릭스는 여기서 재적용하지 않습니다.
-- 이 파일은 테이블을 만들지 않으므로 pg_default_acl의 Dxtm을 새로 물려받는 객체가
-- 없고, 컬럼 타입 변경은 테이블 ACL을 건드리지 않습니다.
-- -----------------------------------------------------------------------------
revoke all on function public.search_chunks(uuid, extensions.vector, int) from public, anon;
grant execute on function public.search_chunks(uuid, extensions.vector, int) to authenticated;

-- PostgREST 스키마 캐시 갱신. 갱신 전에는 재생성된 함수 호출이 PGRST202로 떨어집니다.
notify pgrst, 'reload schema';

commit;
