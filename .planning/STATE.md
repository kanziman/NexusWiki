---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 4
current_phase_name: Hybrid Retrieval and Fusion
status: executing
stopped_at: Phase 4 context gathered
last_updated: "2026-08-10T22:30:50.590Z"
last_activity: 2026-08-10
last_activity_desc: Phase 03 complete, transitioned to Phase 4
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 31
  completed_plans: 27
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-01)

**Core value:** 질문에 대한 답이 원문 청크와 컴파일된 위키 페이지 양쪽으로 추적 가능해야 한다
**Current focus:** Phase 03 — ingest-and-compile-pipeline

## Current Position

Phase: 4 — Hybrid Retrieval and Fusion
Plan: Not started
Status: Ready to execute
Last activity: 2026-08-10 — Phase 03 complete, transitioned to Phase 4

Progress: [██████████] 100% (execution; verification pending)

## Performance Metrics

**Velocity:**

- Total plans completed: 27
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 9 | - | - |
| 02 | 9 | - | - |
| 03 | 9 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 15 min | 3 tasks | 20 files |
| Phase 01 P02 | 30min | 3 tasks | 3 files |
| Phase 01 P05 | 14min | 3 tasks | 16 files |
| Phase 01 P06 | 3h | 3 tasks | 6 files |
| Phase 01 P03 | 1d | 3 tasks | 2 files |
| Phase 01 P07 | 12 min | 3 tasks | 21 files |
| Phase 01 P04 | 3h 17m | 3 tasks | 3 files |
| Phase 01 P08 | 15 min | 3 tasks | 5 files |
| Phase 02 P01 | 1h 5m | 3 tasks | 6 files |
| Phase 02 P02 | 45min | 4 tasks | 17 files |
| Phase 02 P05 | 25min | 3 tasks | 5 files |
| Phase 02 P03 | 35min | 3 tasks | 10 files |
| Phase 02 P06 | 1h | 3 tasks | 7 files |
| Phase 02 P04 | 55min | 3 tasks | 8 files |
| Phase 02 P07 | 12min | 3 tasks | 9 files |
| Phase 02 P08 | 35min | 3 tasks | 7 files |
| Phase 03 P01 | 15m | 3 tasks | 7 files |
| Phase 03 P02 | 25m | 3 tasks | 6 files |
| Phase 03 P03 | 20m | 2 tasks | 7 files |
| Phase 03 P05 | 1h | 3 tasks | 10 files |
| Phase 03 P06 | 1h | 3 tasks | 10 files |
| Phase 03 P07 | 35m | 3 tasks | 4 files |
| Phase 03 P09 | 45m | 3 tasks | 12 files |
| Phase 03 P08 | 1h | 3 tasks | 14 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: DB 레이어(`0001`~`0004`, `0006`)는 Validated — 로드맵이 재구현하지 않음. v1에 남은 스키마는 `0005`(Phase 1)와 `0007`(Phase 2)뿐
- [Roadmap]: 리전은 싱가포르 양쪽 확정 (Railway에 서울·도쿄 없음). Supabase 프로젝트 생성 후 변경 불가 → Phase 1 P0
- [Roadmap]: RTV-06 골든 질의 세트를 ops에서 retrieval(Phase 4)로 이동 — 가중치·`k`·청크 크기·그래프 채널 가치를 판정하는 전제 조건
- [Roadmap]: OPS-01(`usage_events` + 인큐 시점 비용 상한)을 첫 LLM 호출과 같은 페이즈(3)에 배치
- [Roadmap]: UI-06 Cytoscape 캔버스는 Phase 6의 마지막 표면 (연구 3건이 독립적으로 최저 우선순위 결론)
- [Phase 01]: Storage 경로 파서는 UUID/UUID/파일명 형식만 허용하고 나머지는 null로 거부한다. — D-05: 잘못된 UUID를 22P02 서버 오류가 아닌 정책 거부로 처리한다.
- [Phase 01]: sources 객체에는 UPDATE 정책을 만들지 않아 사용자 원본 덮어쓰기를 차단한다. — D-07: content_hash 멱등성과 원본 추적성을 유지한다.
- [Phase 01]: Railway api/worker는 단일 Dockerfile을 공유하고 worker만 Custom Start Command를 사용한다. — 동일 코드 런타임 경계를 유지한다.
- [Phase 01]: Railway 개별 빌드 다이제스트가 다르면 커밋 SHA·Dockerfile 경로·런타임 GIT_SHA 3항 일치로 동일 빌드를 판정한다. — SPEC R8 2차 판정.
- [Phase 01]: State A was proven, so push-clean was selected instead of recreating the project. — Both the migration ledger and target public schema were empty immediately before the one-way push.
- [Phase 01]: Auth 하드닝은 로컬 config.toml과 Supabase Cloud에 각각 적용하고 실제 Cloud HTTP 동작으로 판정한다. — 로컬 설정은 프로덕션 설정을 바꾸지 않으므로 양쪽 적용과 동작 검증이 모두 필요하다.
- [Phase 01]: Auth 검증 계정은 성공·실패 경로 모두 trap으로 삭제하며 검증 스크립트는 개발자 머신에서만 실행한다. — Admin secret 사용 범위와 잔존 테스트 계정 위험을 동시에 제한한다.
- [Phase 01]: RTT는 콜드 요청을 분리하고 워밍업 5회 뒤 성공 표본 50회의 최근접 순위 p50/p95를 기록한다. — 콜드 연결 비용이 정상 왕복 백분위를 오염하지 않도록 한다.
- [Phase 01]: 배포 환경 RTT는 새 라우터 대신 worker 기동 경로에서 측정한다. — SPEC 경계를 지키면서 실제 Railway 네트워크 경로를 관측하는 D-14 결정이다.
- [Phase 02]: DB 트랜스포트는 rpc(SECURITY INVOKER + 요청자 JWT) — 스파이크 실측이 결정. `create function ... SET hnsw.*`가 Supabase RPC로 실제 적용됨을 강제 HNSW 계획에서 확인
- [Phase 02]: D-03의 기계적 3조건 규칙은 실제 질의 형태에서 변별력이 없다 — 두 트랜스포트가 노드 단위 동일 플랜을 내며 조건 2의 실패 원인은 플래너 비용(btree+sort 233 vs HNSW 349,657)
- [Phase ?]: [Phase 02] git SHA·PORT는 설정이 아니라 배포 메타데이터로 nexuswiki_core.deployment가 읽는다 — D-10의 기동 실패 규칙이 빌드 메타데이터까지 번지지 않게 한다
- [Phase ?]: [Phase 02] uvicorn을 factory 모드로 전환하고 모듈 레벨 app 객체를 제거 — api.main import가 프로덕션 환경 전체를 요구하지 않게 한다
- [Phase ?]: [Phase 02] pytest import-mode를 importlib으로 고정 — 워크스페이스 멤버 간 test 모듈 basename 충돌로 수집이 깨지는 것을 막는다
- [Phase ?]: 큐 RPC 헬퍼에는 workspace_id를 요구하지 않는다 — 쓰이지 않는 인자가 되어 격리를 강제하는 척만 하게 되므로, 허용 목록과 분류 테스트로 대체 (02-03)
- [Phase ?]: UserDb는 workspace_id를 강제하지 않고 match 조건을 필수로 요구한다 — 이 경로의 격리 수단은 RLS다 (02-03)
- [Phase ?]: 42501이 아닌 SQLSTATE는 403으로 뭉개지 않는다 — 진짜 장애가 격리 위반으로 위장되는 것을 막는다 (02-03)
- [Phase ?]: [Phase 02] 0007 섹션 8이 9개 테이블 × 3개 롤 최소권한 매트릭스로 권한 공백을 닫았다 — anon 무권한, grant all 없음, RLS를 우회하는 TRUNCATE도 함께 회수 (02-06)
- [Phase ?]: [Phase 02] wiki_pages의 verified CHECK를 걸지 않았다 — verified_by의 on delete set null이 CHECK를 위반해 계정 삭제가 23514로 실패한다. 세 컬럼 동시 기록은 P2-QC-01의 책임 (02-06)
- [Phase ?]: [Phase 02] 마이그레이션을 단일 트랜잭션으로 감싸는 관례를 0007에서 시작 — 부분 적용이 남기는 '스키마는 바뀌었는데 권한이 없는' 상태를 구조적으로 불가능하게 만든다 (02-06)
- [Phase ?]: [Phase 02] 검색 함수는 search_chunks 1채널만 0007에 넣었다 — 나머지 4채널은 융합 가중치가 정해지는 Phase 4의 일이며 지금 고정하면 0008·0009로 되돌아온다 (02-06)
- [Phase ?]: [Phase 02] 교차 테넌트 쓰기를 막는 술어가 workspaces에서 두 겹이다 — SELECT 정책과 UPDATE 정책이 각각 독립으로 막으므로 하나만 푸는 fail-first는 green으로 통과한다 (02-04)
- [Phase ?]: [Phase 02] 격리 테스트 픽스처는 접속 정보를 env가 아니라 상수+루프백 가드로 묶는다 — .env.local이 클라우드 자격증명을 담고 있어 env를 읽으면 운영 프로젝트에 사용자를 만들고 지운다 (02-04)
- [Phase ?]: [Phase 02] 미인증 요청의 401은 FastAPI HTTPBearer가 낸다 — 라우터에 상태 코드를 두지 않으면서 미인증과 격리 위반을 다른 응답으로 유지하는 유일한 방법 (02-04)
- [Phase ?]: 미등록 job type의 즉시 dead는 0003/0007의 SQL 표면으로는 불가능하다 — dead는 attempts >= max_attempts로만 도달한다. fail_job(backoff=0)으로 대기 없이 수렴시키고, 한 번에 보내려면 0008의 dead_letter_job()이 필요하다
- [Phase ?]: 0행 composite RPC는 PostgREST에서 all-null 레코드로 돌아온다 — ServiceDb._rpc가 이것을 None으로 정규화한다. 정규화가 없으면 at-least-once 재호출 no-op이 성공으로 기록된다
- [Phase ?]: [Phase 02] 큐 기준선의 측정 구간은 claim→complete이며 인큐는 구간 밖이다 — reap_stale_jobs가 보는 나이가 locked_at 기준이고 그것은 claim 시점에 찍히므로 인큐 대기는 타임아웃이 덮을 구간이 아니다 (02-08)
- [Phase ?]: [Phase 02] 성공 표본 200 미만이면 p99를 계산하지 않고 None으로 둔다 — 최근접 순위 p99가 사실상 최댓값이 되어 이름이 근거 없는 신뢰를 준다. 시도는 220회로 두어 실패 여유를 확보했고 실제로 1회 소진됐다 (02-08)
- [Phase ?]: [Phase 02] 잠정 reap 타임아웃 2초를 유도했으나 reap_stale_jobs 기본 15분은 바꾸지 않는다 — 2초는 noop 전용 큐의 하한이며 Phase 3 컴파일 잡에 적용하면 전부 이중 처리된다 (02-08)
- [Phase ?]: [Phase 02] 전송 p99 127ms는 15분의 0.0141%다 — 이 데이터는 15분을 반박도 지지도 하지 못하고 정당화 후보 하나(전송 비용 감안)를 제거할 뿐이다. reap 타임아웃을 정하는 것은 전송이 아니라 핸들러 지속시간이다 (02-08)
- [Phase ?]: 0008: 임베딩 차원 1024 — 함수 인자 typmod는 저장되지 않으므로 차원 계약은 행동으로 단언한다
- [Phase ?]: D-08 CI 요구를 소스 수준 토큰 게이트로 이행 — 러너에 Supabase 스택을 세우지 않는다
- [Phase ?]: 0009: 인큐 권한 모델은 security definer RPC — jobs에 INSERT 정책을 주면 그 경로가 비용 상한을 건너뛴다 (D-P1)
- [Phase ?]: 0009: 비용 단위는 micro-dollar 정수(bigint), 기본 상한 $5.00/월/워크스페이스 — open question 해소 (D-P2)
- [Phase ?]: 0009: 취소는 jobs.status에 canceled를 더하고 running 잡은 협조적 — CHECK는 파일 번호와 달리 되돌릴 수 있다 (D-P3)
- [Phase ?]: 0009: 새 함수 revoke에 service_role을 명시하는 것이 관례 — 클라우드 pg_default_acl이 로컬보다 넓다
- [Phase ?]: 03-03: 청크 토큰은 tiktoken cl100k_base로 센다 — bge-m3의 XLM-R SentencePiece를 의도적으로 근사하며 과대평가 방향이라 8192 예산을 넘길 위험이 구조적으로 없다 (D-P4)
- [Phase ?]: 03-03: 청킹 초기값 목표 512토큰·오버랩 64토큰 — 문헌 근거 없는 경험적 출발점이며 Phase 4 골든 세트(RTV-06)가 반증할 대상. 상수로 노출해 반증 가능하게 둔다 (D-P5)
- [Phase ?]: 03-03: 오버랩은 예산과 무관하게 마지막 조각 하나를 반드시 겹친다 — 예산으로만 되돌리면 문단 조각이 64토큰보다 커서 산문에서 오버랩이 조용히 0이 된다
- [Phase ?]: 03-03: 청크 내용은 조각을 이어붙이지 않고 원문에서 다시 잘라 넣는다 — ING-05의 좌표 왕복 속성이 성립하는 유일한 구조적 이유
- [Phase ?]: 03-03: enum 대조 테스트는 마이그레이션 SQL을 실제로 읽어 CHECK 리터럴을 뽑는다 — 파이썬 리터럴끼리 비교하면 베껴 적기가 검증을 통과한다
- [Phase ?]: 03-03: 페이지 수준 축소 재처리는 페이지 삭제가 아니라 sources 역참조 제거 — 한 페이지를 여러 raw_source가 만들 수 있고 삭제는 남의 링크를 레드로 되돌린다 (D-P6, 구현은 03-04/03-08)

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1] `0005`(Storage)는 첫 클라우드 `db push` **이전에** 적용해야 함 — 이미 적용된 `0006`보다 번호가 낮아 이후에 넣으면 로컬/클라우드 순서가 어긋남
- [Phase 1] 2025-11 이후 생성 프로젝트에는 legacy 키가 발급되지 않음 — `sb_publishable_`/`sb_secret_` 체계로 시작해야 함
- [해소 2026-08-06] [Phase 2] DB 트랜스포트 — `create function ... SET hnsw.iterative_scan`이 Supabase RPC로 **실제 적용됨**을 실측 확인(강제 HNSW 계획에서 GUC 3종 · HNSW Index Scan · k=20 전부 충족). RPC 채택으로 잠금 — `checklists.json > decisions.db_transport`, `docs/ops/db-transport-spike.md`
- [Phase 2] `0003`의 `jobs`에 하트비트 가능 컬럼이 있는지 미확인 — 없으면 컴파일을 더 작은 잡으로 분할 (워커 루프 작성 전 확인)
- [Phase 3] 한국어 청킹 파라미터는 문헌 없음 — 실측 튜닝 대상. PDF 품질 게이트 임계값은 실제 픽스처(스캔본·다단·표 위주) 필요
- [Phase 2] authenticated·service_role이 public 9개 테이블에 arwd(SELECT/INSERT/UPDATE/DELETE) 권한을 하나도 갖고 있지 않음 — pg_default_acl이 Dxtm만 부여. RLS는 이미 가진 권한을 좁힐 뿐이므로 0004의 정책 20여 개가 현재 무력하고 요청자 JWT 경로·service_role 워커 경로 모두 42501로 떨어진다. 영구 조치를 0007(02-06-PLAN)에 반영할 것
- [Phase 2] WorkerSettings의 secret 4종 + LLM_MODEL이 필수 필드가 되어, Railway worker 서비스 env에 다섯 키가 모두 없으면 다음 배포에서 crash-loop으로 처음 드러난다 (api 서비스 env에는 secret 4종이 없어야 정상 — SEC-01)
- [Phase 2] 0007이 원격에 올라가 0007 이하 번호의 마이그레이션은 영구히 추가 불가 — 내용 변경은 0008 보정으로만. 섹션 7의 타입 변경은 다음에 되돌릴 때 실제 데이터가 있으므로 사실상 편도 (docs/ops/migration-0007-record.md §한계와 되돌리기)
- [Phase 2] 0007 섹션 8의 권한 매트릭스가 실제 경로에 대해 넓지도 좁지도 않은지는 미확인 — 라우터가 서는 02-04와 워커가 도는 Phase 3에서 처음 드러난다. 좁게 틀리면 42501로 소란스럽고 넓게 틀리면 조용하다
- [Phase 2] 새로 만드는 테이블은 pg_default_acl에서 다시 Dxtm(TRUNCATE 포함)을 물려받는다 — 테이블 추가 마이그레이션마다 0007 섹션 8의 revoke/grant 쌍을 반복할 것
- [Phase 2] 격리 왕복 증명은 workspaces 한 테이블·로컬 스택에 한정 — 나머지 8개 테이블과 Storage, 클라우드 왕복은 미확인. 전수 스위트는 Phase 7 OPS-04 (docs/ops/tenant-isolation-proof.md §한계)
- [해소 2026-08-07] [Phase 2] 02-08 Railway 실측 — 전 단계 완료. 측정값 p50 84.49 / p95 107.92 / p99 127.05ms (N=219, git_sha 60c1e80). 프로브 토글 2종은 `railway variable delete`로 제거하고 로그 부재로 확인(위협 T-02-47 종결), 프로브 워크스페이스는 삭제하고 `select count(*) from public.jobs` = 0 관측(위협 T-02-48 종결). 근거: `docs/ops/reap-timeout-baseline.md` §한계 4·5
- [Phase 3] 프로브성 잡을 다시 만들 일이 있으면 **처분 가능한 워크스페이스에 가두는 방식**을 다시 써야 한다 — `0007` 섹션 8이 `jobs`에 어느 롤에도 DELETE를 주지 않으므로(잡 이력이 곧 감사 기록) "각 왕복이 자기 잡을 지운다"는 권한 매트릭스가 바뀌지 않는 한 앞으로도 불가능하다
- [Phase 2] 02-09 Task 3(게이트)이 체크포인트로 중단됨 — 스크립트 2종과 워크플로우 4잡은 커밋됐고 로컬에서 위반 4종 red·clean tree exit 0까지 실측했으나, 원격 Actions 관측이 남았다. 필요한 것: (a) `ci-violation/service-import` 브랜치 — `apps/api/src/api/` 모듈에 `from worker.db.service import service_client` 한 줄 → PR에서 `service-usage` 잡 red와 위반 파일 경로 확인 (b) `ci-violation/bundle-secret` 브랜치 — dashboard 클라이언트 컴포넌트에 리터럴 한 줄(환경변수 참조는 번들에 안 남음) → PR에서 `bundle-secrets` 잡 red와 **파일 경로는 나오되 값은 안 나오는지** 확인 (c) 두 브랜치 삭제 후 정상 PR에서 4잡 green. 관측을 지어내지 않기 위해 docs/ops/ci-security-gate.md와 02-09-SUMMARY.md는 미작성 상태다
- [Phase 2] 미등록 job type의 즉시 dead 전이는 현재 SQL 표면으로 불가 — dead는 fail_job/reap_stale_jobs 양쪽에서 attempts >= max_attempts로만 도달하고 그 게이트를 건너뛰려면 jobs 직접 UPDATE가 필요하다(금지 경로). 02-07은 fail_job(backoff='0 seconds')로 대기 없이 수렴시켰다. 0008의 dead_letter_job()이 이 자리를 닫을 것
- 클라우드에서 service_role이 public.search_chunks EXECUTE를 갖는다 (pg_default_acl 로컬/클라우드 차이) — 0009의 revoke 한 줄로 정정 필요
- [Phase 3] chunk_text의 오버랩이 최소 조각 1개 단위라 청크가 조각 하나뿐일 때는 인접 청크가 겹치지 않고 맞닿는다 (실측 오버랩 min=0) — 인용 단위로서 문제가 되는지는 Phase 4 골든 세트가 판정한다
- [해소 2026-08-10] [Phase 3] 비용 상한 거부는 사용자 승인 A에 따라 `0010`의 프로젝트 전용 `NW402`와 `api.errors` 단일 HTTP 매핑으로 402가 된다. Postgres가 만들 수 없는 코드라 실제 DB 자원 오류를 예산 초과로 오인하지 않는다 (`03-05-SUMMARY.md`).
- [Phase 3] 03-07 예산 조회는 표시용(`authoritative: false`)이며, UTC 월 경계의 제한된 `usage_events` 합계는 인큐 가능 여부를 판정하지 않는다. 권위 있는 판정은 `enqueue_source_job` SQL 하나에 남는다 (D-P18).

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-08-10T22:08:45.897Z
Stopped at: Phase 4 context gathered
Resume file: .planning/phases/04-hybrid-retrieval-and-fusion/04-CONTEXT.md

**재개 시 첫 행동:** Phase 3 검증·완료 마킹을 실행한다. 실행 플랜 9/9가 끝났고, 03-08은
provider 마스킹·즉시 dead-letter·기동 enum↔DB CHECK 대조·축소 재처리·reap 근거를 닫았다.

⚠️ **보존할 워킹 트리 변경이 있다** — `.planning/config.json`, `checklists.json`, `.agents/`,
`.pnpm-store/`, `docs/architecture/`, `docs/design-systems/`는 이 플랜과 무관하다. 정리 명령으로
삭제하지 않는다.
