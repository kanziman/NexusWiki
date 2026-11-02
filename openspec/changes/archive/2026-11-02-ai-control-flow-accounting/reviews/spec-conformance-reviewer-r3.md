# Spec Conformance 리뷰 — ai-control-flow-accounting r3

- 판정: needs_fix
- 대상: 기준 커밋 `79b68fe` 대비 `66a2afd` + 커밋되지 않은 작업 트리 (`git diff 79b68fe` + 추적되지 않은 파일)
- 일시: 2026-11-02T10:37:27Z

## 요약

59개 Scenario 중 57개는 충족, 1개는 미충족, 1개는 결정대로 보류(task 7.3)다. r2의 미충족 3건은 모두 해소됐다.

차단 사유는 이번 라운드에 추가된 Scenario 하나다. "멤버가 이미 쓰인 trace로 새 턴을 만들려 한다"는 `start_ask_turn`에서만 막혀 있다. 같은 JWT로 `ask_messages`에 직접 INSERT하면 201로 통과하고, 그 trace의 상세 조회가 403에서 200으로 바뀐다. 실제 스택에서 재현했다. 다른 테넌트로 넘어가는 경로는 아니고 새로 드러나는 값도 찾지 못했다. 그래도 Scenario의 THEN 두 절이 모두 거짓이다.

- 스펙 밖 동작: 찾지 못했다.
- 조용한 범위 축소: 조치 항목 1이 해당한다. task 8.6이 `- [x]`다.
- 미검증 완료 주장: 조치 항목 1의 경로 외에는 찾지 못했다.

⚠️ 프로젝트 규칙상 3라운드에서 `pass`가 아니므로 호출자가 `blocked`로 확정해 사람에게 넘긴다. 이 보고서의 `needs_fix`는 "스펙을 고치지 않고 코드로 해결된다"는 분류다.

## r2 조치 항목 해소 여부

| 항목 | 상태 | 근거 |
| --- | --- | --- |
| 1. falsy 형태 프레임 | 해소 | `apps/api/src/api/services/ask.py:449-472`가 부재와 `null`만 빈 값으로 두고 나머지는 타입을 검사한다. 테스트 `apps/api/tests/test_ask_router.py:546-577`이 `0`, `""`, `false`, `{}`, `[0]`, `delta`의 `0`, `""`, `false`, `[]`를 앞선 델타와 함께 보내 `llm_unavailable`, `done`, `status=error`, 빈 답변을 단언한다. 정상 대조군 `:580` (`content: null`) |
| 2. 렌더 실패와 공급자 호출 0회 | 해소 | `test_ask_router.py:624-679`의 `render` 매개변수(`{{question` 템플릿)가 `context_unavailable`, `status=error`, `fake_llm.calls == 0`을 단언한다. 검색 실패는 `:602-621`이 `fake_llm.calls == 0`을 단언한다 |
| 3-a. 워커 라우트 등록 | 해소 | `apps/worker/tests/test_worker_main.py:179-218`이 실제 `_serve_internal_listeners`가 만든 앱으로 204와 401을 확인한다 |
| 3-b. `_ask_service` 기본 조립 | 해소 | `test_ask_router.py:754-782`가 기본 조립에서 내보내기가 `/internal/ask-turn-export`로 가는 것을 확인한다 |
| 3-c. 격리 테스트 고정 본문과 viewer | 해소 | `apps/api/tests/test_tenant_isolation_full_path.py:564-592`가 고정 본문을, `:596-612`가 owner, editor, viewer 대조군을 단언한다 |

## 이번 라운드에서 직접 실행한 검증

| 항목 | 결과 |
| --- | --- |
| 관련 pytest 16개 파일 (ask, control, db 오류 매핑, 관측, 미들웨어, 검색, 워커, 게이트웨이, core) | 208 통과 |
| `test_tenant_isolation_full_path.py -k retrieval` | 5 통과 |
| `test_pipeline_e2e.py`, `test_controlled_ai_evidence.py`, `test_handlers.py`, `test_queue.py` | 84 통과, 1 스킵 (`test_committed_code_cannot_ship_with_uncommitted_evidence`) |
| vitest `ControlRoom`, `ControlledAiShowcase`, `AskConversation` | 28 통과 |
| `supabase/tests/0023_job_trace.sql` | `job_trace: ok`, 롤백 |
| `openspec validate ai-control-flow-accounting --strict` | valid |
| 로컬 DB 최신 마이그레이션, `ask_messages` 권한과 정책 | `0026`. `authenticated`의 UPDATE는 네 컬럼, INSERT는 `trace_id` 포함 전 컬럼 |
| 스크래치 프로브 2종 | 아래 "실측" |

전체 스위트, `typecheck`, `lint`, `build`, 0001~0026 전체 적용은 호출자가 알린 결과를 인용하며 재실행하지 않았다.

## 실측

스크래치에 두고 실행했다. 저장소 파일을 바꾸지 않았고 프로브는 지웠다. 실행 뒤 `ask_messages` 0행, `test-%` 사용자 0건이다.

### trace 채택 (실제 API와 PostgREST, viewer JWT)

| 원본 trace | 상세 조회(전) | `start_ask_turn` | 직접 `POST /rest/v1/ask_messages` | 상세 조회(후) |
| --- | --- | --- | --- | --- |
| 다른 멤버의 Ask 턴과 그 사용량 행 | 403 | 403 `42501` | **201** | **200**, `calls` 1건 |
| 수집 잡 | 403 | 403 `42501` | **201** | **200**, `calls` 0건, `stages` 빈 값 |

### 리스너 종료 (실제 uvicorn, 제한 시간만 1초로 축소, 공급자와 기록은 대역)

세 번 실행했다. 제한 시간 뒤 스트림이 취소되고, 기록이 `incomplete=True`로 시작되고, `_drain_usage_writes`가 그 기록을 집합에 담아 끝까지 기다린 뒤 리스너가 내려갔다. 클라이언트는 `RemoteProtocolError`를 받으므로 API는 `llm_unavailable`로 종결한다. 실제 SIGTERM으로 보낸 경우 `stop`은 신호와 같은 시각에 세워져 큐 쪽 반납이 늦어지지 않았다.

## 시나리오 판정

### ai-control-room

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 추적 탭 / 완료된 trace 상세 | 충족 | `apps/api/src/api/routers/control.py:332-367`, `:369-383`, 합계 `:260-266` · 화면 `apps/dashboard/components/ControlRoom.tsx:365-485` · 테스트 `apps/api/tests/test_control_router.py:140`, `apps/dashboard/tests/ControlRoom.test.tsx:135` |
| 추적 탭 / 진행 중인 수집 trace | 충족 | `control.py:203-238`, `ControlRoom.tsx:433-447` · 테스트 `test_control_router.py:324`, `ControlRoom.test.tsx:227` |
| 추적 탭 / 데이터가 없는 워크스페이스 | 충족 | `ControlRoom.tsx:270-273` · 테스트 `ControlRoom.test.tsx:124` |
| (본문) Router 결정, 시도, 최종 상태 | 충족 | `ControlRoom.tsx:380`, `:390`, `:440`, `:457-458`, `:473` · 테스트 `ControlRoom.test.tsx:156` |
| (본문) 이후 탭은 지어낸 수치 없음 | 충족 | `ControlRoom.tsx:258` · 테스트 `ControlRoom.test.tsx:277` |
| (본문) 운영 환경 동작 | 확인 불가 | 환경 분기는 없다. 클라우드 마이그레이션 미적용이라 운영 실측은 불가능하다 |
| 작성자와 역할 / 작성자가 자신의 Ask trace를 본다 | 충족 | `control.py:325-332` · 테스트 `test_control_router.py:140` |
| 작성자와 역할 / editor가 다른 멤버의 Ask trace를 요청한다 | 충족 (우회 있음) | `control.py:369-386` · 테스트 `test_control_router.py:202`. 요청자가 먼저 같은 trace의 행을 직접 넣으면 200이 된다. 조치 항목 1에 합산한다 |
| 작성자와 역할 / viewer가 탭을 연다 | 충족 | `control.py:287-315`, `ControlRoom.tsx:159` · 테스트 `test_control_router.py:225`, `ControlRoom.test.tsx:210` |
| 작성자와 역할 / 다른 워크스페이스의 trace | 충족 | `control.py:287-288`, `:386`, `supabase/migrations/0026_ask_trace_aggregate.sql:40-43` · 테스트 `test_control_router.py:252` |
| 작성자와 역할 / 멤버십을 잃은 작성자 | 충족 | RLS `is_workspace_member` · 테스트 `test_control_router.py:274` |
| Ask 집계 / editor가 집계를 본다 | 충족 | `0026_ask_trace_aggregate.sql:18-28`, `control.py:390-414` · 테스트 `test_control_router.py:363` |
| Ask 집계 / 작성자가 보고서에 범위 밖의 값을 넣는다 | 충족 | `0026_ask_trace_aggregate.sql:62-67` · 테스트 `test_control_router.py:390`, `:415` |
| Ask 집계 / 집계 경계를 조금씩 옮긴다 | 충족 | `0026_ask_trace_aggregate.sql:37` · 테스트 `test_control_router.py:541` |
| trace 식별자 고정 / 멤버가 이미 쓰인 trace로 새 턴을 만들려 한다 | **미충족** | `start_ask_turn`만 막는다: `supabase/migrations/0025_ask_trace.sql:104-115` · 테스트 `test_control_router.py:459`는 RPC만 지난다. 직접 INSERT는 201이고 상세가 200이 된다(위 실측). `trace_id` INSERT 권한은 `0018_ask_history.sql:127`, 정책 `:112`에 trace 조건이 없다. 조치 항목 1 |
| trace 식별자 고정 / 작성자가 턴의 trace를 바꾸려 한다 | 충족 | `0025_ask_trace.sql:39-41`, 로컬 권한 조회 · 테스트 `test_control_router.py:439` |
| 허용 목록 / 실패한 호출을 포함한 trace | 충족 | `control.py:106-112`, `:241-257` · 테스트 `test_control_router.py:169`, `:297` |

재전달이 새 거부에 걸리지 않는 것은 `0025_ask_trace.sql:85-96`과 테스트 `test_control_router.py:505`로 확인했다. API의 정상 경로는 요청마다 새 값을 발급하고 임베딩보다 먼저 턴을 시작하므로(`apps/api/src/api/routers/ask.py:94-101`, `:129`) 거부에 닿지 않는다.

### ai-controls-showcase

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 쇼케이스 / 익명 방문자의 접속 | 충족 | `apps/dashboard/app/showcase/controlled-ai/page.tsx:18`, `apps/dashboard/middleware.ts:81` · 테스트 `apps/dashboard/tests/ControlledAiShowcase.test.tsx:82`, `:90`, `:101`, `:107` |
| 쇼케이스 / 로그인 세션이 있는 방문자 | 충족 | 미들웨어 대상 아님 · 테스트 `ControlledAiShowcase.test.tsx:90`, `:101` |
| 증거 / 충돌 판정 비용 누락의 전후 비교 | 보류 (7.3, 차단 아님) | 비용, 시나리오, 수정 전 커밋은 충족 (`apps/dashboard/components/ControlledAiShowcase.tsx:133` · 테스트 `:33`). 수정 후 커밋은 `apps/dashboard/content/controlled-ai/step1.json:38`의 `uncommitted`이고 코드 커밋 뒤에 채운다. 누락 방어는 `apps/worker/tests/test_controlled_ai_evidence.py:532`이며 r2에서 동작을 확인했다 |
| 증거 / 증거 파일의 내용 검사 | 충족 | 테스트 `test_controlled_ai_evidence.py:564`, `:584` |
| 증거 / 아직 구현되지 않은 단계 | 충족 | 테스트 `ControlledAiShowcase.test.tsx:67`, `test_controlled_ai_evidence.py:546` |

### ai-request-tracing

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 서버 발급 / 일반 요청 | 충족 | `packages/core/src/nexuswiki_core/trace.py:106`, `:151-158` · 테스트 `apps/api/tests/test_trace_middleware.py:54`, `:123` |
| 서버 발급 / 클라이언트가 trace 값을 위조한다 | 충족 | `trace.py:151-158` · 테스트 `test_trace_middleware.py:73` |
| 서버 발급 / 오류 응답 | 충족 | `trace.py:110-139` · 테스트 `test_trace_middleware.py:82`, `:91`, `:104` |
| 내부 호출 전파 / Ask 요청 한 건 | 충족 | `apps/api/src/api/services/ask.py:127`, `apps/api/src/api/services/retrieval.py:58`, `routers/ask.py:100`, `:109`, `apps/worker/src/worker/__main__.py:229` · 구간별 테스트 `test_trace_middleware.py:143`, `:168`, `apps/worker/tests/test_query_embedding.py:48`, `apps/worker/tests/test_llm_stream.py:52`, `test_worker_main.py:222`, `test_ask_router.py:339` |
| 내부 호출 전파 / 워크스페이스 헤더가 없는 질의 임베딩 | 충족 | `apps/worker/src/worker/query_embedding.py:25-32`, `:149-156`, `__main__.py:84-87`, `:121` · 테스트 `test_worker_main.py:261`, `:339` |
| 내부 호출 전파 / 내부 호출 호환성 | 충족 | `trace.py:151-158` · 테스트 `test_query_embedding.py:73` |
| 잡 체인 / 수집 체인 완료 | 충족 | `supabase/migrations/0023_job_trace.sql:102-108`, `:169-177` · 테스트 `test_pipeline_e2e.py:20`, `supabase/tests/0023_job_trace.sql:137`, `test_sources_router.py:258` |
| 잡 체인 / 실패한 잡의 재시도 | 충족 | 테스트 `supabase/tests/0023_job_trace.sql:145-179` (회수, dead 재시도 포함) |
| 잡 체인 / 이미 큐에 있는 대상의 중복 인큐 | 충족 | 테스트 `supabase/tests/0023_job_trace.sql:46-67` |
| 잡 체인 / trace가 없던 기존 잡 | 충족 | 테스트 `apps/worker/tests/test_queue.py:318` |
| Router shadow / 제목과 정확히 일치하는 질문 | 충족 | `ask.py:713`, `packages/core/src/nexuswiki_core/router.py:76` · 테스트 `test_ask_router.py:305`, `packages/core/tests/test_router.py:41` |
| Router shadow / 근거가 없는 질문 | 충족 | `router.py:65`, `ask.py:720-750` · 테스트 `test_ask_router.py:168`, `:327` |
| Router shadow / 내용이 같은 원문의 재컴파일 | 충족 | `apps/worker/src/worker/handlers/compile.py:148-174` · 테스트 `apps/worker/tests/test_handlers.py:841` |
| 본문 금지 / 고유한 문자열이 담긴 Ask와 컴파일 | 충족 | `ask.py:485-524`, `packages/core/src/nexuswiki_core/observability.py:192-217`, `:332-337` · 테스트 `apps/api/tests/test_observability_e2e.py:75`, `packages/core/tests/test_observability.py:350` |
| 외부 내보내기 / 자격 증명이 없다 | 충족 | `observability.py:116-122` · 테스트 `test_observability.py:90`, `:99` |
| 외부 내보내기 / Ask 턴을 내보낸다 | 충족 | `ask.py:140-184`, `:601-608`, `routers/ask.py:57-81`, `apps/worker/src/worker/ask_turn_export.py:40-50`, `__main__.py:263` · 테스트 `test_ask_router.py:693`, `:728`, `:754`, `apps/worker/tests/test_ask_turn_export.py:44`, `test_worker_main.py:179`, `test_observability_e2e.py:75` |
| 외부 내보내기 / 내부 라우트에 인증 없이 호출한다 | 충족 | `ask_turn_export.py:27-32`, `:45-46` · 테스트 `test_ask_turn_export.py:77`, `:91` |
| 외부 내보내기 / 외부 서비스 장애 | 충족 | `observability.py:320`, `ask.py:179-182` · 테스트 `test_observability.py:285`, `test_ask_router.py:693`, `:835` |
| 외부 내보내기 / 프로세스 종료 | 충족 | `__main__.py:297`, `:304-306`, `:435` · 테스트 `test_observability.py:306`, `test_worker_main.py:216-218`, `:354`, 위 실측 |
| (본문) API 설정에 비밀 키 없음 | 충족 | `apps/api/src`에 `LANGFUSE` 없음 · 테스트 `packages/core/tests/test_settings.py:29` |

### grounded-answering

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 스트림 종결 / Provider stream contains a malformed frame | 충족 | `ask.py:439-442`, `:846-860` · 테스트 `test_ask_router.py:380` |
| 스트림 종결 / Provider stream contains a frame with the wrong shape | 충족 | `ask.py:449-472` · 테스트 `test_ask_router.py:546-577` |
| 스트림 종결 / Preparation fails after the turn started | 충족 | `ask.py:665-703`, `:714-717`, `:752-781` · 테스트 `test_ask_router.py:602`, `:624` |
| 스트림 종결 / Provider reports an error mid-stream | 충족 | `ask.py:443-444`, `:459-460`, `:846-860` · 테스트 `test_ask_router.py:398-407` |
| (본문) 턴이 끝나기 전 클라이언트 끊김은 범위 밖 | 스펙과 일치 | `ask.py:844-845`가 `CancelledError`를 그대로 올린다. 추적은 #170, 근거 `design.md:168` |
| 인용 지표 / A sentence cites only fabricated anchors | 충족 | `ask.py:225` · 테스트 `apps/api/tests/test_ask_citations.py:28` |
| 인용 지표 / Anchor follows the period | 충족 | `packages/core/src/nexuswiki_core/sentences.py` · 테스트 `test_ask_citations.py:37`, `packages/core/tests/test_sentences.py` |
| 부분 검색 / One retrieval channel fails | 충족 | `ask.py:527`, `:808`, `apps/dashboard/components/AskConversation.tsx:392` · 테스트 `test_ask_router.py:442`, `:452` |
| 부분 검색 / Graph channel is disabled | 충족 | `ask.py:527` · 테스트 `test_ask_router.py:442`, `:463` |

### hybrid-retrieval

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 4채널 / All retrieval channels are available | 충족 | 테스트 `apps/api/tests/test_retrieval_service.py:44`, `:151` |
| 4채널 / A policy enables graph expansion | 충족 | 테스트 `test_retrieval_service.py:168` |
| 멤버십 게이트 / A non-member queries another workspace | 충족 | `apps/api/src/api/routers/retrieval.py:55-67`, `:81`, `apps/api/src/api/errors.py:251-258` · 테스트 `test_tenant_isolation_full_path.py:564-592` (고정 본문, 임베딩 0회, 사용량 0행) |
| 멤버십 게이트 / The bearer token is forged or expired | 충족 | `errors.py:69-82`, `:267-269` · 테스트 `test_tenant_isolation_full_path.py:564-592` (실제 스택), `apps/api/tests/test_db_error_mapping.py:36`, `:60`. 게이트웨이의 401은 500으로 남는 것도 같은 매개변수가 고정한다 |
| 멤버십 게이트 / A member queries their workspace | 충족 | `retrieval.py:64`, `:81-109` · 테스트 `test_tenant_isolation_full_path.py:596-612` (owner, editor, viewer), 응답 계약 `test_retrieval_service.py:223` |

### usage-guardrails

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 사용량 기록 / Provider reports successful billable usage | 충족 | `apps/worker/src/worker/llm_gateway.py:176` · 테스트 `apps/worker/tests/test_llm_gateway.py:108`, `:162` |
| 사용량 기록 / Structured output is retried after a validation failure | 충족 | `apps/worker/src/worker/llm.py:248-263` · 테스트 `test_llm_gateway.py:82` |
| 사용량 기록 / Every structured attempt fails | 충족 | 테스트 `test_llm_gateway.py:95` |
| 사용량 기록 / A billed response is rejected | 충족 | `llm.py:248-263`, `apps/worker/src/worker/embedding.py:91-92` · 테스트 `test_llm_gateway.py:246`, `:285` |
| 사용량 기록 / Conflict judgement calls the provider | 충족 | 테스트 `test_handlers.py:709` |
| 사용량 기록 / Ask stream is aborted | 충족 | `apps/worker/src/worker/llm_stream.py:135-175`, `llm_gateway.py:148` · 테스트 `test_llm_stream.py:315`, `:331`, `:357`, `test_llm_gateway.py:201`, 위 실측 |
| 사용량 기록 / Query embedding completes | 충족 | `__main__.py:83-98`, `:118-123` · 테스트 `test_worker_main.py:222`, `:247` |
| 사용량 기록 / Job is retried after usage was recorded | 충족 | `apps/worker/src/worker/db/service.py:443` · 테스트 `test_pipeline_e2e.py:31`, `test_llm_gateway.py:82` |

## 조치가 필요한 항목

1. **이미 쓰인 trace의 채택이 직접 INSERT로 통과한다.** 근거 Scenario: "멤버가 사용량이나 잡에 이미 있는 `trace_id`를 넣어 새 턴을 시작한다 → 데이터베이스가 권한 오류로 거부하고, 그 trace의 상세 조회 권한은 변하지 않는다." 검사는 `supabase/migrations/0025_ask_trace.sql:104-115`의 `start_ask_turn` 안에만 있다. `authenticated`는 `ask_messages`의 `trace_id`에 INSERT 권한이 있고(`0018_ask_history.sql:127`), `ask_messages_insert_own`은 스레드 소유와 멤버십만 본다. 함수가 `security invoker`라 함수가 쓰는 권한을 요청자가 그대로 가지므로, 컬럼 권한만 좁혀서는 막히지 않는다.

   - 결과: viewer가 자기 스레드에 그 trace의 행을 넣으면 201이고, `control.py:331-332`의 게이트를 지나 상세가 403에서 200으로 바뀐다. 같은 `client_turn_id`로 `/ask`를 재전달하면 저장된 trace가 다시 묶이므로(`0025_ask_trace.sql:85-96`, `routers/ask.py:107-109`), 이번 검사가 막으려던 "합계 부풀리기"도 같은 경로로 남는다(코드 판독).
   - 영향 범위: 다른 테넌트에는 닿지 않는다. 응답의 `calls`는 그 viewer가 `usage_events`에서 RLS로 직접 읽을 수 있는 값이고, Ask 분기는 `jobs`를 읽지 않아 `stages`가 비어 있다. `design.md:167`은 위험을 `start_ask_turn` 호출로만 서술하고, `:170`은 직접 INSERT를 집계 건수 위조로만 다룬다. `tenant-isolation-reviewer-r2.md`의 지적 4에 "같은 일을 직접 INSERT로도 할 수 있다"가 이미 적혀 있었다.
   - 제안 (스펙 변경 없음): 검사를 `0025`의 INSERT 경로로 옮긴다. `ask_messages_insert_own`의 `with check`에 "`trace_id`가 null이거나 같은 워크스페이스의 `usage_events`, `jobs`에 없음"을 더하면 RPC와 직접 INSERT가 함께 `42501`이 된다. BEFORE INSERT 트리거도 같은 효과다. `test_control_router.py:459`에 직접 INSERT 매개변수를 추가하고, 재전달 테스트 `:505`가 계속 통과하는지 확인하며, `design.md:167`을 고친다. 제안 자체를 적용해 보지는 않았다.
   - 사람이 고를 수 있는 다른 길: 새로 드러나는 값이 없다는 이유로 수용한다면, Scenario를 `start_ask_turn` 경로로 좁히고 직접 INSERT의 잔여 위험을 Risks에 적어야 한다. 이는 스펙 변경이다.

## 참고 (차단 사유 아님)

- **`_serve_internal_listeners`의 기록 대기 연결을 테스트가 고정하지 않는다.** `test_worker_main.py:325`는 `_drain_usage_writes`에 `stream_records`를 직접 넘긴다. `__main__.py:305`를 지워도 실패하지 않는다. 대응 Scenario가 없고 실측으로 동작을 확인했다. 취소된 기록이 만들어지는 시점과 대기 집합을 읽는 시점이 같은 밀리초 안에 있어, 순서가 이벤트 루프 진행에 기대고 있다. 3회 모두 잡혔지만 보장은 아니다.
- **`export_ask_turn`의 값 검사는 모양만 본다.** `observability.py:87`은 공백 없는 64자 이하 문자열을 통과시키고, `route.decision`을 `AskRoute` 값으로 닫지 않는다. 구간 이름은 닫혀 있다(`:88`, `:215`). API 조립에 본문이 없고 라우트에는 내부 토큰이 필요하므로 Scenario는 충족한다.
- **`[DONE]` 없이 조용히 끝난 스트림은 `resolved`로 저장된다.** `ask.py:838-843`에 종료 프레임 확인이 없다. 스펙의 Requirement는 깨진 프레임과 오류 프레임만 다루므로 미충족이 아니다. 전송 계층이 끊기면 `RemoteProtocolError`로 오류 종결된다(위 실측).
- **전 라우트 401 계약은 `design.md:191`에만 있다.** delta spec의 Scenario는 `/retrieval`만 다룬다. 결정을 다시 묻지 않지만, 아카이브 뒤에도 계약으로 남기려면 스펙 동기화 때 Requirement로 옮기는 편이 낫다.
- `RESUME.md`는 호출자 안내대로 판정에서 뺐다. task 7.3의 미완료와 `after.commit`의 `uncommitted`도 차단 사유로 삼지 않았다.
- `design.md`의 "리뷰 1라운드 후 결정" 절은 위임 확정으로 보고 다시 묻지 않았다.

## 판정 근거

`needs_fix`다. 미충족 Scenario가 하나 있고, task 8.6이 `- [x]`이지만 Scenario의 THEN 두 절이 직접 INSERT 경로에서 거짓이다. `0025`의 정책이나 트리거와 테스트 추가로 해결되며 스펙을 고칠 필요가 없어 `blocked`의 정의에는 해당하지 않는다. 격리 r2 지적을 반영한 나머지 변경(`grounded-answering`의 범위 문장, `hybrid-retrieval`의 JWT 거부 한정, `export_ask_turn`의 닫힌 값, 워커 종료)은 delta spec과 일치한다. 다만 3라운드 제한에 따라 호출자는 이 결과를 `blocked`로 확정해 사람에게 넘겨야 한다. 사람이 정할 것은 조치 항목 1의 두 길 중 하나다.
