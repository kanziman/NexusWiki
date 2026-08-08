# Requirements: NexusWiki

**Defined:** 2026-08-02
**Core Value:** 질문에 대한 답이 원문 청크와 컴파일된 위키 페이지 양쪽으로 추적 가능해야 한다

**Scope basis:** `checklists.json` Phase 0~4 전체 32개 태스크를 이관하되, 리서치가 찾아낸 P0 블로커와
확정 결정 4건(싱가포르 리전 · 읽기 전용 페이지 · `0007` 스키마 보강 · 캔버스 v1 유지)을 반영해 확장.
이미 적용·검증이 끝난 데이터 계층(마이그레이션 `0001`~`0004`, `0006`)은 PROJECT.md의 Validated에 있으며
여기 v1 요구사항에는 포함하지 않는다.

---

## v1 Requirements

### Bootstrap (BOOT)

- [x] **BOOT-01**: `sources` 비공개 버킷과 **실제 `storage.objects` 정책**이 마이그레이션 `0005`로 적용된다 (경로 규약이 주석이 아니라 강제여야 함, 첫 클라우드 push 이전 필수)
- [x] **BOOT-02**: Supabase Cloud 프로젝트가 **싱가포르 `ap-southeast-1`** 에 생성되고 `sb_publishable_` / `sb_secret_` 키 체계를 사용한다 (2025-11 이후 생성 프로젝트에는 legacy 키가 발급되지 않음)
- [x] **BOOT-03**: Supabase CLI를 첫 클라우드 `db push` 이전에 업그레이드한다
- [x] **BOOT-04**: uv 워크스페이스 monorepo(`apps/api` · `apps/worker` · `packages/core`)가 구성되고, `packages/core`가 두 앱보다 먼저 존재한다
- [x] **BOOT-05**: ruff + prettier pre-commit, `.editorconfig`, 루트 README가 동작한다
- [x] **BOOT-06**: FastAPI 앱이 `lifespan`으로 기동하고 `/health`가 응답하며 structlog 구조화 로깅이 `job_id`/`workspace_id`를 컨텍스트로 바인딩한다
- [x] **BOOT-07**: Next.js **15.5.22 이상**(하한 15.2.3 — CVE-2025-29927) 앱이 Tailwind 4 · TypeScript strict · Vitest + Testing Library로 구성된다
- [x] **BOOT-08**: Railway가 단일 Dockerfile·Root Directory `/`에서 `api`(web)와 `worker`(resident) 두 서비스를 `asia-southeast1`에 배포하고, 두 서비스가 동일 이미지로 동작함이 보장된다
- [x] **BOOT-09**: Railway ↔ Supabase 실측 RTT가 기록된다 (`checklists.json` open question #2 해소)
- [x] **BOOT-10**: 프로덕션 인증 설정이 하드닝된다 (비밀번호 길이, 이메일 확인 — 팀 제품에 CLI 기본값 사용 금지)

### Tenant Isolation Spine (SEC)

- [x] **SEC-01**: `ApiSettings`에 service key 필드가 **존재하지 않는다**; `WorkerSettings`만 보유하고 Railway에서도 worker 서비스에만 주입된다
- [x] **SEC-02**: `db/user.py`와 `db/service.py`가 분리되고 ruff banned-api 규칙이 `worker/**` 외의 `db/service` import를 차단한다
- [x] **SEC-03**: CI가 worker 밖의 `service_client` 사용을 탐지하면 빌드를 실패시킨다
- [x] **SEC-04**: `UserDb`가 *affected rows = 0*을 403으로 매핑한다 (라우터마다 흩어지지 않고 한 곳에서)
- [x] **SEC-05**: 클라이언트 번들에 secret 키가 포함되지 않음이 grep으로 검증된다
- [x] **SEC-06**: 애플리케이션 경로에서의 교차 테넌트 접근 시도가 테스트로 차단 확인된다

### Data Access & Shared Domain (DOM)

- [x] **DOM-01**: DB 트랜스포트가 **스파이크로 결정**되고 기록된다 — `create function ... SET hnsw.iterative_scan`이 Supabase RPC를 통해 실제로 적용되는지 검증 (적용되면 `SECURITY INVOKER` RPC, 아니면 asyncpg + Supavisor session mode)
- [x] **DOM-02**: 마이그레이션 `0007`이 검색 함수 · `jobs_dedup_idx` · `complete_job_and_chain()`(원자적 complete+enqueue)을 추가한다
- [x] **DOM-03**: `0007`이 `verification_status`에 `verified_by` / `verified_at` / `expires_at`을 추가한다 (주인과 날짜 없는 검증 배지는 쓰이지 않음)
- [x] **DOM-04**: `0007`이 `embedding_version` / `chunker_version`을 추가한다 (어휘 검색에만 버전이 있던 비대칭 해소)
- [x] **DOM-05**: `packages/core`의 단일 모듈이 `normalize()`(NFKC + casefold + 공백 정규화)와 `bigram()`을 제공하고, `bigram()`은 정규화된 입력만 받는다; `tsv_tokenizer_version`이 정규화 형식까지 인코딩한다
- [x] **DOM-06**: NFC / NFD / 전각 입력에 대한 토크나이저 왕복 자가검색 테스트가 통과한다
- [x] **DOM-07**: 슬러그가 `title`의 결정적 순수 함수로 생성되고 버전이 붙는다 — **LLM은 슬러그를 소유하지 않는다**; 페이지 생성 전 기존 슬러그와 `wiki_links.target_slug`에 대해 해소한다
- [x] **DOM-08**: 워커 스켈레톤이 SIGTERM graceful shutdown · reaper · `noop` 잡 타입으로 큐 계약을 증명한다 (LLM 비용 발생 이전에)
- [x] **DOM-09**: `jobs`에 하트비트 가능 컬럼이 있는지 확인하고, `reap_stale_jobs` 타임아웃을 실측 p99 기준으로 설정한다 (없으면 컴파일을 더 작은 잡으로 분할)

### Ingestion (ING)

- [ ] **ING-01**: 사용자가 파일 · URL · 텍스트를 투입하면 즉시 `202`와 잡 식별자를 받는다 (블로킹 작업이 요청 안에서 실행되지 않음)
- [ ] **ING-02**: 동일 `content_hash` 재투입이 **눈에 보이게** "이미 수집됨 — 건너뜀"으로 표시된다 (조용한 성공 금지)
- [ ] **ING-03**: 원본 파일이 `{workspace_id}/{raw_source_id}/{filename}` 경로로 Storage에 보존된다
- [ ] **ING-04**: 문서 파서가 추출 품질 게이트(페이지당 문자 수 임계값)를 적용하고, 미달 시 `needs_ocr`로 잡을 실패시켜 UI에 사유를 노출한다 (빈 문서를 조용히 수집하지 않음)
- [x] **ING-05**: 청킹이 토큰 기준으로 수행되고 `content[char_start:char_end] == chunk.content` 속성 테스트가 통과한다
- [ ] **ING-06**: 사용자가 소스별 잡 진행 상태를 **실제 단계 이름**으로 확인한다 (불확정 스피너 금지 — 4분 컴파일이 멈춘 것처럼 보이면 재투입으로 비용이 2배가 됨)
- [ ] **ING-07**: 사용자가 `dead` 상태 잡을 재시도할 수 있다

### Compile Pipeline (COMP)

- [x] **COMP-01**: 워커가 OpenRouter LLM으로 소스를 위키 페이지로 컴파일하고 Pydantic 검증 + 3회 재시도를 **필수 백스톱**으로 적용한다 (`response_format` json_schema는 모델 능력 탐지 후 선택적 최적화)
- [ ] **COMP-02**: 기동 시 Python enum 정의와 `pg_constraint`의 CHECK 값을 대조하는 어서션이 불일치를 즉시 실패시킨다
- [x] **COMP-03**: 재시도 2·3회차가 1회차와 달라진다 — 검증 오류를 프롬프트에 되먹인다
- [ ] **COMP-04**: 잡이 `parse → compile → link_sync → embed` 체인으로 분리되어 각 단계가 자기 멱등성 키를 갖는다 (모놀리식 잡의 p99가 reap 윈도우를 넘어 정상 잡이 탈취·이중 과금되는 것을 방지)
- [ ] **COMP-05**: `[[WikiLink]]`가 파싱되어 `wiki_links`에 동기화되고, 미해결 타깃은 레드 링크(`to_wiki_id IS NULL`)로 남는다
- [x] **COMP-06**: 위키 청크와 원문 청크 양쪽이 임베딩된다 (`source.embed`는 `wiki.compile`과 병렬)
- [ ] **COMP-07**: 재처리 결과가 더 적은 단위로 줄어드는 경우에도 잔여 행이 삭제된다 (`upsert_and_truncate` — `source_chunks` · `wiki_embeddings` · `wiki_links` 공통)
- [ ] **COMP-08**: 원본 provider 예외가 `jobs.last_error`에 그대로 들어가지 않는다 (`jobs_select_member`가 viewer에게 `select *`를 허용함)

### Retrieval (RTV)

- [ ] **RTV-01**: 검색이 2웨이브로 동작한다 — 채널 1~4 동시 실행 후 RRF, 그 결과를 seed로 채널 5(그래프 확장) 실행 후 재융합
- [ ] **RTV-02**: RRF가 순위만 사용하고 채널별 가중치·`k`·limit이 Python 정책 계층에 있다 (SQL 안에서 융합하지 않음)
- [ ] **RTV-03**: `hnsw.iterative_scan` · `hnsw.ef_search` · `hnsw.max_scan_tuples` 세 GUC가 모두 설정된다 (`strict_order` 단독은 불충분 — `ef_search` 기본값 40에 묶임)
- [ ] **RTV-04**: `relaxed_order` 대 `strict_order`가 실제 코퍼스로 벤치마크되고 선택 근거가 기록된다
- [ ] **RTV-05**: 채널별 기여도(`channel_hits`)와 `returned < requested_k`가 1급 메트릭으로 기록된다
- [ ] **RTV-06**: 한국어/영어/혼합 30~50문항 골든 질의 세트가 존재한다 (가중치·`k`·청크 크기·그래프 채널 가치를 판정하는 전제 조건)
- [ ] **RTV-07**: 그래프 채널이 depth ≤ 2 · fan-out 상한 · 사이클 가드를 갖고, 골든 세트로 가치가 입증될 때까지 기본 비활성 플래그 뒤에 있다
- [ ] **RTV-08**: `EXPLAIN` 회귀 테스트가 HNSW 인덱스 스캔 사용을 단언한다 (플래너가 조용히 seq scan으로 이탈하는 것을 탐지)
- [ ] **RTV-09**: 한 채널이 실패해도 요청이 실패하지 않고 융합에서 빠지며 `meta`에 보고된다

### Citation Integrity (CITE)

- [ ] **CITE-01**: 인용 앵커가 서버 발급 짧은 별칭(`[[src:s3]]`)으로 프롬프트에 주입되고 서버가 실제 id로 해소한다 (36자 UUID를 모델이 정확히 복사하도록 요구하지 않음)
- [ ] **CITE-02**: `double_citation`이 **파싱된 앵커 ∩ 검색 결과**로 구성된다 (검색 결과 그대로가 아니라)
- [ ] **CITE-03**: 발급되지 않은 앵커는 조작으로 간주해 제거하고 카운트한다
- [ ] **CITE-04**: 앵커가 하나도 없으면 "근거를 찾지 못했습니다"를 명시적으로 반환한다
- [ ] **CITE-05**: `dual_citation_rate` · `unsourced_sentence_ratio` · `fabricated_anchor_count` · `cited_anchor_count`가 측정된다
- [ ] **CITE-06**: 수집된 소스가 위조한 `[[...]]` 앵커가 수집 시점에 제거된다 (소스를 통한 프롬프트 인젝션 차단)

### Ask & Read APIs (API)

- [ ] **API-01**: Ask 엔드포인트가 SSE로 스트리밍한다 — `meta` → `delta*` → `citations` → `done` 순서, POST + fetch + ReadableStream (`EventSource` 불가 — GET 전용이라 `Authorization` 설정 불가)
- [ ] **API-02**: 상황별 `ask` 프롬프트 템플릿을 선택해 질문할 수 있다
- [ ] **API-03**: 답변 언어가 질문 언어를 따른다
- [ ] **API-04**: 위키 · 소스 · 그래프 · 잡 상태 조회 API가 제공된다 (RSC 직접 읽기로 대체 가능한 것은 제외)

### Knowledge Quality (QC)

- [ ] **QC-01**: 지식 충돌이 감지되어 `disputed`로 표시된다
- [ ] **QC-02**: 검증 상태 전이 API가 **누가 · 언제 · 언제까지**를 기록한다 (`verified_by` / `verified_at` / `expires_at`)

### Frontend (UI)

- [ ] **UI-01**: 사용자가 로그인하면 `middleware.ts`가 유일한 쿠키 기록자로 동작하고 `/w/[workspaceId]`가 테넌시의 단일 진실 소스가 된다 (React state의 낡은 id는 에러 없이 빈 결과를 내므로 URL이 소유)
- [ ] **UI-02**: 사용자가 워크스페이스를 전환하고, 이메일로 멤버를 초대하고, 3역할을 부여할 수 있다
- [ ] **UI-03**: 드롭존에서 소스를 투입하고 잡 체인 진행 상태를 실제 단계로 확인한다
- [ ] **UI-04**: Ask UI가 상황별 프롬프트 칩과 이중 Citation 카드를 제공하고, 인용 마커가 **근거가 되는 절 옆에** 인라인으로 붙으며, 스트리밍 중 제자리에서 해소된다; 원문은 `char_start`/`char_end` 구간이 하이라이트되고 근거 없음 상태가 구분된다
- [ ] **UI-05**: 위키 뷰어가 **읽기 전용임을 명시**하고("이 페이지는 컴파일됩니다") WikiLink 내비게이션 · 레드 링크("아직 작성되지 않음 · 지금 생성") · 상태 콜아웃을 제공한다
- [ ] **UI-06**: Cytoscape 지식 캔버스가 렌즈 필터(`wiki_pages.category` 재사용)와 함께 동작하고, **PostgREST 1000행 상한에 대한 처리**(페이지네이션 또는 서브그래프 제한)를 포함한다

### Cost, Verification & Ops (OPS)

- [ ] **OPS-01**: `usage_events` 테이블 · 인큐 시점 워크스페이스별 비용 상한 · 입력 크기 상한 · 잡 취소 경로가 동작한다
- [ ] **OPS-02**: 수집 → 컴파일 → 임베딩 → 검색 E2E 시나리오가 통과한다
- [ ] **OPS-03**: 재수집 멱등성이 검증된다 — 동일 `content_hash` 무증가 **및 더 적은 단위로 줄어드는 축소 케이스**
- [ ] **OPS-04**: 워크스페이스 격리가 애플리케이션 경로 전수로 검증된다
- [ ] **OPS-05**: 검색 품질(골든 세트 기준)과 지연 기준선이 수립된다
- [ ] **OPS-06**: LLM/임베딩 비용과 잡 파이프라인에 대한 관측이 갖춰진다

---

## v2 Requirements

현재 로드맵 밖. 추적하되 계획하지 않는다.

### Navigation

- **NAV-01**: 페이지별 backlinks 패널 (`wiki_links` 역방향 조회 1회 — LOW 복잡도)
- **NAV-02**: 랭킹된 레드링크 백로그 ("12개 페이지가 `[[온보딩 절차]]`를 참조하는데 없음" — 경쟁사 미제공)
- **NAV-03**: `wiki_links`를 걸어 만드는 후속 질문 칩 (LLM 비용 0)

### Maintain

- **MNT-01**: `maintain` 워크플로우 — 중복 탐지 · 병합 · 린트. Karpathy 패턴의 세 번째 워크플로우이자 위키를 "누적"이 아닌 "살아있게" 만드는 요소 (HIGH 복잡도, 트리거: ~100 페이지 또는 첫 중복 슬러그 민원)
- **MNT-02**: 컴파일 로그 — 어느 소스가 · 어느 컴파일에서 · 어느 `prompt_template_id`로. 프롬프트가 교체 가능하므로 소스가 안 바뀌어도 페이지가 바뀔 수 있어 필요
- **MNT-03**: 검증 상태를 RRF 랭킹 입력으로 연결 (Guru가 검증 배지를 살아있게 만든 유일한 이유 — 만료 콘텐츠를 AI 답변에서 강등)

### Quality & History

- **QCV-01**: 타입이 있는 충돌 감지 — 시간적(=staleness)은 자동 해소, 사실적 불일치만 에스컬레이션
- **QCV-02**: 답변 이력 저장 (`ask_answers`) — 퍼머링크 · 피드백 루프 · `disputed`의 증거 추적
- **QCV-03**: 조종 가능한 컴파일 아웃라인

### Platform

- **PLT-01**: 채팅 전용 공개 공유 (`anon` 경로를 여는 것은 검증된 격리에 대한 최고 위험 변경 — 별도 검증 필요)
- **PLT-02**: 외부 커넥터 (Notion, Google Drive, Slack)
- **PLT-03**: SSO / SAML

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| 수치 `confidence` 배지 노출 | 검증 배지와 신뢰 신호가 경쟁해 둘 다 안 읽히게 됨. LLM 자기 확신도는 캘리브레이션되지 않음 |
| 위키 페이지 자유 텍스트 편집 | `(workspace_id, slug)` 업서트와 정면 충돌 — 재컴파일이 편집을 덮어씀. v1은 읽기 전용임을 UI가 명시 |
| 전체 자동 재컴파일 | 비용이 소스 수에 선형이고 사용자가 통제할 수 없음 |
| 페이지 단위 권한 | 워크스페이스 3역할이 엔터프라이즈 규모에서도 실질 상한 |
| Neo4j 등 그래프 DB | GDS가 Aura 기본 티어에 없고 이 규모에서 순회 이점 없음. 팀 모드에선 RLS 부재가 보안 부담. `wiki_links` + recursive CTE로 대체 |
| pg_bigm / pgroonga | Supabase 미제공 |
| `search_tsv` 생성 컬럼화 | Postgres에 한국어 형태소 분석기 없음 — 공백 분리만 되어 어휘 검색이 무력화됨 |
| PyMuPDF | AGPL-3.0이 네트워크 사용자에게 미침 — 호스팅 SaaS는 소스 공개 또는 Artifex 라이선스 구매 필요. pypdf(BSD-3)로 대체 |
| `react-cytoscapejs` | 2022-09-02 마지막 배포, 이슈 45건, React 18 StrictMode 이전. Cytoscape 직접 사용 |
| Celery / arq / dramatiq / RQ | 전부 브로커(Redis)를 요구하고 이미 검증된 `claim_job` 계약을 중복 구현 |
| Alembic / SQLAlchemy | 마이그레이션 진실 소스가 둘이 됨 |
| Turborepo / Nx | JS 패키지가 하나뿐 |
| Gunicorn | Railway SIGTERM drain을 깨고 $5/mo 인스턴스에서 유휴 메모리 2배 |
| Fly.io / Render 배포 | 각 ~$6.5/mo, $14/mo 고정 — Railway Hobby($5/mo, 워크스페이스 단위) 대비 불리 |
| 서울 리전 | Railway에 서울·도쿄 리전이 없어 교차 리전 왕복이 5채널마다 곱해짐. 싱가포르 양쪽으로 확정 |
| 모바일 네이티브 앱 | 웹 우선 |
| 외부 큐 브로커 / 캐시 계층 | Postgres 하나로 충분하고 잡 상태를 프론트에 그대로 노출 가능 |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BOOT-01 | Phase 1 | Complete |
| BOOT-02 | Phase 1 | Complete |
| BOOT-03 | Phase 1 | Complete |
| BOOT-04 | Phase 1 | Complete |
| BOOT-05 | Phase 1 | Complete |
| BOOT-06 | Phase 1 | Complete |
| BOOT-07 | Phase 1 | Complete |
| BOOT-08 | Phase 1 | Complete |
| BOOT-09 | Phase 1 | Complete |
| BOOT-10 | Phase 1 | Complete |
| SEC-01 | Phase 2 | Complete |
| SEC-02 | Phase 2 | Complete |
| SEC-03 | Phase 2 | Complete |
| SEC-04 | Phase 2 | Complete |
| SEC-05 | Phase 2 | Complete |
| SEC-06 | Phase 2 | Complete |
| DOM-01 | Phase 2 | Complete |
| DOM-02 | Phase 2 | Complete |
| DOM-03 | Phase 2 | Complete |
| DOM-04 | Phase 2 | Complete |
| DOM-05 | Phase 2 | Complete |
| DOM-06 | Phase 2 | Complete |
| DOM-07 | Phase 2 | Complete |
| DOM-08 | Phase 2 | Complete |
| DOM-09 | Phase 2 | Complete |
| ING-01 | Phase 3 | Pending |
| ING-02 | Phase 3 | Pending |
| ING-03 | Phase 3 | Pending |
| ING-04 | Phase 3 | Pending |
| ING-05 | Phase 3 | Complete |
| ING-06 | Phase 3 | Pending |
| ING-07 | Phase 3 | Pending |
| COMP-01 | Phase 3 | Complete |
| COMP-02 | Phase 3 | Pending |
| COMP-03 | Phase 3 | Complete |
| COMP-04 | Phase 3 | Pending |
| COMP-05 | Phase 3 | Pending |
| COMP-06 | Phase 3 | Complete |
| COMP-07 | Phase 3 | Pending |
| COMP-08 | Phase 3 | Pending |
| OPS-01 | Phase 3 | Pending |
| RTV-01 | Phase 4 | Pending |
| RTV-02 | Phase 4 | Pending |
| RTV-03 | Phase 4 | Pending |
| RTV-04 | Phase 4 | Pending |
| RTV-05 | Phase 4 | Pending |
| RTV-06 | Phase 4 | Pending |
| RTV-07 | Phase 4 | Pending |
| RTV-08 | Phase 4 | Pending |
| RTV-09 | Phase 4 | Pending |
| CITE-01 | Phase 5 | Pending |
| CITE-02 | Phase 5 | Pending |
| CITE-03 | Phase 5 | Pending |
| CITE-04 | Phase 5 | Pending |
| CITE-05 | Phase 5 | Pending |
| CITE-06 | Phase 5 | Pending |
| API-01 | Phase 5 | Pending |
| API-02 | Phase 5 | Pending |
| API-03 | Phase 5 | Pending |
| API-04 | Phase 5 | Pending |
| QC-01 | Phase 5 | Pending |
| QC-02 | Phase 5 | Pending |
| UI-01 | Phase 6 | Pending |
| UI-02 | Phase 6 | Pending |
| UI-03 | Phase 6 | Pending |
| UI-04 | Phase 6 | Pending |
| UI-05 | Phase 6 | Pending |
| UI-06 | Phase 6 | Pending |
| OPS-02 | Phase 7 | Pending |
| OPS-03 | Phase 7 | Pending |
| OPS-04 | Phase 7 | Pending |
| OPS-05 | Phase 7 | Pending |
| OPS-06 | Phase 7 | Pending |

**Coverage:**

- v1 requirements: 73 total (BOOT 10 · SEC 6 · DOM 9 · ING 7 · COMP 8 · RTV 9 · CITE 6 · API 4 · QC 2 · UI 6 · OPS 6)
- Mapped to phases: 73 ✓
- Unmapped: 0

**Per-phase counts:**

| Phase | Requirements | Count |
|-------|--------------|-------|
| Phase 1 — Bootstrap and Ground Truth | BOOT-01…10 | 10 |
| Phase 2 — Security Spine and Shared Domain | SEC-01…06, DOM-01…09 | 15 |
| Phase 3 — Ingest and Compile Pipeline | ING-01…07, COMP-01…08, OPS-01 | 16 |
| Phase 4 — Hybrid Retrieval and Fusion | RTV-01…09 | 9 |
| Phase 5 — Citation Integrity and Answer APIs | CITE-01…06, API-01…04, QC-01…02 | 12 |
| Phase 6 — Dashboard | UI-01…06 | 6 |
| Phase 7 — Integration and Ops Baseline | OPS-02…06 | 5 |

**배치 근거 (카테고리 경계를 의도적으로 벗어난 3건):**

- **OPS-01 → Phase 3**: `usage_events` + 인큐 시점 비용 상한은 **첫 LLM 호출과 같은 페이즈**에 있어야 한다. 나머지 비용 관측(OPS-06)이 전부 이 테이블 위에 세워진다
- **RTV-06 → Phase 4**: 골든 질의 세트는 ops 산출물이 아니라 retrieval의 **전제 조건**이다. 이것 없이는 RTV-02(가중치)·RTV-04(`relaxed_order` 대 `strict_order`)·RTV-07(그래프 채널 가치)이 전부 반증 불가능하다
- **QC-01 / QC-02 → Phase 5**: 충돌 감지는 "의미적으로 유사하되 상충하는 내용"을 찾는 것이라 검색 위에 얹히고, 검증 상태 전이는 `0007`이 추가하는 `verified_by`/`verified_at`/`expires_at`(Phase 2)에 의존한다. 둘 다 UI-05의 상태 콜아웃이 소비하는 백엔드다

**SEC-06 vs OPS-04 (중복 아님):** SEC-06은 보안 척추가 실제로 동작하는지 확인하는 Phase 2의 단일 격리 테스트이고, OPS-04는 모든 애플리케이션 경로가 존재한 뒤 도는 Phase 7의 전수 스위트다.

---
*Requirements defined: 2026-08-02*
*Last updated: 2026-08-02 after roadmap creation*
