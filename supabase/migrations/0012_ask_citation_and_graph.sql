-- =============================================================================
-- NexusWiki 0012: Ask citation instruction fix, bounded graph read, conflict
--                  candidate read, verification-transition audit trigger
--
-- 관련 태스크: 05-02-PLAN.md (Task 1) — 05-CONTEXT.md > D-10 (ask 템플릿 인용 표기
--   교정), D-07.1/D-11 (그래프 읽기 RPC 경계), D-05 (충돌 후보 RPC), D-06 (검증
--   전이 감사)
--
-- 이 마이그레이션은 스키마 변경 없이(신규 테이블·컬럼 없음) 두 함수와 트리거
-- 하나, 데이터 UPDATE 하나만 더합니다. 0011의 SECURITY INVOKER/STABLE 경계
-- 관례를 그대로 잇습니다.
-- =============================================================================

begin;

-- 0011과 동일한 이유로 pgvector를 먼저 로드합니다: hnsw.* GUC은 이 세션이
-- extensions.vector를 한 번이라도 쓴 뒤에야 SET 가능한 파라미터로 인식됩니다.
-- 로컬 `db reset`은 0011의 함수 정의가 이미 같은 세션에서 이 GUC들을 써서
-- 문제가 드러나지 않지만, `db push`는 이 파일만 담은 새 세션이라 워밍업 없이
-- find_similar_wiki_pages를 정의하면 "permission denied to set parameter"
-- (SQLSTATE 42501)로 실패합니다 — 05-02 Task 2 클라우드 푸시에서 실측.
select '[1,2,3]'::extensions.vector as pgvector_warmup;

-- -----------------------------------------------------------------------------
-- 1. ask 템플릿 인용 표기 교정 (D-10)
--
-- 0006이 심은 네 ask 템플릿은 "위키 근거는 [[wiki:slug]], 원문 근거는
-- [[src:청크id]] 형식 그대로 쓰세요"라고 지시합니다 — 이건 D-02가 확정한
-- 서버 발급 짧은 별칭([[wiki:w1]], [[src:s1]]) 이전의 문구입니다. 네 템플릿이
-- 저마다 다르게 표현하고 있어 문자열 치환(replace)으로는 네 곳을 안전하게
-- 맞힐 수 없습니다 — 대신 시스템 프롬프트 끝에 명확한 지시를 덧붙입니다.
-- 가장 마지막 지시가 모델에게 가장 최근 지시이므로 충돌하는 옛 문구를
-- 실질적으로 무력화합니다.
--
-- 같은 append로 API-03(답변 언어는 질문 언어를 따른다)의 시스템 프롬프트
-- 지시도 함께 넣습니다 — D-08이 "시스템 프롬프트 지시"로 satisfy하기로 한
-- 부분을 앱 코드가 아니라 데이터로 구현합니다.
-- -----------------------------------------------------------------------------
update public.prompt_templates
   set system_prompt = system_prompt || E'\n\n## 인용 형식 (중요)\n\n각 컨텍스트 항목 머리에 표시된 [[wiki:wN]] 또는 [[src:sN]] 형태의 짧은 별칭을 그대로 복사해 인용하세요. 슬러그나 청크 id를 직접 쓰지 마세요 — 표시된 별칭 외의 형식은 인용으로 인정되지 않습니다.\n\n## 답변 언어\n\n질문과 같은 언어로 답변하세요.'
 where target_type = 'ask'
   and workspace_id is null;

comment on table public.prompt_templates is
  'target_type=''ask'' 전역 4종의 system_prompt는 0006 원문 뒤에 0012가 짧은-별칭 인용 지시와 답변-언어 지시를 append했다 (05-CONTEXT.md > D-10). 0006의 [[wiki:slug]]/[[src:청크id]] 문구는 시스템 프롬프트에 여전히 남아있지만, 뒤에 덧붙인 지시가 모델의 가장 최근 지시로서 우선한다.';


-- -----------------------------------------------------------------------------
-- 2. wiki_graph_neighborhood — API-04 그래프 읽기 RPC (D-07.1 / D-11)
--
-- expand_wiki_graph(0011)와 리커시브 CTE 메커닉(깊이 2 고정, lateral fan-out,
-- 사이클 가드)은 그대로 거울처럼 복사하되 독립적으로 버전 관리합니다 —
-- expand_wiki_graph는 Phase 4 검색-융합 정책 소유(seeds가 이미 융합된
-- evidence에서만 옴)이고, 이 함수는 대시보드 "그래프 둘러보기"라는 별개
-- 소비자를 위한 별개 계약입니다. 노드만 반환하는 expand_wiki_graph와 달리
-- 여기서는 (from, to, depth) 엣지 삼중항을 반환합니다 — 그래프 UI가 그릴
-- 엣지가 필요하기 때문입니다.
--
-- 대역폭은 RTV-07의 검색-시간 확장 한계(fanout 1..5, total 1..50)보다 넓게
-- 열어둡니다(fanout 1..20, total 1..200) — D-11의 논거대로 대시보드 조회는
-- 요청당 재검색 비용 배수가 아니라 사용자가 명시적으로 한 번 누르는 단일
-- 행동이기 때문입니다.
-- -----------------------------------------------------------------------------
create or replace function public.wiki_graph_neighborhood(
  p_workspace_id uuid,
  p_seed_wiki_id uuid,
  p_fanout       int default 10,
  p_total_limit  int default 100
)
returns table (from_wiki_id uuid, to_wiki_id uuid, depth int)
language plpgsql
security invoker
stable
set search_path = public
as $$
begin
  if p_fanout < 1 or p_fanout > 20 then
    raise exception 'wiki_graph_neighborhood fan-out must be 1..20' using errcode = '22023';
  end if;
  if p_total_limit < 1 or p_total_limit > 200 then
    raise exception 'wiki_graph_neighborhood total limit must be 1..200' using errcode = '22023';
  end if;

  return query
  with recursive walk as (
    select p_seed_wiki_id as from_wiki_id, first_hop.to_wiki_id, 1 as depth,
           array[p_seed_wiki_id, first_hop.to_wiki_id]::uuid[] as path
      from (
        select l.to_wiki_id from public.wiki_links l
         where l.workspace_id = p_workspace_id
           and l.from_wiki_id = p_seed_wiki_id
           and l.resolved
         order by l.to_wiki_id
         limit p_fanout
      ) first_hop
    union all
    select walk.to_wiki_id, edge.to_wiki_id, walk.depth + 1, walk.path || edge.to_wiki_id
      from walk
      cross join lateral (
        select l.to_wiki_id from public.wiki_links l
         where l.workspace_id = p_workspace_id
           and l.from_wiki_id = walk.to_wiki_id
           and l.resolved and l.to_wiki_id is not null
         order by l.to_wiki_id limit p_fanout
      ) edge
     where walk.depth < 2 and not edge.to_wiki_id = any(walk.path)
  )
  select walk.from_wiki_id, walk.to_wiki_id, walk.depth from walk limit p_total_limit;
end;
$$;

comment on function public.wiki_graph_neighborhood(uuid, uuid, int, int) is
  'API-04 대시보드 그래프 읽기. expand_wiki_graph(0011)의 리커시브-CTE 메커닉을 거울처럼 복사하되 독립 버전 — 검색-융합 정책(POLICY_VERSION/hybrid-rrf-v1)과 무관하다. 노드가 아닌 (from, to, depth) 엣지를 반환해 그래프 UI가 엣지를 그릴 수 있게 한다. SECURITY INVOKER로 RLS가 테넌트 경계를 유지한다 (05-CONTEXT.md > D-07.1/D-11).';

-- search_chunks/expand_wiki_graph와 동일하게 service_role은 명시적으로
-- 제외한다 — 이건 사용자 대상 읽기 경로다.
revoke all on function public.wiki_graph_neighborhood(uuid, uuid, int, int)
  from public, anon, service_role;
grant execute on function public.wiki_graph_neighborhood(uuid, uuid, int, int) to authenticated;


-- -----------------------------------------------------------------------------
-- 3. find_similar_wiki_pages — QC-01 충돌 후보 RPC (D-05)
--
-- search_wiki_embeddings(0011)와 동일한 HNSW GUC 3종을 그대로 복사합니다 —
-- 이 세 GUC은 함수 정의 안의 SET이지 세션 기본값이 아니므로, 새 ad hoc
-- 코사인 질의는 이걸 빼먹으면 조용히 벤치마크되지 않은 pgvector 기본값으로
-- 떨어집니다(05-RESEARCH.md Pitfall 4).
--
-- 이 함수는 한 페이지의 청크 임베딩들을 같은 워크스페이스의 다른 모든
-- 페이지의 청크 임베딩들과 비교합니다(워크스페이스 경계 안, 전체 DB가
-- 아님). 0.88 기본 임계값은 문헌 근거가 아니라 실제 코퍼스로 검증되기
-- 전까지의 출발 가정입니다(05-RESEARCH.md Assumption A3) — 03-03의
-- 청킹 상수처럼 같은 이유로 상수를 노출해 반증 가능하게 둡니다.
--
-- 호출자는 워커의 충돌 감지 잡뿐입니다(사용자 요청 경로 아님) — 그래서
-- EXECUTE는 service_role에게만 주고 authenticated에게는 주지 않습니다.
-- -----------------------------------------------------------------------------
create or replace function public.find_similar_wiki_pages(
  p_workspace_id uuid,
  p_wiki_id uuid,
  p_similarity_threshold double precision default 0.88,
  p_limit int default 5
)
returns table (candidate_wiki_id uuid, similarity double precision)
language sql
security invoker
stable
set search_path = public
set hnsw.iterative_scan = 'strict_order'
set hnsw.ef_search = '200'
set hnsw.max_scan_tuples = '40000'
as $$
  select other.wiki_id,
         max(1 - (mine.embedding operator(extensions.<=>) other.embedding)) as similarity
    from public.wiki_embeddings mine
    join public.wiki_embeddings other
      on other.workspace_id = mine.workspace_id
     and other.wiki_id <> mine.wiki_id
   where mine.workspace_id = p_workspace_id
     and mine.wiki_id = p_wiki_id
     and mine.embedding is not null
     and other.embedding is not null
   group by other.wiki_id
  having max(1 - (mine.embedding operator(extensions.<=>) other.embedding)) >= p_similarity_threshold
   order by similarity desc
   limit least(greatest(p_limit, 1), 20);
$$;

comment on function public.find_similar_wiki_pages(uuid, uuid, double precision, int) is
  'QC-01 충돌 감지 후보 페어 읽기. 워크스페이스 경계 안에서 한 페이지의 청크 임베딩을 다른 모든 페이지의 청크 임베딩과 비교한다(워크스페이스 밖으로는 절대 나가지 않는다). 0.88 기본 임계값은 실제 코퍼스 검증 전 출발 가정이다(05-RESEARCH.md Assumption A3). 워커의 충돌 감지 잡(service_role)만 호출한다 — 사용자 요청 경로에서는 호출되지 않는다 (05-CONTEXT.md > D-05).';

revoke all on function public.find_similar_wiki_pages(uuid, uuid, double precision, int)
  from public, anon, authenticated;
grant execute on function public.find_similar_wiki_pages(uuid, uuid, double precision, int) to service_role;


-- -----------------------------------------------------------------------------
-- 4. stamp_wiki_verification — QC-02 검증 전이 감사 트리거 (D-06)
--
-- verification_status가 실제로 바뀔 때만(new is distinct from old) verified_by
-- verified_at을 auth.uid()/now()로 강제 기록합니다 — 클라이언트가 이 두
-- 컬럼에 어떤 값을 실어 보내도 이 트리거가 무조건 덮어씁니다. "누가·언제"가
-- 요청 바디의 신뢰가 아니라 DB의 보증이 됩니다.
--
-- ⚠️ compile.py의 _upsert_page()는 재컴파일 upsert 페이로드에서
-- verification_status를 의도적으로 뺍니다(T-03-28) — 그래서 그 UPDATE 경로는
-- 이 컬럼을 건드리지 않고, new.verification_status is distinct from
-- old.verification_status는 false로 평가되어 이 트리거는 발동하지 않습니다.
-- 나중에 재컴파일 upsert가 verification_status를 페이로드에 넣도록 바뀌면
-- 이 불변식이 깨지니 그럴 땐 이 주석을 먼저 읽으세요.
-- -----------------------------------------------------------------------------
create or replace function public.stamp_wiki_verification()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  if new.verification_status is distinct from old.verification_status then
    new.verified_by := auth.uid();
    new.verified_at := now();
  end if;
  return new;
end;
$$;

comment on function public.stamp_wiki_verification() is
  'QC-02: verification_status 전이 시 verified_by/verified_at을 auth.uid()/now()로 DB가 강제한다 — 클라이언트 제공 값은 무시된다. compile.py의 재컴파일 upsert는 verification_status를 페이로드에서 빼므로(T-03-28) 이 트리거를 발동시키지 않는다 (05-CONTEXT.md > D-06).';

create trigger wiki_pages_stamp_verification
  before update on public.wiki_pages
  for each row execute function public.stamp_wiki_verification();


notify pgrst, 'reload schema';

commit;
