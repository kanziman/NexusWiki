---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Awaiting next milestone
stopped_at: Phase 7 complete — all evidence including browser-layout backstops verified
last_updated: "2026-08-13T05:21:34.012Z"
last_activity: 2026-08-13
last_activity_desc: Milestone v1.0 completed and archived
progress:
  total_phases: 7
  completed_phases: 7
  total_plans: 55
  completed_plans: 55
current_phase: 7
current_phase_name: Integration and Ops Baseline
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-13)

**Core value:** 질문에 대한 답이 원문 청크와 컴파일된 위키 페이지 양쪽으로 추적 가능해야 한다
**Current focus:** Planning next milestone — run `/gsd-new-milestone` to scope v1.1

## Current Position

Phase: Milestone v1.0 complete
Plan: —
Status: Awaiting next milestone
Last activity: 2026-08-13 — Milestone v1.0 completed and archived

## Performance Metrics

**Velocity:**

- Total plans completed: 55
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 9 | - | - |
| 02 | 9 | - | - |
| 03 | 9 | - | - |
| 04 | 9 | - | - |
| 05 | 7 | - | - |
| 6 | 8 | - | - |
| 7 | 4 | - | - |

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
| Phase 04 P04 | 12min | 3 tasks | 6 files |
| Phase 04 P05 | 5 min | 2 tasks | 7 files |
| Phase 04 P06 | 14 min | 2 tasks | 3 files |
| Phase 04 P09 | 5min | 2 tasks | 5 files |
| Phase 05 P01 | 35min | 2 tasks | 16 files |
| Phase 05 P02 | 25min | 2 tasks | 1 files |
| Phase 06 P01 | ~40min | 2 tasks | 16 files |
| Phase 06 P02 | 35min | 2 tasks | 5 files |
| Phase 06 P03 | ~20min (continuation) + earlier Task0/1/1b session | 3 tasks | 7 files |
| Phase 06 P04 | ~20min | 2 tasks | 4 files |
| Phase 06 P08 | ~2h | 3 tasks | 5 files |
| Phase 06 P05 | ~1h | 3 tasks | 6 files |
| Phase 06 P06 | ~35min | 3 tasks | 8 files |
| Phase 06 P07 | ~2h | 3 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table (updated at v1.0 milestone close). The full per-phase decision log below is v1.0 history — the phase docs it references are archived at `.planning/milestones/v1.0-phases/`.

<details>
<summary>v1.0 decision history (archived — click to expand)</summary>

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
- [Phase ?]: [Phase 04]: strict_order와 graph off는 유지하되 측정 근거는 없다 — `.claude/CLAUDE.md:21`·`0011:76,147` 제약과 RTV-07 안전 기본값에 따른 유지이며, 12/12/8행 코퍼스에서는 플래너가 HNSW를 고르지 않아 비교 자체가 T-04-12가 된다 (`docs/ops/hnsw-order-benchmark.md`)
- [Phase ?]: [Phase 04]: 검색 정책 변경은 POLICY_VERSION 상승 + 동일 corpus/golden/model 해시 위 before/after 레코드 쌍 + 리뷰어 승인을 모두 통과해야 채택된다 (`docs/ops/retrieval-policy-change-log.md`, 04-CONTEXT.md > D-08)
- [Phase ?]: [Phase 4] RTV-04 gap closure: _pins() now includes git_sha as a comparator pin; compare_order_records() asserts a distinct {strict_order, relaxed_order} pair. v5 strict/relaxed evidence pair (one identical commit) is now the valid comparability evidence; v4 pair marked superseded-invalid, preserved byte-for-byte.
- [Phase ?]: [Phase 4] Relaxed-order arm again shows zero vector-channel hits in the v5 record (measured from one pinned revision, not a runner-mismatch artifact) — reinforces keeping strict_order as default; root cause investigation is out of scope for this gap-closure plan.
- [Phase ?]: [Phase 5] Starlette sends http.response.start before iterating a StreamingResponse body — auth/rate-limit checks needing a clean HTTP status must run in a plain coroutine awaited before StreamingResponse is constructed, never inside the generator that becomes its body_iterator (05-01)
- [Phase ?]: [Phase 5] AskService.ask() stays one all-in-one async generator (retrieve + evidence-check + LLM streaming) because none of its internal failure paths need a non-200 top-level status — router-level query-length pre-check + Pydantic requested_k bound matching DEFAULT_RETRIEVAL_POLICY mean retrieve() never raises inside the generator (05-01)
- [Phase ?]: [Phase 5] ask 템플릿 인용 표기는 4종의 서로 다른 문구를 문자열 치환하지 않고 append로 교정한다 — 가장 최근 지시가 우선하는 성질을 이용해 D-02 별칭 스킴을 강제 (05-02)
- [Phase ?]: [Phase 5] wiki_graph_neighborhood는 expand_wiki_graph를 재사용하지 않고 새로 만든다 — Phase 4 검색-융합 정책과 API-04 그래프 읽기는 서로 다른 소비자이므로 독립 버전으로 분리 (05-02, D-07.1/D-11)
- [Phase ?]: [Phase 5] hnsw.* GUC을 설정하는 함수가 있는 마이그레이션은 supabase db push 단독 세션에서 실패하지 않도록 파일마다 pgvector 워밍업 쿼리를 필요로 한다 — db reset은 이전 마이그레이션이 이미 세션을 데워서 이 버그를 가린다 (05-02)
- [Phase ?]: [Phase 5] CITE-06은 파일·URL·텍스트 분기마다가 아니라 parse.py에서 최종 content가 합류한 직후, chunk_text() 전에 전체 텍스트에 한 번 적용한다 — 청크 경계에 걸친 위조 앵커도 구조적으로 제거하고 ING-05 offset은 정제된 content 기준으로 보존한다 (05-03)
- [Phase ?]: [Phase 5] template_id는 요청자 JWT/RLS로 읽힌 행만 우선 사용하고 빈 결과는 기본 템플릿 조회 체인으로 폴백한다 — foreign/missing id를 구별하지 않아 템플릿 존재 여부를 노출하지 않는다 (05-03)
- [Phase ?]: [Phase 6] window.location.assign 대신 router.push를 쓰면 signInWithPassword 직후 RSC soft-navigation이 방금 쓴 세션 쿠키보다 먼저 도착할 수 있다 — 전체 네비게이션으로 구조적으로 제거 (06-01)
- [Phase ?]: [Phase 6] docs/design-systems/design-tokens.css/.json을 이번에 처음 git에 커밋 — 이전 세션 산출물이 미추적 상태였고 Phase 6 전체가 이 파일 존재를 전제한다 (06-01)
- [Phase ?]: [Phase 6] Tailwind 4 @theme 색상 키는 design-tokens.css의 동일 이름 커스텀 프로퍼티를 var()로 셀프 참조 — CSS Cascade Layers가 unlayered 선언에 무조건 우선순위를 주므로 순환 참조가 되지 않고 원본 값으로 정확히 해석됨을 실측 확인 (06-01)
- [Phase ?]: [Phase 6] NavShell 로딩 backstop은 useTransition()이 router.push()를 감싸는 방식으로 구현 — 별도 isLoading state 없이 Next.js App Router의 라우트 전환 신호를 그대로 쓴다 (06-02)
- [Phase ?]: [Phase 6] jsdom은 Pointer Capture/scrollIntoView/ResizeObserver를 구현하지 않는다 — vitest.setup.ts에 전역 폴리필을 추가해 이후 모든 Phase 6 Radix 컴포넌트 테스트가 공유하게 했다 (06-02)
- [Phase ?]: [Phase 6] invite_workspace_member의 RETURNS TABLE 출력 컬럼(user_id/email/role)이 plpgsql 본문에서 암묵적 변수로 스코프에 들어와, 같은 이름의 바닥 컬럼 참조(auth.users.email, ON CONFLICT (workspace_id,user_id))가 ambiguous로 죽는다 — 테이블 별칭 + ON CONFLICT ON CONSTRAINT로 회피 (06-03)
- [Phase ?]: [Phase 6] Tailwind max-w-*/w-*/h-* 유틸리티가 이 프로젝트의 커스텀 --spacing-{xs,sm,base,lg,xl,xxl,section} @theme 오버라이드와 이름이 겹치면 Tailwind 기본 --container-* 대신 --spacing-*로 잘못 해석된다(실측: max-w-xl -> 32px) — 겹치는 크기 유틸리티는 인라인 style로 대체 (06-03, WINDOWS #11)
- [Phase ?]: [Phase 6] MembersList는 owner 자신의 행에 제거 버튼을 그리지 않는다 — protect_owner_membership 트리거(0004)가 owner 자기 삭제를 DB 레벨에서 거부하므로 클릭만 되고 항상 실패하는 버튼을 만들지 않는다 (06-03)
- [Phase ?]: [Phase 6] apps/dashboard/lib/api-client.ts의 ApiError.extra는 errors.py의 body 필드를 개별 화이트리스트하지 않고 detail 제외 나머지 전부로 일반화 — 새 필드가 추가돼도 클라이언트를 따로 고칠 필요가 없다 (06-04)
- [Phase ?]: [Phase 6] lib/sse.ts의 파일 헤더 주석은 ask.py/AskConversation.tsx를 직접 인용하지 않는다 — Task 2 자신의 grep 기반 수용기준(generic 모듈 검증)과 충돌하므로 06-PATTERNS.md 인용으로 대체 (06-04)
- [Phase ?]: GraphLensFilter.tsx는 Task 2 <action>이 요구한 그대로 workspaceId를 받되 URL 파라미터 구성 자체에는 쓰지 않는다 — pathname이 이미 workspaceId를 포함하므로 prop은 API 계약 일치용
- [Phase ?]: Cytoscape 카테고리 색상은 selector 기반 스타일 규칙(node[category = "x"])으로 구현 — 스타일 값 함수 매퍼보다 타입 마찰이 적고 cytoscape.js 표준 관용구에 더 가깝다
- [Phase ?]: GraphCanvas.tsx는 RSC page.tsx가 아니라 컴포넌트 자신이 클라이언트에서 직접 fetch한다 — ?category= 재선택마다 풀 네비게이션 없이 재조회하기 위해서이며 Phase 6의 다른 표면과 의도적으로 다른 지점
- [Phase ?]: [Phase 6] JobStepper의 5단계 헤더 캡션은 jobs.py STEP_LABELS와 별개의 D-05 verbatim 고정 문구다 — STEP_LABELS는 dead 에러 템플릿에만 소비 (06-05)
- [Phase ?]: [Phase 6] Dropzone.onIngested는 (jobId, rawSourceId) 2-arg 고정 시그니처라 SourcesList는 전체 재조회 대신 단일 행 targeted select로 prepend한다 (06-05)
- [Phase ?]: [Phase 6] Radix Tabs는 activationMode=automatic이라 jsdom 테스트에서 fireEvent.click이 아닌 userEvent.click으로 탭을 전환해야 한다 (06-05)
- [Phase ?]: [Phase 6] AskConversation의 citations 프레임(또는 스트림 종료 시점의 부재)만 턴의 최종 렌더를 결정한다 — done 프레임은 상태 전이에 관여하지 않는다. citations 이후 done 직전 네트워크가 끊겨도 이미 완결된 답변을 dropped로 되돌리지 않기 위해서다 (06-06)
- [Phase ?]: [Phase 6] CitationSidePanelProps에 선택적 workspaceId를 추가했다 — Task 3 <action>이 요구하는 위키 카드 링크(/w/[workspaceId]/wiki/[slug])는 {part,onClose} 2필드만으로는 구성 불가능하다 (06-06, Rule 2)
- [Phase ?]: [Phase 6] baseSlug()/normalize()는 nexuswiki_core.slug._base_slug/tokenizer.normalize의 근사 포팅이다 — 충돌 접미(-2) 해소와 정확한 casefold는 재현하지 않는다(안전한 실패, 06-07)
- [Phase ?]: [Phase 6] 위키 뷰어의 disputed 콜아웃은 verification_status와 무관하게 항상 본문보다 먼저 렌더링된다 — 파일/DOM 순서 구조적 보장 (T-06-22, 06-07)
- [Phase ?]: [Phase 6] canVerify는 has_workspace_role RPC 우선, workspace_members 직접 읽기로 폴백해 서버에서 판정한다 — 실제 쓰기 경계는 wiki.py RLS다 (T-06-21, 06-07)
- [Phase ?]: [Phase 6] 06-07 라이브 Playwright 검증은 두 차례 중단되어 정적 검증(vitest/tsc/next build)만으로 대체 — WINDOWS.md #12로 추적, Phase 6 6개 요구사항(UI-01~06) 전부 완료
- [Phase ?]: worker/db/service.py의 _rpc()가 PostgREST의 204 No Content(returns void RPC)를 처리하지 않아 lexical 색인 호출에서 JSONDecodeError로 죽었다 — status_code==204 또는 빈 바디를 응답 판정에서 먼저 걸러 None으로 정규화하도록 수정 (`.planning/debug/resolved/worker-parse-jsondecodeerror.md`, 커밋 `bf338a8`)
- [Phase ?]: 로컬 `.env`에 EMBEDDING_MODEL/EMBEDDING_PROVIDER가 없으면 embed 잡이 OpenRouter에 model:null을 보내 400으로 죽는다 — 코드 결함이 아니라 worker/settings.py가 의도적으로 코드 기본값을 안 두는 필드다. `.env.sample`의 관측값(baai/bge-m3, deepinfra/fp32)을 그대로 채우면 해결

</details>

### Pending Todos

None.

### Blockers/Concerns

None open. All v1.0 blockers were either resolved during the milestone or are now closed as historical context — see `.planning/RETROSPECTIVE.md` for what shipped and what to watch for, and `.planning/PROJECT.md` §Next Milestone Goals for open questions carried into v1.1 scoping. Full blocker history for v1.0 is preserved in the archived phase docs at `.planning/milestones/v1.0-phases/`.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| debug (audit false-positive) | `.planning/debug/knowledge-base.md` flagged as an "open debug session" (slug `knowledge-base`) by `audit-open` — it is the persistent resolved-sessions knowledge-base index file, not an in-progress session. No open debug work exists; the one entry it lists (`worker-parse-jsondecodeerror`) is already archived at `.planning/debug/resolved/worker-parse-jsondecodeerror.md`. | Acknowledged — not real deferred work | v1.0 milestone close (2026-08-13) |

## Session Continuity

Last session: 2026-08-13 (v1.0 milestone completion and archival)
Stopped at: v1.0 milestone shipped, archived, and tagged
Resume file: None — no active phase. Next entry point is `/gsd-new-milestone`.

**재개 시 첫 행동:** v1.0은 완전히 마감됐다. 다음 세션은 `/gsd-new-milestone`으로 v1.1 스코프를 잡는 것부터 시작한다.

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
