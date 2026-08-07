# Phase 3: Ingest and Compile Pipeline - Context

**Gathered:** 2026-08-07
**Status:** Ready for planning

<domain>
## Phase Boundary

투입한 소스(파일 · URL · 텍스트)가 워커 잡 체인 `parse → compile → link_sync → embed`을 거쳐 **링크되고 임베딩된 위키 페이지**가 되며, 그 과정이 비용 상한 안에서 사용자에게 단계 이름으로 보인다.

요구사항 16건: ING-01~07(수집 · 즉시 202 · content_hash 중복 표시 · Storage 보존 · 추출 품질 게이트 · 청킹 · 진행 표면 · dead 재시도), COMP-01~08(OpenRouter 컴파일 · enum↔CHECK 대조 · 오류 되먹임 재시도 · 잡 분할 · WikiLink 동기화 · 양방향 임베딩 · 축소 재처리 · provider 예외 마스킹), OPS-01(`usage_events` · 인큐 시점 비용 상한 · 입력 크기 상한 · 잡 취소).

**이 페이즈가 하지 않는 것:** 5채널 융합·가중치·골든 세트(Phase 4), 답변 생성과 이중 Citation(Phase 5), 프론트엔드 표면(Phase 6), E2E·격리 전수 스위트(Phase 7). Phase 3은 **쓰기 경로**만 완성한다.

**논의 범위 주의:** 이번 discuss는 사용자가 `0008 마이그레이션 경계` 한 영역만 선택했다. 나머지 세 영역(컴파일 산출 단위 / 비용 상한·취소 / 수집 게이트·청킹)은 **의도적으로 researcher와 planner 재량으로 남겨졌다** — 결정이 없어서가 아니라 위임된 것이다. 아래 `<deferred>`의 "이 페이즈 안에서 열려 있는 것"을 참조할 것.

</domain>

<decisions>
## Implementation Decisions

### `0008` 마이그레이션 경계

- **D-01 (`0008`에는 되돌릴 수 없는 것만 넣는다 — 사용자 결정):** `0008`은 **기존 객체 변경**만 담는다.
  1. `source_chunks.embedding`을 `extensions.vector(1024)`로 (`0002_search_schema.sql:77`)
  2. `wiki_embeddings.embedding`을 `extensions.vector(1024)`로 (`0002_search_schema.sql:138`)
  3. HNSW 인덱스 2개 drop → recreate — `source_chunks_embedding_idx`(`0002:115`), `wiki_embeddings_embedding_idx`(`0002:152`). 컬럼 타입이 바뀌면 인덱스가 따라가야 한다
  4. `public.search_chunks` drop → create — 시그니처에 `p_query extensions.vector(1536)`이 박혀 있어(`0007_search_and_queue_extensions.sql:72`) `create or replace`로는 바뀌지 않는다

  `dead_letter_job()`과 `usage_events`는 `0008`에 넣지 **않는다**. 판별 기준: "`0008` 이하는 영구 수정 불가"는 **기존 객체 변경**에만 걸린다. 새 함수·새 테이블은 `0009`든 `0012`든 언제든 추가되므로 지금 묶을 이유가 없고, 묶으면 스키마가 그걸 쓰는 코드보다 먼저 확정되어 컬럼·머신을 추측으로 정하게 된다. 반대로 임베딩 차원은 **Phase 3가 첫 임베딩을 만드는 순간 창이 닫힌다** — 지금은 임베딩 데이터가 0건이라 재임베딩 비용이 없다. — **Reversibility:** one-way — `0008`이 클라우드에 push되면 `0008` 이하 번호는 영구히 추가 불가이고, 차원을 되돌리려면 그때 존재하는 모든 임베딩을 재생성해야 한다.

- **D-02 (`0008`은 Wave 1 단독 플랜이고 클라우드 `db push`까지 그 플랜 안에서 [BLOCKING] — 사용자 결정):** `0008` 작성 → 로컬 `supabase db reset` → 클라우드 `supabase db push`가 **한 플랜에서 끝나고**, Phase 3의 나머지 플랜 전부가 그 위에 쌓인다. `02-06-PLAN`이 `0007`에 쓴 관례를 그대로 따른다.

  근거: `0002`와 `0007`이 이미 클라우드에 1536차로 올라가 있으므로, push 전에는 클라우드에서 **어떤 임베딩도 만들 수 없다**. 로컬만 먼저 고치면 로컬↔클라우드 스키마가 페이즈 중간 내내 갈라진 채로 남고, 그 상태에서 작성된 임베딩 코드는 클라우드에서 처음 돌 때 검증된다.

  ⚠️ planner는 `0008` 플랜을 임베딩 핸들러 플랜에 합치지 말 것 — 합치면 파싱·컴파일 플랜들이 이 플랜을 기다리거나, 기다리지 않고 1536차 가정 위에서 진행한다.

- **D-03 (`dead_letter_job()` 시그니처를 지금 잠근다 — 사용자 결정):** `dead_letter_job(p_job_id uuid, p_worker_id text, p_error text)`. `release_job(p_job_id, p_worker_id)`와 **동형**이며 `locked_by = p_worker_id and status = 'running'` 술어를 같이 갖는다. reap이 락을 이미 빼앗은 뒤 늦게 깨어난 워커가 남의 잡을 `dead`로 만드는 경로가 구조적으로 없어진다.

  ⚠️ 새 함수이므로 `0007` §8의 권한 방향을 **반드시 반복**한다:
  ```sql
  revoke all on function public.dead_letter_job(uuid, text, text) from public, anon, authenticated;
  grant execute on function public.dead_letter_job(uuid, text, text) to service_role;
  ```
  빠뜨리면 PostgREST `/rpc/`로 아무나 남의 잡을 데드레터로 보낼 수 있다.

  이 함수는 D-01에 따라 `0008`이 아니라 **그것을 호출하는 `queue.py` 변경과 같은 마이그레이션(`0009`+)**에 들어간다. 현재 한계(`fail_job(backoff=0)`으로 `max_attempts`만큼 왕복해 `dead`에 수렴)는 `apps/worker/src/worker/queue.py:112-136`에 인라인으로 기록되어 있으며, 위협 T-02-43이 그 자리에서 열려 있다.

### 임베딩 공급자와 `embedding_version` 앱 계약

- **D-04 (공급자 = OpenRouter — 사용자 결정, open question 해소):** `checklists.json > open_questions`의 "임베딩 공급자 미정(DeepInfra vs Together vs OpenRouter)"을 **OpenRouter**로 닫는다. 확인된 사실: OpenRouter는 `POST https://openrouter.ai/api/v1/embeddings`를 OpenAI 임베딩 API 형식으로 제공하고, bge-m3는 1024차다. `.planning/research/EMBEDDING.md:116`이 요구한 판정 기준 중 "OpenAI 임베딩 API 호환"은 충족된다.

  **파생 이득 — planner는 이것을 실제로 회수할 것:** `OPENROUTER_API_KEY` 하나가 LLM(COMP-01)과 임베딩(COMP-06)을 모두 덮으므로 `WorkerSettings`에서 `OPENAI_API_KEY`가 **사라질 수 있다**. `decisions.embedding_model`의 implication은 "OPENAI_API_KEY 자리를 대체할 키가 여전히 필요"라고 적었으나, OpenRouter 선택은 새 키를 하나도 요구하지 않는다. 이 결정 이후 그 문장은 무효다. planner는 `WorkerSettings`와 `.env.sample` 양쪽에서 `OPENAI_API_KEY`가 실제로 다른 소비자를 갖는지 확인한 뒤 제거를 판단할 것.

- **D-05 (공급자를 고정하고 폴백을 금지한다 — 사용자 결정):** 임베딩 호출에 `provider: { order: [...], allow_fallbacks: false }`를 **강제**하고, 그 호스트명을 `embedding_version`에 쓴다. `embedding_version` 값은 **모델 + 실제 호스트 + 버전**을 인코딩한다 (D-19가 `tsv_tokenizer_version`을 `bigram-nfkc-cf-v1`로 정한 것과 같은 논리 — 값의 유일한 존재 이유는 나중에 재임베딩 범위를 좁히는 것이다).

  근거: OpenRouter는 같은 모델을 여러 호스팅 업체에 라우팅하고 라우팅 모드에 따라 요청마다 실제 호스트가 달라질 수 있다. 공급자마다 정규화·풀링·truncation 처리가 달라 **같은 모델명이어도 벡터가 미묘하게 다를 수 있으므로**, 고정하지 않으면 `embedding_version`이 한 워크스페이스 안에 섞인 벡터의 평균만 기록하게 되어 애초의 목적을 잃는다.

  ⚠️ 수용한 대가: 고정한 호스트에 장애가 나면 임베딩 잡이 실패한다. 잡은 재시도되지만 **섞인 벡터는 재임베딩 외에 복구 수단이 없으므로** 이 방향이 맞다. planner는 이 실패가 `parse`/`compile`을 되돌리지 않도록 `embed`가 독립 잡이라는 COMP-04 분할을 유지할 것.

### Claude's Discretion

사용자가 명시적으로 위임하거나(마무리 선택), 기존 관례가 답을 이미 정해둔 영역. **planner/researcher가 뒤집을 수 있다 — 다만 뒤집을 때 이유를 남길 것.**

- **D-06 (`0002:76`의 무효 주석 처리):** `0002_search_schema.sql:76`의 `-- text-embedding-3-small(1536차원)` 주석은 `0002` 수정 불가로 영원히 남는다. `0008` 파일 헤더에 **그 주석이 무효임과 대체 근거(`checklists.json > decisions.embedding_model`)를 명시**한다. 이 프로젝트의 파일 헤더 관례(태스크 ID + 결정 키 인용)와 어긋나지 않으며, 근거를 재서술하지 않고 키만 가리킨다.

- **D-07 (`0008`은 단일 트랜잭션):** `begin; … commit;`으로 감싼다. `0007`이 세운 관례이며(`0007:26-31`), 부분 적용이 "컬럼 타입은 바뀌었는데 인덱스나 함수가 옛 차원에 남은" 상태를 만드는 것을 구조적으로 막는다. `notify pgrst, 'reload schema';`도 `0007`처럼 커밋 직전에 넣는다 — 없으면 재생성된 `search_chunks` 호출이 PGRST202로 떨어진다.

- **D-08 (`search_chunks` 재생성 계약 검증):** 재생성 시 옮겨야 하는 계약이 6가지다 — `security invoker` · `stable` · `set search_path` · `hnsw` GUC 3종 · `operator(extensions.<=>)` 수식 · pgvector warmup 한 줄(`0007:54-58`). 하나라도 빠지면 02-01 스파이크가 판정한 트랜스포트 계약이 **조용히** 깨진다. 검증은 기존 자산을 확장한다:
  - `supabase/tests/0008_search_contract.sql` — `pg_proc`의 `prosecdef`(=false) · `provolatile`(=`s`) · `proconfig`(search_path + hnsw 3종)를 단언하고, `EXPLAIN`이 `HNSW Index Scan`을 보이는지까지 확인
  - `scripts/verify_search_contract.sh` — `scripts/verify_queue_functions.sh`와 동형(`ON_ERROR_STOP=1` + 출력 grep). ⚠️ `ON_ERROR_STOP=1`이 없으면 `raise exception`이 나도 psql이 성공 코드로 끝난다
  - GitHub Actions PR 게이트(`02-09-PLAN`이 세운 4잡)에 추가

  둘 다 하는 이유: 마이그레이션 내 어서션은 잘못된 스키마가 클라우드에 **도달하지 못하게** 막고, SQL 계약 러너는 Phase 4가 검색 함수를 다시 건드릴 때의 **회귀**를 잡는다. `0007`이 이미 이 조합(begin/commit + 별도 러너)을 쓴다.

- **D-09 (`0008` 커밋 형태):** `NNNN_snake_case_topic.sql` 규약에 따라 `supabase/migrations/0008_embedding_dimension.sql`. 커밋 메시지는 마이그레이션 번호로 시작한다(`feat(db): 0008 — …`). 산출물 기록은 `docs/ops/migration-0008-record.md`로 `docs/ops/migration-0007-record.md`와 대칭을 이룬다.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

ROADMAP.md의 Phase 3 항목에는 `Canonical refs:` 줄이 없다. 아래는 스카우트와 논의에서 누적한 목록이다.

### 이 페이즈의 계약
- `.planning/ROADMAP.md` §Phase 3 (120-131행) — 5개 성공 기준. 기준 3이 잡 체인 · 축소 재처리 · 스키마 위반 복구 · enum/CHECK 기동 시 실패를 한 문장에 묶는다
- `.planning/REQUIREMENTS.md` ING-01~07 (51-57행) · COMP-01~08 (61-68행) · OPS-01 (114행) — 16개 요구사항 원문
- `.planning/REQUIREMENTS.md` 275행 — OPS-01이 Phase 3에 있는 이유("`usage_events` + 인큐 시점 비용 상한은 **첫 LLM 호출과 같은 페이즈**에 있어야 한다")

### 프로젝트 수명 결정 (재논의 금지 — `checklists.json`이 소유)
- `checklists.json > decisions.embedding_model` — bge-m3 1024차. `implication` 필드가 `0008`의 작업 목록 원본. ⚠️ 단 "OPENAI_API_KEY 자리를 대체할 키가 여전히 필요"는 D-04가 무효화했다
- `checklists.json > decisions.db_transport` — RPC 채택. **검색 쿼리는 애플리케이션이 아니라 마이그레이션이 소유**하고, 쿼리가 바뀔 때마다 새 마이그레이션이 필요하다는 반복 비용을 인지한 상태에서 감수했다
- `checklists.json > decisions.llm` — OpenRouter 경유, `LLM_MODEL` env, Pydantic 검증 + 3회 재시도가 **필수 백스톱**. `openrouter_slug`가 아직 `TODO` — COMP-01이 닫아야 한다
- `checklists.json > decisions.job_queue` · `decisions.original_file_retention` — 큐 계약, Storage 원본 보존
- `checklists.json > open_questions` — 이 페이즈가 닫아야 하는 3건(OpenRouter 모델 슬러그 · 청킹 파라미터 · 월 비용 상한값). 임베딩 공급자는 D-04가 닫았다

### 선행 페이즈에서 물려받은 결정
- `.planning/phases/02-security-spine-and-shared-domain/02-CONTEXT.md` > **D-16** — 하트비트 컬럼을 넣지 않고 잡 분할로 간다. COMP-04의 전제
- 같은 파일 > **D-17** — reap 타임아웃은 Phase 2에서 **잠정치**, Phase 3에서 확정. 근거 문서는 `docs/ops/reap-timeout-baseline.md`
- 같은 파일 > **D-18** — `attempts`가 claim 시점에 증가하므로 자발적 반납은 `release_job`이 필요하다. D-03의 시그니처 동형성 근거
- 같은 파일 > **D-19** — `tsv_tokenizer_version` = `bigram-nfkc-cf-v1`. D-05의 `embedding_version` 설계 논리가 같다
- 같은 파일 > **D-20** — 슬러그는 `slug_v1`, 한글 유지, **LLM은 `title`만 내고 슬러그를 소유하지 않는다**. COMP-01/COMP-05가 그대로 따른다
- 같은 파일 > **D-08** — `service_client(settings: WorkerSettings)` 팩토리. 임베딩·LLM 클라이언트도 같은 형태를 따를 것
- 같은 파일 > **D-11/D-12/D-13** — 쓰기 0행 → 403, 404 안 씀, `42501`도 같은 단일 핸들러. ING-01 인큐 라우터가 이 위에 선다
- `.planning/phases/01-bootstrap-and-ground-truth/01-CONTEXT.md` > **D-01** — 단일 Dockerfile · 단일 이미지
- 같은 파일 > **D-12** — Railway 서비스별 env 스코프. D-04의 키 정리가 착지하는 곳

### 기존 스키마 (재구현 금지 — 이미 적용·검증 완료)
- `supabase/migrations/0002_search_schema.sql:77` · `:115` · `:138` · `:152` — D-01이 바꿀 컬럼 2개와 인덱스 2개. ⚠️ `:76`의 `text-embedding-3-small(1536차원)` 주석은 D-06이 다룬다
- `supabase/migrations/0007_search_and_queue_extensions.sql:37-105` (§1) — `search_chunks` 정의. D-01(4)이 재생성할 대상이고, `⚠️` 주석 4개가 옮겨야 할 계약을 그 자리에서 설명한다
- 같은 파일 §2~§6 — `jobs_dedup_idx`(중복 인큐 차단, 키는 `payload ->> 'target_id'`) · `complete_job_and_chain()`(COMP-04 체인의 원시연산) · `release_job()` · `verified_by`/`verified_at`/`expires_at` · `embedding_version`/`chunker_version`(D-05가 값 규약을 정한 컬럼)
- 같은 파일 §8 — 최소권한 매트릭스. **새 함수를 만들 때마다 반복해야 하는 revoke/grant 방향의 출처**
- `supabase/migrations/0003_jobs.sql:31-36` — `jobs.type`에 enum CHECK가 없는 유일한 예외와 그 이유. 워커가 미등록 type을 dead-letter해야 하는 근거
- `supabase/migrations/0003_jobs.sql:103-212` — 큐 함수 4종. `attempts`가 claim 시점에 증가
- `supabase/migrations/0005_storage.sql` — `sources` 버킷과 `{workspace_id}/{raw_source_id}/{filename}` 경로 강제. ING-03이 그대로 소비
- `supabase/migrations/0001_core_schema.sql:90-` — `raw_sources`(`content_hash` 멱등성 키 · `storage_path`). ⚠️ **UPDATE 정책이 없다** — 불변성이 정책 부재로 강제된다

### 현재 코드 (확장 대상)
- `apps/worker/src/worker/queue.py:112-136` — `_dead_letter()`. D-03이 대체할 인라인 한계가 여기 기록되어 있다
- `apps/worker/src/worker/handlers/noop.py` — 핸들러 레지스트리 형태. `parse`/`compile`/`link_sync`/`embed` 4종이 이 자리에 들어간다
- `apps/worker/src/worker/db/service.py` — service_role 경로. ⚠️ BYPASSRLS이므로 `workspace_id` 필터를 코드가 명시해야 한다
- `apps/worker/src/worker/settings.py` — `WorkerSettings`. D-04의 `OPENAI_API_KEY` 제거 판단 지점
- `packages/core/src/nexuswiki_core/tokenizer.py` — `normalize`/`bigram`/`TSV_TOKENIZER_VERSION`. 청킹(ING-05)과 `search_tsv` 작성이 이걸 쓴다
- `packages/core/src/nexuswiki_core/slug.py` — `slug_v1`. COMP-01이 LLM `title`을 여기 통과시킨다
- `apps/api/src/api/db/user.py` · `apps/api/src/api/errors.py` — `UserDb` 쓰기 메서드와 단일 403 핸들러. ING-01/ING-07 라우터가 소비

### 검증 자산 (확장 대상 — 새로 만들지 말 것)
- `supabase/tests/0007_queue_functions.sql` + `scripts/verify_queue_functions.sh` — SQL 계약 러너 관례. D-08이 확장한다. ⚠️ `ON_ERROR_STOP=1`이 계약의 일부다
- `scripts/spike_db_transport.py` — EXPLAIN 계획 파싱. D-08의 `HNSW Index Scan` 단언이 이 코드를 재사용한다
- `scripts/verify_storage_policies.sh` — ING-03 경로 규약 검증에 재사용 가능

### 실측·결정 기록
- `docs/ops/migration-0007-record.md` — `0007` 적용 기록. `docs/ops/migration-0008-record.md`가 대칭으로 따라간다 (D-09)
- `docs/ops/db-transport-spike.md` — RPC 판정 근거 전문
- `docs/ops/reap-timeout-baseline.md` — noop 큐 오버헤드 실측(p99 127.054ms, N=219)과 **그 한계**. Phase 3가 핸들러 지속시간으로 타임아웃을 확정할 때의 출발점
- `.planning/research/EMBEDDING.md` — bge-m3 선택 근거 전문. 116행이 공급자 판정 기준(지연 + OpenAI API 호환)을 정의했고 D-04가 그것을 닫았다
- `.planning/phases/02-security-spine-and-shared-domain/02-VERIFICATION.md` — 갭 2건과 그 해소. 갭 2가 reap 타임아웃을 Phase 3로 이월한 근거

### 코드베이스 맵 (2026-08-01 기준)
- `.planning/codebase/ARCHITECTURE.md` · `.planning/codebase/INTEGRATIONS.md` · `.planning/codebase/CONVENTIONS.md` · `.planning/codebase/CONCERNS.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`supabase/tests/0007_queue_functions.sql` + `scripts/verify_queue_functions.sh`**: SQL 수준에서 함수 계약을 고정하는 러너가 이미 있고 CI에 붙어 있다. D-08은 새 형식을 만들지 않고 이 쌍을 복제한다
- **`0007` §3 `complete_job_and_chain(uuid, text, jsonb)`**: COMP-04의 `parse → compile → link_sync → embed` 체인을 원자적으로 잇는 원시연산이 **이미 존재한다**. planner는 체인 전이를 애플리케이션에서 두 번 왕복하도록 설계하지 말 것
- **`0007` §2 `jobs_dedup_idx`**: 같은 `payload ->> 'target_id'`에 대한 중복 인큐를 DB가 막는다. ING-02의 "이미 수집됨"은 `content_hash`(원본 중복)와 이 인덱스(잡 중복)의 **두 층**이며 planner는 둘을 섞지 말 것
- **`0007` §6 `embedding_version` / `chunker_version` 컬럼**: 이미 존재한다. D-05가 값 규약만 채운다
- **`packages/core`의 토크나이저·슬러그**: 검증 완료. COMP-01/COMP-05/ING-05가 그대로 소비하고 재구현하지 않는다
- **`0005`의 Storage 정책**: ING-03의 경로 규약을 이미 강제한다. 애플리케이션이 경로를 문자열로 조립하되 정책이 최종 판정자다

### Established Patterns
- **`⚠️` 접두사 = "무시하면 데이터/보안이 조용히 깨지는 지점"**. Phase 3에서 이 마커가 붙을 곳: D-05(섞인 벡터), D-08(트랜스포트 계약 누락), COMP-08(provider 예외 노출), 축소 재처리 잔여 행
- **새 함수를 만들 때마다 `0007` §8의 revoke/grant 방향을 반복한다.** 빠뜨리면 PostgREST `/rpc/`가 그대로 공개 표면이 된다
- **단일 트랜잭션 마이그레이션** — `0007`이 시작한 관례(D-07)
- **마이그레이션 번호 = 적용 순서**, `NNNN_snake_case_topic.sql`. `0008`이 다음 번호이며 push는 편도
- **파일 헤더에 태스크 ID + 결정 키 인용, 근거는 재서술하지 않음.** 프로젝트 수명 결정은 `checklists.json > decisions.<key>`, 페이즈 한정 결정은 `03-CONTEXT.md > D-XX`
- **모든 주석·커밋 메시지·문서는 한국어**, 식별자·키워드·파일명은 영문
- **"정책이 없어서 못 한다"가 이 프로젝트의 관용구** — `raw_sources`에 UPDATE 정책이 없다는 사실이 ING의 불변성 보장이다

### Integration Points
- **`apps/worker/src/worker/handlers/__init__.py`** — 핸들러 레지스트리. 미등록 type이 dead-letter로 가는 경로(D-03)와 같은 자리
- **`apps/worker/src/worker/settings.py`** — D-04의 키 정리 지점. Railway 서비스별 env(Phase 1 D-12)와 짝을 이룬다
- **`apps/api`의 인큐 라우터 (신규)** — ING-01의 202 응답. `UserDb` 403 매핑(02 D-11~13)과 OPS-01의 인큐 시점 상한 거부가 여기서 만난다
- **GitHub Actions PR 게이트 (`02-09-PLAN`의 4잡)** — D-08의 계약 러너가 5번째 잡으로 붙는다
- **`0008` → 나머지 전 플랜** — D-02가 만든 유일한 하드 의존. Wave 1이 닫히기 전에는 어떤 임베딩 코드도 클라우드에서 검증될 수 없다

</code_context>

<specifics>
## Specific Ideas

- **"`0008` 이하 수정 불가"는 기존 객체 변경에만 걸린다** — 이 구분이 D-01의 전부다. 새 테이블·새 함수를 `0008`에 밀어 넣으면 스키마가 그것을 쓰는 코드보다 먼저 확정되고, 그 추측이 틀렸을 때 **그 추측까지 수정 불가 구간에 들어간다**. planner는 "한 번에 끝내자"는 유혹을 이 문장으로 기각할 것
- **재임베딩 창은 Phase 3가 첫 임베딩을 만드는 순간 닫힌다** — 지금 창이 열려 있는 유일한 이유는 임베딩 데이터가 0건이기 때문이다. D-02가 `0008`을 Wave 1에 두는 이유가 이것이며, 순서를 바꾸면 되돌릴 비용이 0에서 전체 재임베딩으로 점프한다
- **`embedding_version`은 기록용 메타데이터가 아니라 재임베딩 범위를 좁히는 도구다** — D-19가 `tsv_tokenizer_version`에서 확립한 논리와 같다. 값이 결과를 바꿀 수 있는 축(모델·호스트)을 인코딩하지 않으면 나중에 "무엇을 다시 만들어야 하는가"에 답할 수 없어 전량 재임베딩이 유일한 선택지가 된다
- **D-05는 가용성을 의도적으로 희생한다** — 폴백을 허용하면 임베딩 잡은 항상 성공하지만 워크스페이스 안에 섞인 벡터가 남고, 그건 재임베딩 외에 복구 수단이 없다. 반대로 폴백을 막으면 잡이 실패할 뿐이고 잡은 재시도된다. **복구 가능한 실패를 복구 불가능한 성공보다 택했다**
- **`search_chunks` 재생성의 위험은 "실패"가 아니라 "성공한 것처럼 보이는 누락"이다** — `security invoker`를 `definer`로 잘못 쓰면 교차 테넌트 검색이 열리고, `stable`이나 hnsw GUC가 빠지면 아무 에러 없이 검색 품질만 조용히 나빠진다. `0007:45-62`의 주석 4개가 각각의 실패 양상을 이미 서술해두었으므로 D-08은 그 목록을 단언으로 옮기는 작업이다
- **OpenRouter 선택은 키를 늘리지 않고 줄인다** — planner가 이 이득을 회수하지 않으면 워커가 쓰지 않는 `OPENAI_API_KEY`를 Railway에 계속 주입하게 되고, 그건 "역량 부재"(02 D-06)로 격리를 강제한다는 이 프로젝트의 보안 논리와 어긋난다

</specifics>

<deferred>
## Deferred Ideas

### 이 페이즈 안에서 열려 있는 것 (researcher/planner가 채운다)

사용자가 `0008 마이그레이션 경계` 한 영역만 골랐으므로 아래는 **위임된 것이지 결정되지 않은 것이 아니다.** researcher는 이 셋을 RESEARCH.md의 주요 조사 대상으로 삼을 것.

- **컴파일 산출 단위 (COMP-01/COMP-07)** — 소스 1개가 위키 페이지 몇 개가 되는가, 같은 `(workspace_id, slug)`가 다시 나오면 덮어쓰기·병합·거부 중 무엇인가, `upsert_and_truncate`의 "축소 재처리"가 페이지 수준에도 적용되는가. 제품 핵심에 가까우므로 planner가 임의로 정하지 말고 근거를 남길 것
- **비용 상한과 잡 취소 (OPS-01)** — 상한 단위(달러 vs 토큰)와 값(`open_questions`가 "P4-OPS-01에서 확정"으로 적어둔 것을 Phase 3가 앞당겨 닫아야 한다), 인큐 거부 응답 형태, `running` 잡의 취소 메커니즘. ⚠️ `jobs.status`에 취소 상태가 없어(`0003`) 협조적 취소가 필요하다 — 새 상태값은 CHECK 변경이므로 **기존 객체 변경**이고, D-01의 판별 기준상 `0008`에 넣었어야 하는지 planner가 재검토할 것
- **수집 게이트와 청킹 (ING-04/ING-05)** — PDF 추출 품질 임계값(페이지당 문자 수)과 `needs_ocr` 판정선, URL 수집 방식, 청킹 토큰 수·오버랩 초기값과 **어느 토크나이저로 세는가**(bge-m3의 8192 컨텍스트와 `packages/core`의 bigram 토크나이저는 다른 것이다). `open_questions`의 "청킹 파라미터 — P2-ING-02에서 실측 후 확정"이 여기서 닫힌다

### 다른 페이즈로 미루는 것

- **reap 타임아웃 최종 확정 (02 D-17)** — Phase 3 범위이긴 하나 **핸들러 지속시간을 실측한 뒤**에만 정할 수 있으므로 파이프라인이 실제로 도는 후반 플랜에 배치한다. 출발점은 `docs/ops/reap-timeout-baseline.md`이며, ⚠️ noop p99 127ms에서 유도한 잠정 2초를 그대로 적용하면 LLM 대기 중인 컴파일 잡이 전부 reap되어 이중 처리된다
- **`jobs` 하트비트 컬럼 (`heartbeat_at` + `heartbeat_job()`)** — 02 D-16이 미룬 것. 잡 분할(COMP-04)만으로 부족하다는 것이 **실측으로** 드러나면 그때 추가한다. 되돌리기 싼 변경이라 미루는 비용이 낮다
- **`bge-m3`의 sparse 벡터가 앱 레이어 bigram 어휘 채널을 보강·대체할 수 있는지** — `open_questions`가 Phase 4 RTV-06 골든 질의 세트로 판정하기로 이미 정했다. Phase 3는 dense 1024차만 다룬다
- **나머지 4개 채널의 검색 함수** — `0007:64-66`이 Phase 4로 명시적으로 미뤘다. 융합 가중치와 `k`가 정해지기 전에 시그니처를 고정하면 `0009`, `0010`으로 계속 되돌아온다
- **`relaxed_order` vs `strict_order` 벤치마크 (RTV-04)** — Phase 4
- **`README.md:16`의 `uv sync --frozen`이 워크스페이스 멤버를 설치하지 않는 문제** — `02-02`에서 범위 밖으로 발견됨(`.planning/phases/02-security-spine-and-shared-domain/deferred-items.md`). ROADMAP Phase 1 성공기준 3과 어긋나므로 여전히 미해결. Phase 3가 다루지 않으면 계속 이월된다

</deferred>

---

*Phase: 3-Ingest and Compile Pipeline*
*Context gathered: 2026-08-07*
