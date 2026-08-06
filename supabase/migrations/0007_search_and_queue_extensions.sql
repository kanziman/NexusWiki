-- =============================================================================
-- NexusWiki 0007: 검색 함수 · 큐 확장 · 최소권한 매트릭스
--
-- 관련 태스크: P2-BE-01(섹션 1) · P2-JOB-01(섹션 2·3·4) · P2-QC-01(섹션 5)
--             P2-EMB-01(섹션 6) · P2-ING-02(섹션 7) · P4-SEC-01(섹션 8)
-- 설계 근거:  checklists.json > decisions.db_transport   (섹션 1)
--             02-CONTEXT.md > D-21                       (섹션 1~6의 구성 순서)
--             02-CONTEXT.md > D-18                       (섹션 4)
--             02-CONTEXT.md > D-19                       (섹션 7)
--             checklists.json > open_questions           (섹션 7·8이 닫는 두 항목)
--
-- 상태 전이 (0003의 그림에 release 화살표가 하나 추가됩니다)
--
--   queued ──claim──> running ──complete──> succeeded
--     ^  ^               │
--     │  │               ├──fail (attempts < max)──> failed ──run_after 경과──┐
--     │  │               └──fail (attempts >= max)──> dead                    │
--     │  └───────────────── reap (락 타임아웃, attempts 유지) ──────────────────┘
--     └──────────────────── release (attempts −1, 자발적 반납) ────────────────┘
--
-- release는 reap과 다릅니다. reap은 죽은 워커에게서 락을 뺏는 것이라 소진된
-- 시도를 그대로 두지만, release는 살아 있는 워커가 SIGTERM을 받고 스스로
-- 내려놓는 것이라 시도 하나를 되돌립니다. 되돌리지 않으면 재배포 세 번에
-- 정상 잡이 dead로 떨어집니다 (02-CONTEXT.md > D-18).
--
-- ⚠️ 이 파일은 저장소에서 처음으로 자기 자신을 begin/commit으로 감쌉니다.
--    0001~0006 중 어느 것도 그러지 않았습니다. 02-SPEC.md R7이 "부분 적용 불가"를
--    수용기준으로 요구하므로 여덟 섹션은 전부 적용되거나 전부 되돌아가야 합니다.
--    특히 섹션 7(컬럼 타입 변경)만 적용되고 섹션 8(권한)이 빠지면, 스키마는
--    새 값을 받을 수 있게 되었는데 그 값을 쓸 롤이 여전히 42501을 받는
--    상태가 남습니다 — 원인을 되짚기 가장 어려운 조합입니다.
-- =============================================================================

begin;


-- -----------------------------------------------------------------------------
-- 1. 검색 함수 — source_chunks 벡터 최근접 (5채널 중 채널 2)
--
-- 트랜스포트가 rpc로 잠겼으므로(checklists.json > decisions.db_transport) 검색
-- 쿼리는 애플리케이션이 아니라 이 마이그레이션이 소유합니다. supabase/spike/
-- 0002_search_fn_rpc.sql의 spike_search_chunks를 프로덕션 이름으로 승격한
-- 것이며, 인자·modifier·연산자 수식은 실측으로 판정된 형태 그대로입니다.
--
-- security invoker  — 요청자 JWT의 authenticated 롤로 본문이 실행되어 RLS가 그대로
--                     걸립니다. ⚠️ definer로 바꾸면 RLS가 우회되어 교차 테넌트
--                     검색이 열립니다. 이 함수에서 definer는 오타가 아니라 사고입니다.
-- stable            — 빠뜨리면 호출마다 재평가되는 계약이 되어 플래너 선택이 흔들립니다.
-- set search_path   — definer가 아니어도 고정합니다. 0004의 헬퍼 3종과 같은 규약입니다.
-- set hnsw.*        — 호출자가 잊을 수 없다는 것이 RPC 경로의 유일한 구조적 이점입니다.
--                     벡터 검색은 사후 필터링이라 k보다 적게 돌아올 수 있고,
--                     strict_order가 없으면 그 손실이 조용히 커집니다 (RTV-03).
--
-- ⚠️ 아래 warmup 한 줄을 지우지 마세요. hnsw.* GUC는 vector.so가 백엔드에 적재된
--    뒤에야 등록되며, 적재 전에는 미지의 placeholder라 함수 정의의 set 절이
--    "permission denied to set parameter"로 거부됩니다. Supabase의 postgres 롤은
--    superuser가 아니라 load 'vector'도 쓸 수 없습니다. 벡터 표현식을 한 번
--    평가하면 입력 함수가 라이브러리를 적재합니다.
--
-- ⚠️ search_path에 extensions가 없으므로 pgvector 연산자를 수식 없이 쓰면 호출자
--    search_path에 따라 결과가 조용히 달라집니다. operator(extensions.<=>)로
--    못 박습니다. 근거: 0002_search_schema.sql:25-28.
--
-- 나머지 4개 채널의 함수는 여기서 만들지 않습니다. 융합 가중치와 k가 정해지는
-- 곳이 Phase 4이고(RTV-06 골든 질의 세트), 그 전에 시그니처를 고정하면 0008,
-- 0009로 계속 되돌아오게 됩니다.
-- -----------------------------------------------------------------------------
select '[1,2,3]'::extensions.vector as pgvector_warmup;

create or replace function public.search_chunks(
  p_workspace_id uuid,
  p_query        extensions.vector(1536),
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
-- 2. jobs_dedup_idx — 같은 대상에 대한 중복 인큐 차단
--
-- 인큐 경로(P2-ING-01)는 사용자 요청마다 불립니다. 같은 원본에 대해 두 번
-- 누르면 같은 일을 두 번 하는 잡이 두 개 생기고, LLM 비용이 그대로 두 배가
-- 됩니다. 큐 함수들은 이미 있는 행을 다룰 뿐이라 이 중복을 막지 못합니다.
--
-- 식별 키는 payload ->> 'target_id' 입니다. 잡 종류마다 대상이 다르므로
-- (수집은 raw_source_id, 컴파일은 wiki_id) 컬럼을 늘리는 대신 인큐 측이
-- 대상 식별자를 이 한 키에 싣는 것을 계약으로 둡니다.
--
-- 부분 인덱스인 이유: 조건을 대기·진행 중인 잡(queued/running/failed)으로
-- 좁히지 않으면 한 번 succeeded가 된 잡이 같은 대상의 재처리를 영구히
-- 막습니다. 원본이 갱신되면 다시 컴파일할 수 있어야 합니다.
--
-- ⚠️ target_id가 없는 잡은 중복이 막히지 않습니다. 유니크 인덱스에서 NULL은
--    서로 다른 값으로 취급되기 때문입니다. 이것은 의도된 탈출구가 아니라
--    생산자가 지켜야 할 계약입니다 — 새 잡 종류를 추가할 때 payload에
--    target_id를 넣지 않으면 이 인덱스는 조용히 아무 일도 하지 않습니다.
-- ⚠️ 중복 인큐는 예외(23505)로 돌아옵니다. 생산자는 on conflict do nothing으로
--    받아 "이미 큐에 있음"을 정상 흐름으로 처리하세요.
-- -----------------------------------------------------------------------------
create unique index jobs_dedup_idx
  on public.jobs (workspace_id, type, (payload ->> 'target_id'))
  where status in ('queued', 'running', 'failed');


-- -----------------------------------------------------------------------------
-- 3. complete_job_and_chain — 완료와 다음 잡 인큐를 한 트랜잭션에
--
-- COMP-04가 컴파일을 parse → compile → link_sync → embed로 쪼갭니다. 단계
-- 사이를 complete_job() 다음에 별도 insert로 이으면 그 틈에서 워커가 죽었을 때
-- 앞 단계는 succeeded인데 다음 단계가 없는 상태로 파이프라인이 조용히 멈춥니다.
--
-- where 절의 status = 'running'은 0003의 complete_job에서 그대로 가져온 것이며
-- 반드시 유지해야 합니다. 이 절이 이미 succeeded인 잡에 대한 재호출을 예외가
-- 아니라 0행 no-op으로 만듭니다. 잡은 at-least-once라 재호출이 정상 경로이고,
-- 0행이 아니라면 재호출마다 다음 잡이 하나씩 더 생겨 큐가 증식합니다.
--
-- locked_at/locked_by를 함께 비웁니다 — 그러지 않으면 jobs_lock_consistency
-- CHECK(0003:65-68)가 행을 거부합니다.
--
-- 다음 잡 삽입에 on conflict do nothing을 거는 이유는 섹션 2의 jobs_dedup_idx
-- 입니다. 같은 대상의 다음 잡이 이미 큐에 있으면 조용히 넘어가는 것이 맞고,
-- 여기서 23505로 죽으면 방금 성공한 앞 단계까지 롤백됩니다.
-- -----------------------------------------------------------------------------
create or replace function public.complete_job_and_chain(
  p_job_id       uuid,
  p_next_type    text  default null,
  p_next_payload jsonb default '{}'::jsonb
)
returns setof public.jobs
language plpgsql
volatile
set search_path = public
as $fn$
declare
  v_job public.jobs;
begin
  update public.jobs j
  set status     = 'succeeded',
      last_error = null,
      locked_at  = null,
      locked_by  = null
  where j.id = p_job_id and j.status = 'running'
  returning j.* into v_job;

  -- 0행이면 다음 잡을 인큐하지 않고 그대로 빠져나갑니다.
  if not found then
    return;
  end if;

  if p_next_type is not null then
    insert into public.jobs (workspace_id, type, payload)
    values (v_job.workspace_id, p_next_type, coalesce(p_next_payload, '{}'::jsonb))
    on conflict do nothing;
  end if;

  return next v_job;
end
$fn$;

comment on function public.complete_job_and_chain(uuid, text, jsonb) is
  '잡을 succeeded로 전이시키고 같은 트랜잭션에서 다음 잡을 인큐한다. 이미 succeeded면 0행 no-op이며 다음 잡도 생기지 않는다. service_role 전용.';


-- -----------------------------------------------------------------------------
-- 4. release_job — SIGTERM 시 자발적 반납 (02-CONTEXT.md > D-18)
--
-- attempts는 claim 시점에 증가합니다(0003:44-47). 그래서 배포로 인한 자발적
-- 종료를 그냥 반납으로 처리하면 잘못한 것이 없는 잡이 재배포마다 시도를
-- 하나씩 소진합니다.
--
-- ⚠️ fail_job을 대신 쓰면 재배포 세 번(max_attempts 기본 3)에 정상 잡이 dead로
--    떨어집니다. 그것이 이 함수가 따로 존재하는 유일한 이유입니다.
--
-- ⚠️ locked_by = p_worker_id 술어가 "다른 워커의 진행을 덮어쓰지 않는다"를 참으로
--    만드는 유일한 장치입니다. 이 술어를 빼면 종료 중인 워커 A가 살아 있는
--    워커 B의 잡을 큐로 되돌려 같은 잡이 두 번 처리됩니다. 이 계약은
--    supabase/tests/0007_queue_functions.sql이 SQL 수준에서 고정합니다.
--
-- attempts − 1을 greatest()로 감싸지 않은 것은 의도입니다. running 잡은 claim을
-- 거쳤으므로 attempts >= 1이고, 그렇지 않은 행이 여기 오면 그것 자체가 버그이니
-- attempts >= 0 CHECK(0003:47)가 소란스럽게 막는 편이 낫습니다.
-- -----------------------------------------------------------------------------
create or replace function public.release_job(
  p_job_id    uuid,
  p_worker_id text
)
returns setof public.jobs
language sql
volatile
set search_path = public
as $$
  update public.jobs j
  set status    = 'queued',
      attempts  = j.attempts - 1,
      locked_at = null,
      locked_by = null
  where j.id = p_job_id
    and j.status = 'running'
    and j.locked_by = p_worker_id
  returning j.*;
$$;

comment on function public.release_job(uuid, text) is
  '락 소유자 본인이 잡을 큐로 반납하고 claim에서 소진한 attempts를 1 되돌린다. locked_by가 다르거나 running이 아니면 0행 no-op이다. service_role 전용.';


-- -----------------------------------------------------------------------------
-- 5. 검증 메타 (DOM-03)
--
-- 0001의 verification_status는 상태만 있고 주인과 시각이 없습니다. 누가 언제
-- 검증했는지 없는 배지는 감사할 수도 철회할 수도 없어 아무도 신뢰하지 않습니다.
-- expires_at은 "검증은 시간이 지나면 낡는다"를 표현합니다 — 만료된 검증을
-- 검증으로 세면 오래된 위키가 영원히 verified로 남습니다.
--
-- verified_by는 created_by(0001:131)와 같은 on delete set null 규약을 따릅니다.
--
-- CHECK를 걸지 않은 이유: verification_status = 'verified'일 때 verified_by가
-- not null이어야 한다는 CHECK를 걸면, 계정 삭제가 발동시키는 set null이 곧바로
-- 그 CHECK를 위반해 auth.users 행 삭제가 23514로 실패합니다. 계정 삭제는
-- Supabase가 관리하는 경로라 막으면 안 됩니다. 대신 세 컬럼을 한 UPDATE로 함께
-- 쓰는 것을 P2-QC-01의 PATCH /api/wiki/{id}/verify가 책임집니다.
-- -----------------------------------------------------------------------------
alter table public.wiki_pages
  add column verified_by uuid references auth.users (id) on delete set null,
  add column verified_at timestamptz,
  add column expires_at  timestamptz;

comment on column public.wiki_pages.verified_by is
  '이 페이지를 verified로 전이시킨 사용자. 계정 삭제 시 null이 되며 그때 배지는 주인 없는 상태로 남는다(P2-QC-01이 처리).';
comment on column public.wiki_pages.expires_at is
  '검증의 유효 기한. 지나면 verification_status를 그대로 신뢰하지 않는다.';


-- -----------------------------------------------------------------------------
-- 6. 버전 컬럼 (DOM-04)
--
-- 0002는 어휘 검색에만 tsv_tokenizer_version을 뒀습니다. 그래서 임베딩 모델을
-- 바꾸거나 청킹 파라미터를 조정하면 재처리 대상을 골라낼 방법이 없어 워크스페이스
-- 전체를 다시 돌려야 합니다 — 임베딩은 종량 과금이라 그 비용이 곧바로 돈입니다.
--
-- 타입이 text인 이유: 임베딩 모델 이름은 애초에 문자열이고
-- ('text-embedding-3-small'), 청커 버전도 알고리즘과 파라미터를 인코딩한
-- 문자열입니다. 바로 다음 섹션이 tsv_tokenizer_version도 text로 맞추므로
-- 세 버전 컬럼의 타입이 일치합니다.
-- -----------------------------------------------------------------------------
alter table public.source_chunks
  add column embedding_version text,
  add column chunker_version   text;

alter table public.wiki_embeddings
  add column embedding_version text;

comment on column public.source_chunks.embedding_version is
  '이 행의 embedding을 만든 모델 식별자. 모델 교체 시 재임베딩 대상을 이 값으로 좁힌다.';
comment on column public.source_chunks.chunker_version is
  '이 행을 자른 청커의 알고리즘·파라미터 식별자. 청킹 규칙이 바뀌면 이 값으로 재청킹 대상을 좁힌다.';


-- -----------------------------------------------------------------------------
-- 7. 토크나이저 버전 컬럼 타입 정정 — smallint → text (D-21 이탈)
--
-- packages/core/src/nexuswiki_core/tokenizer.py의 TSV_TOKENIZER_VERSION은
-- 'bigram-nfkc-cf-v1'이라는 문자열입니다. SPEC R8과 02-CONTEXT.md > D-19가
-- 알고리즘·정규화 형식·casefold 여부·버전을 한 문자열에 인코딩하라고 요구했기
-- 때문입니다. 그런데 두 컬럼은 smallint(0002_search_schema.sql:94, :220)라
-- 그 값을 담을 수 없습니다.
--
-- ⚠️ 이 섹션은 02-CONTEXT.md > D-21이 열거한 여섯 섹션에 없는 의도적 추가입니다.
--    D-21은 `### Claude's Discretion` 블록 안에 있고 그 블록은 뒤집기를 허용하되
--    이유를 남기라고 요구합니다. 뒤집는 이유는 창의 시점입니다 — 두 테이블의
--    행이 지금 0개라 alter ... type text가 using 절 없는 한 줄로 끝납니다.
--    미루면 0008 하나와, 첫 색인 INSERT에서 막히는 P2-ING-02가 비용으로
--    남습니다. 관련 항목: checklists.json > open_questions.
--
-- ⚠️ 0002의 원본 파일은 수정하지 않습니다. 0002는 이미 로컬과 클라우드 양쪽에
--    적용되었고, 마이그레이션 번호가 곧 적용 순서라는 규약상 소급 편집은 두
--    원장을 어긋나게 합니다. 정정은 앞으로 나아가는 방식으로만 합니다.
-- -----------------------------------------------------------------------------
alter table public.source_chunks
  alter column tsv_tokenizer_version type text;

alter table public.wiki_pages
  alter column tsv_tokenizer_version type text;

comment on column public.source_chunks.tsv_tokenizer_version is
  '이 행의 search_tsv를 만든 토크나이저 식별자. nexuswiki_core.tokenizer.TSV_TOKENIZER_VERSION과 글자 그대로 같아야 하며, 어긋나면 검색이 오류 없이 조용히 빈다.';


-- -----------------------------------------------------------------------------
-- 8. 권한 — 최소권한 역할 × 테이블 × 동작 매트릭스와 새 함수 EXECUTE
--
-- ⚠️ 0004_rls_policies.sql:12-13의 "anon/authenticated는 public 스키마 테이블에
--    이미 전권 GRANT를 가진다"는 머리말 전제는 현재 Supabase CLI 기본값에서
--    사실이 아닙니다. pg_default_acl의 postgres|public|r 항목은 세 롤에
--    Dxtm(TRUNCATE/REFERENCES/TRIGGER/MAINTAIN)만 부여하며 arwd는 하나도
--    주지 않습니다. RLS는 이미 가진 권한을 좁힐 뿐 없는 권한을 만들지 않으므로,
--    이 섹션 이전까지 0004의 정책 20여 개는 전부 무력했고 요청자 JWT 경로도
--    service_role 워커 경로도 실제 질의에서 42501로 떨어졌습니다.
--    (P2-BE-01 스파이크 실측. 0004는 이미 적용된 파일이라 소급 수정하지 않고
--     여기서 앞으로 나아가는 방식으로 정정합니다.)
--
-- ⚠️ 반대로 Dxtm 중 TRUNCATE는 RLS를 우회합니다. 로그인 사용자가 truncate 경로를
--    하나라도 얻으면 워크스페이스 전체가 아니라 테이블 전체가 사라집니다.
--    아래 revoke가 그것까지 함께 걷어냅니다.
--
-- 부여 원칙(checklists.json > open_questions, 사용자 결정):
--   anon           — 아무것도 주지 않습니다. 로그인 없는 요청은 계속 전면 거부입니다.
--   authenticated  — 0004가 정책을 건 테이블·동작만. RLS가 그 위에서 다시 좁힙니다.
--                    raw_sources에 update가 없는 것은 원본 불변성 때문이고,
--                    파생 3종(source_chunks/wiki_embeddings/wiki_links)과 jobs가
--                    select뿐인 것은 사용자 쓰기 경로가 설계상 없기 때문입니다.
--   service_role   — 워커가 실제로 쓰는 테이블·동작만. BYPASSRLS이므로 여기서
--                    넓히면 실수 한 줄이 곧바로 교차 테넌트 쓰기가 됩니다.
--                    jobs에 update가 필요한 것은 큐 함수 5종이 SECURITY INVOKER라
--                    호출자 권한으로 UPDATE를 수행하기 때문입니다.
--   포괄적 grant all은 어느 롤에도 쓰지 않습니다.
--
-- ⚠️ 이 매트릭스는 지금 존재하는 9개 테이블에만 걸립니다. 앞으로 만들 테이블은
--    pg_default_acl에서 다시 Dxtm을 물려받으므로, 테이블을 추가하는 마이그레이션은
--    자기 테이블에 대해 이 revoke/grant 쌍을 반드시 반복해야 합니다.
-- -----------------------------------------------------------------------------
revoke all on all tables in schema public from anon, authenticated, service_role;

grant select, insert, update, delete on table public.workspaces        to authenticated;
grant select, insert, update, delete on table public.workspace_members to authenticated;
grant select, insert, delete         on table public.raw_sources       to authenticated;
grant select, insert, update, delete on table public.wiki_pages        to authenticated;
grant select                         on table public.source_chunks     to authenticated;
grant select                         on table public.wiki_embeddings   to authenticated;
grant select                         on table public.wiki_links        to authenticated;
grant select, insert, update, delete on table public.prompt_templates  to authenticated;
grant select                         on table public.jobs              to authenticated;

grant select                         on table public.workspaces        to service_role;
grant select                         on table public.workspace_members to service_role;
grant select, insert, update         on table public.raw_sources       to service_role;
grant select, insert, update, delete on table public.wiki_pages        to service_role;
grant select, insert, update, delete on table public.source_chunks     to service_role;
grant select, insert, update, delete on table public.wiki_embeddings   to service_role;
grant select, insert, update, delete on table public.wiki_links        to service_role;
grant select                         on table public.prompt_templates  to service_role;
grant select, insert, update         on table public.jobs              to service_role;

-- 새 함수의 EXECUTE. Supabase는 public 스키마 새 함수에 기본 실행 권한을 주므로,
-- 놔두면 PostgREST의 /rpc/ 로 아무나 남의 잡을 집어가거나 완료 처리할 수 있습니다.
-- 0003:213-229의 revoke/grant 쌍을 그대로 반복합니다.
revoke all on function public.complete_job_and_chain(uuid, text, jsonb) from public, anon, authenticated;
revoke all on function public.release_job(uuid, text)                   from public, anon, authenticated;

grant execute on function public.complete_job_and_chain(uuid, text, jsonb) to service_role;
grant execute on function public.release_job(uuid, text)                   to service_role;

-- 검색 함수만 방향이 반대입니다. security invoker + 요청자 JWT가 이 함수의 격리
-- 수단이므로 authenticated가 부르는 것이 정상 경로이고, BYPASSRLS인 service_role이
-- 부르면 워크스페이스 필터가 애플리케이션 코드 한 줄에만 의존하게 됩니다.
-- 그래서 service_role에는 주지 않습니다.
revoke all on function public.search_chunks(uuid, extensions.vector, int) from public, anon;
grant execute on function public.search_chunks(uuid, extensions.vector, int) to authenticated;

-- PostgREST 스키마 캐시 갱신. 갱신 전에는 새 함수 호출이 PGRST202로 떨어집니다.
notify pgrst, 'reload schema';

commit;
