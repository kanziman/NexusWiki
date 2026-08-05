# Roadmap: NexusWiki

## Overview

데이터 계층(마이그레이션 `0001`~`0004`, `0006`)은 이미 적용·검증이 끝났다. 이 로드맵은 그 위에
애플리케이션을 올리는 여정이다. 되돌릴 수 없는 결정(리전·키 체계·`0005` 순서·모노레포 형태)을 먼저
못 박고(1), 테넌트 격리와 DB 트랜스포트와 공용 토크나이저를 **라우터가 하나라도 생기기 전에** 구조로
확정한 뒤(2), 소스를 위키로 만드는 쓰기 경로를 비용 상한과 함께 세우고(3), 5채널 검색을 골든 세트로
측정 가능하게 만든 다음(4), 제품의 핵심 가치인 이중 Citation과 답변 API를 그 위에 얹는다(5).
프론트엔드 셸은 워커 스켈레톤 이후 백엔드 트랙과 병렬로 진행해 Ask UI에서 만나고(6), 마지막으로
E2E·멱등성·격리·품질·비용 기준선을 세운다(7).

순서의 원칙은 하나다 — **제약이 기능보다 먼저**. 설정 분리·토크나이저·트랜스포트는 지금은 싸고
나중엔 재작성이며, 셋 다 실패해도 에러를 내지 않는다.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Bootstrap and Ground Truth** - 되돌릴 수 없는 결정을 전부 확정하고 두 서비스를 클라우드에 띄운다
- [ ] **Phase 2: Security Spine and Shared Domain** - 격리·트랜스포트·토크나이저를 라우터 이전에 구조로 확정한다
- [ ] **Phase 3: Ingest and Compile Pipeline** - 투입한 소스가 링크·임베딩된 위키 페이지가 되는 쓰기 경로
- [ ] **Phase 4: Hybrid Retrieval and Fusion** - 5채널 2웨이브 검색을 골든 세트로 측정 가능하게 만든다
- [ ] **Phase 5: Citation Integrity and Answer APIs** - 실제로 인용한 근거만 이중 Citation으로 돌려주는 답변 계층
- [ ] **Phase 6: Dashboard** - 브라우저만으로 워크스페이스를 운영하는 프론트엔드
- [ ] **Phase 7: Integration and Ops Baseline** - E2E·멱등성·격리·품질·비용 기준선

## Phase Details

### Phase 1: Bootstrap and Ground Truth

**Goal**: 나중에 바꿀 수 없거나 매주 비싸지는 결정이 전부 확정되고, `api`와 `worker` 두 서비스가 클라우드에서 실제로 기동한다
**Depends on**: Nothing (first phase)
**Requirements**: BOOT-01, BOOT-02, BOOT-03, BOOT-04, BOOT-05, BOOT-06, BOOT-07, BOOT-08, BOOT-09, BOOT-10
**Success Criteria** (what must be TRUE):

  1. 싱가포르 `ap-southeast-1` 클라우드 프로젝트에 `0001`~`0006`이 순서대로 적용되고(`0005` 포함), 다른 워크스페이스 경로로 `sources` 버킷에 업로드를 시도하면 `storage.objects` 정책이 실제로 거부한다 — 경로 규약이 주석이 아니라 강제다
  2. Railway `asia-southeast1`의 `api`(web)와 `worker`(resident)가 **동일 이미지**로 기동하고, `/health`가 200을 반환하며, 로그 한 줄에 `job_id`/`workspace_id`가 컨텍스트로 붙어 나온다
  3. 저장소를 새로 클론한 상태에서 `uv sync` 한 번으로 `apps/api`·`apps/worker`·`packages/core`가 빌드되고, 포맷·린트를 어긴 커밋이 pre-commit에서 거부된다
  4. Next.js 15.5.22 이상 앱이 Tailwind 4 · TypeScript strict로 기동하고 Vitest가 통과한다 (CVE-2025-29927 하한 위)
  5. Railway↔Supabase 실측 RTT가 문서에 기록되고(open question #2 해소), 6자 비밀번호나 미확인 이메일로는 가입이 거부된다

**Plans**: 6/8 plans executed

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — [tracer] uv 워크스페이스 3멤버 + 공용 structlog 로깅 + api `/health`·`/health/ready` + worker SIGTERM 기동을 로컬에서 end-to-end 증명

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Supabase CLI 2.111.0+ 업그레이드와 `0005_storage.sql` 작성, 경로 규약을 `storage.objects` 정책으로 강제
- [x] 01-05-PLAN.md — Next.js 15.5.22 대시보드 스캐폴딩 (Tailwind 4 · TS strict · Vitest 2건)
- [x] 01-06-PLAN.md — 단일 Dockerfile 이미지 하나로 Railway `asia-southeast1`에 `api`·`worker` 배포, 동일 빌드 증명

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — 클라우드 선행 상태 확인 후 `0001`~`0006`을 `ap-southeast-1`에 번호 순서대로 push
- [x] 01-07-PLAN.md — pre-commit(ruff + prettier) · `.editorconfig` · 루트 README와 저장소 문서 경로 표기 정합

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 01-04-PLAN.md — Auth 하드닝 (최소 12자 · 이메일 확인 필수)을 로컬·클라우드 양쪽에 적용하고 두 거부를 증명
- [ ] 01-08-PLAN.md — 배포 환경 RTT 실측 문서화(p50/p95/콜드/×5)와 `checklists.json` open question #2 해소

### Phase 2: Security Spine and Shared Domain

**Goal**: 테넌트 격리가 코드 규약이 아니라 **역량 부재**로 강제되고, 라우터를 쓰기 전에 DB 트랜스포트와 공용 토크나이저가 확정된다
**Depends on**: Phase 1
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05, SEC-06, DOM-01, DOM-02, DOM-03, DOM-04, DOM-05, DOM-06, DOM-07, DOM-08, DOM-09
**Success Criteria** (what must be TRUE):

  1. worker 밖의 코드가 service key에 **닿을 수 없다** — `ApiSettings`에 필드 자체가 없고, ruff banned-api와 CI가 `db/service` import를 빌드 실패로 막으며, 클라이언트 번들 grep에 secret 키가 걸리지 않는다
  2. 다른 워크스페이스의 행을 수정·삭제하려는 애플리케이션 경로 시도가 조용한 0행이 아니라 403으로 돌아오고, 그 매핑이 라우터마다가 아니라 `UserDb` 한 곳에 있다
  3. GUC를 세팅한 실제 5채널 쿼리를 돌린 스파이크로 DB 트랜스포트가 결정·기록되고(`create function ... SET hnsw.iterative_scan`이 RPC로 실제 적용되는지가 판정 기준), 마이그레이션 `0007`이 그 결정에 맞춰 검색 함수·`jobs_dedup_idx`·`complete_job_and_chain()`·`verified_by`/`verified_at`/`expires_at`·`embedding_version`/`chunker_version`을 추가한다
  4. NFC·NFD·전각으로 각각 입력한 같은 한국어 문장이 `packages/core`의 **단일** 토크나이저를 거쳐 서로를 검색해내고, `tsv_tokenizer_version`이 정규화 형식까지 인코딩한다
  5. 워커가 `noop` 잡을 claim→complete로 통과시키고 SIGTERM에 진행 중인 잡을 잃지 않고 종료하며, 같은 `title`이 항상 같은 슬러그를 내고, `reap_stale_jobs` 타임아웃이 추측이 아니라 실측 p99로 설정된다

**Plans**: TBD

### Phase 3: Ingest and Compile Pipeline

**Goal**: 투입한 소스가 워커 잡 체인을 거쳐 링크되고 임베딩된 위키 페이지가 되며, 그 과정이 비용 상한 안에서 사용자에게 보인다
**Depends on**: Phase 2
**Requirements**: ING-01, ING-02, ING-03, ING-04, ING-05, ING-06, ING-07, COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, COMP-06, COMP-07, COMP-08, OPS-01
**Success Criteria** (what must be TRUE):

  1. 파일·URL·텍스트를 투입하면 요청이 즉시 `202`와 잡 식별자로 돌아오고(블로킹 작업이 요청 안에서 돌지 않음), 같은 파일을 다시 넣으면 "이미 수집됨 — 건너뜀"이 **눈에 보이게** 표시된다
  2. 원본 파일이 `{workspace_id}/{raw_source_id}/{filename}`에 보존되고, 스캔본처럼 추출 품질이 임계값 미달인 문서는 조용히 빈 채로 수집되는 대신 `needs_ocr` 사유와 함께 실패한다
  3. 소스 하나가 `parse → compile → link_sync → embed` 체인을 통과해 위키 페이지·`wiki_links`(미해결 타깃은 레드 링크)·위키와 원문 양쪽 임베딩을 만들고, 재처리 결과가 더 적은 단위로 줄어들어도 잔여 행이 남지 않으며, 스키마를 어긴 LLM 출력은 검증 오류를 되먹인 재시도로 복구되고 Python enum과 DB CHECK 불일치는 기동 시점에 즉시 실패한다
  4. 월 비용 상한을 넘긴 워크스페이스의 인큐가 **인큐 시점에** 거부되고, 진행 중인 잡을 취소할 수 있으며, `usage_events`에 토큰과 비용이 남는다
  5. 사용자가 소스별 잡 진행을 실제 단계 이름으로 확인하고 `dead` 잡을 재시도할 수 있으며, `jobs.last_error`에 provider 원문 예외가 그대로 노출되지 않는다

**Plans**: TBD

### Phase 4: Hybrid Retrieval and Fusion

**Goal**: 질문 하나가 5채널을 거쳐 **측정 가능하게** 옳은 근거 집합을 돌려준다
**Depends on**: Phase 3
**Requirements**: RTV-01, RTV-02, RTV-03, RTV-04, RTV-05, RTV-06, RTV-07, RTV-08, RTV-09
**Success Criteria** (what must be TRUE):

  1. 한국어·영어·혼합 30~50문항 골든 질의 세트가 먼저 존재하고, 그것으로 채널별 가중치·`k`·limit(전부 Python 정책 계층)과 `relaxed_order` 대 `strict_order` 선택이 근거와 함께 기록된다 — 튜닝 결정이 반증 가능해진다
  2. 검색이 2웨이브로 동작한다 — 채널 1~4 동시 실행 후 RRF, 그 결과를 seed로 채널 5(depth ≤ 2 · fan-out 상한 · 사이클 가드) 실행 후 재융합. 그래프 채널은 골든 세트로 가치가 입증될 때까지 기본 비활성 플래그 뒤에 있다
  3. 한 채널이 죽어도 요청이 실패하지 않고, 빠진 채널이 응답 `meta`에 보고된다
  4. 응답마다 채널별 기여도(`channel_hits`)와 `returned < requested_k`가 1급 메트릭으로 기록되어, 벡터 채널이 `ef_search`·`max_scan_tuples` 한계로 조용히 부족하게 돌아오는 것이 관측된다
  5. `EXPLAIN` 회귀 테스트가 HNSW 인덱스 스캔 사용을 단언해, 플래너가 조용히 seq scan으로 이탈하는 것을 잡아낸다

**Plans**: TBD

### Phase 5: Citation Integrity and Answer APIs

**Goal**: 답변이 **실제로 사용한** 근거만 인용하고 위키와 원문 양쪽으로 추적된다 — 이 제품의 핵심 가치가 여기서 살거나 죽는다
**Depends on**: Phase 4
**Requirements**: CITE-01, CITE-02, CITE-03, CITE-04, CITE-05, CITE-06, API-01, API-02, API-03, API-04, QC-01, QC-02
**Success Criteria** (what must be TRUE):

  1. 인용 앵커가 서버 발급 짧은 별칭(`[[src:s3]]`)으로 주입되고 서버가 실제 id로 해소하며, `double_citation`이 검색 결과가 아니라 **모델이 파싱된 앵커로 실제 인용한 것**의 교집합으로 구성된다 (`double_citation` 길이가 항상 `k`와 같으면 실패다)
  2. 발급되지 않은 앵커는 조작으로 간주해 제거·카운트되고, 앵커가 하나도 없으면 "근거를 찾지 못했습니다"가 명시적으로 반환된다
  3. `dual_citation_rate`·`unsourced_sentence_ratio`·`fabricated_anchor_count`·`cited_anchor_count`가 응답마다 측정되고, 소스가 위조한 `[[...]]` 앵커는 수집 시점에 이미 제거되어 프롬프트에 도달하지 않는다
  4. Ask 엔드포인트가 POST + `ReadableStream`으로 `meta` → `delta*` → `citations` → `done` 순서로 스트리밍하고, 상황별 `ask` 프롬프트 템플릿을 골라 질문할 수 있으며, 답변 언어가 질문 언어를 따른다
  5. 위키·소스·그래프·잡 상태를 읽을 수 있고, 충돌한 지식이 `disputed`로 표시되며, 검증 상태 전이가 **누가·언제·언제까지**를 남긴다

**Plans**: TBD

### Phase 6: Dashboard

**Goal**: 사용자가 브라우저만으로 워크스페이스를 운영한다 — 소스 투입부터 이중 Citation 답변까지
**Depends on**: Phase 2 (셸·인증은 Phase 3와 병렬 시작 가능), Phase 5 (Ask UI에 필요)
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, UI-06
**Success Criteria** (what must be TRUE):

  1. 로그인 후 `/w/[workspaceId]`가 테넌시의 단일 진실 소스로 동작하고(`middleware.ts`가 유일한 쿠키 기록자), 워크스페이스를 전환하고 이메일로 멤버를 초대해 3역할을 부여할 수 있다
  2. 드롭존에 소스를 놓으면 잡 체인 진행이 불확정 스피너가 아니라 **실제 단계 이름**으로 보여, 4분짜리 컴파일이 멈춘 것처럼 보이지 않는다
  3. Ask UI에서 인용 마커가 근거가 되는 절 옆에 인라인으로 붙어 스트리밍 중 제자리에서 해소되고, 카드가 컴파일된 위키 페이지와 원문의 `char_start`/`char_end` 하이라이트를 함께 보여주며, 근거 없음 상태가 시각적으로 구분된다
  4. 위키 뷰어가 읽기 전용임을 명시하고("이 페이지는 컴파일됩니다") WikiLink 내비게이션·레드 링크("아직 작성되지 않음 · 지금 생성")·상태 콜아웃을 제공한다
  5. Cytoscape 지식 캔버스가 렌즈 필터(`wiki_pages.category` 재사용)와 함께 동작하고, PostgREST 1000행 상한에서 조용히 잘리지 않는다 (이 페이즈에서 **가장 마지막** 표면)

**Plans**: TBD
**UI hint**: yes

### Phase 7: Integration and Ops Baseline

**Goal**: 조각들이 실제로 함께 동작함이 증명되고, 품질·비용·격리에 이후 회귀를 판정할 기준선이 생긴다
**Depends on**: Phase 6
**Requirements**: OPS-02, OPS-03, OPS-04, OPS-05, OPS-06
**Success Criteria** (what must be TRUE):

  1. 빈 워크스페이스에서 시작해 수집 → 컴파일 → 임베딩 → 검색 E2E 시나리오가 통과한다
  2. 같은 `content_hash` 재투입이 행을 늘리지 않고, **더 적은 단위로 줄어드는 축소 재처리**에서도 잔여 행이 남지 않는다
  3. 애플리케이션 경로 전수(읽기·쓰기·잡·Storage)의 교차 테넌트 시도가 차단됨이 스위트로 확인된다
  4. 골든 세트 기준 검색 품질과 채널별 지연 기준선이 기록되어, 이후 변경이 회귀인지 개선인지 판정할 수 있다
  5. 워크스페이스별 LLM/임베딩 비용과 잡 파이프라인 상태가 관측 가능해, 비용이 새는 것을 청구서가 아니라 대시보드에서 먼저 본다

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

**Parallelization note:** Phase 2의 워커 스켈레톤(DOM-08)이 끝나면 백엔드 트랙(3 → 4 → 5)과
프론트엔드 셸(6의 UI-01/UI-02/UI-03)이 병렬로 진행 가능하다. 두 트랙은 Ask UI(UI-04)에서 만난다.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Bootstrap and Ground Truth | 6/8 | In Progress|  |
| 2. Security Spine and Shared Domain | 0/TBD | Not started | - |
| 3. Ingest and Compile Pipeline | 0/TBD | Not started | - |
| 4. Hybrid Retrieval and Fusion | 0/TBD | Not started | - |
| 5. Citation Integrity and Answer APIs | 0/TBD | Not started | - |
| 6. Dashboard | 0/TBD | Not started | - |
| 7. Integration and Ops Baseline | 0/TBD | Not started | - |

## Coverage

v1 requirements: 73 (BOOT 10 · SEC 6 · DOM 9 · ING 7 · COMP 8 · RTV 9 · CITE 6 · API 4 · QC 2 · UI 6 · OPS 6)
Mapped: 73/73 ✓ — orphan 없음, 중복 배정 없음

이미 적용·검증이 끝난 데이터 계층(마이그레이션 `0001`~`0004`, `0006`)은 PROJECT.md의 Validated에 있으며
이 로드맵의 어떤 페이즈도 그것을 다시 만들지 않는다. v1에 남은 스키마 작업은 `0005`(Phase 1)와
`0007`(Phase 2) 둘뿐이다.

---
*Roadmap created: 2026-08-02*
