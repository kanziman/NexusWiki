# Spec Conformance 리뷰 — ai-control-flow-accounting r2

- 판정: needs_fix
- 대상: 기준 커밋 `79b68fe` 대비 `66a2afd` + 커밋되지 않은 작업 트리 (`git diff 79b68fe` + 새 파일 3개)
- 일시: 2026-11-02T19:12:07+09:00

## 요약

58개 Scenario 중 56개는 충족이고 1개는 부분 미충족, 1개는 결정에 따라 보류(task 7.3)다. 동작 결함은 한 건이다. 형태가 틀린 프레임 중 **값이 falsy인 경우**(`{"choices":0}`, `{"choices":[{"delta":0}]}` 등)가 오류로 종결되지 않아, 부분 답변이 `resolved`로 저장된다. 나머지 지적은 동작은 맞는데 테스트가 고정하지 않는 공백이다. 전부 스펙을 바꾸지 않고 해결된다.

- 스펙 밖 동작: 찾지 못했다. 전 라우트 401 매핑은 delta spec이 `/retrieval`만 다루지만 `design.md` "리뷰 1라운드 후 결정"에 기록된 대로다. 아래 "범위 밖 관찰"을 본다.
- 조용한 범위 축소: 조치 항목 1이 해당한다. task 1.1이 `- [x]`다.
- 미검증 완료 주장: 조치 항목 2, 3이 해당한다. 동작은 프로브와 코드로 확인했다.

## 1라운드 조치 항목 해소 여부

| 항목 | 상태 | 근거 |
| --- | --- | --- |
| 1. 형태가 틀린 프레임과 스트림 전 실패 | **부분 해소** | 스트림 전 실패는 해소: `apps/api/src/api/services/ask.py:647-675`, `:677-686`, `:721-750`. 형태 검사는 truthy한 틀린 값만 잡는다: `:438`, `:448`의 `or` 때문에 falsy한 틀린 값이 빈 값으로 바뀐다. 조치 항목 1 |
| 2. 청구됐지만 기록되지 않는 경로 | 해소 | `apps/worker/src/worker/llm.py:246-263` (기록 후 `_read_content`), `apps/worker/src/worker/embedding.py:83-101` (기록 후 공급자·차원 검증), `apps/worker/src/worker/llm_gateway.py:117-134` · 테스트 `apps/worker/tests/test_llm_gateway.py:246`, `:285` |
| 3. Control Room의 Router 결정과 최종 상태 | 해소 | `apps/dashboard/components/ControlRoom.tsx:379-391`, `:457`, `:472` · 테스트 `apps/dashboard/tests/ControlRoom.test.tsx:156` |
| 4. 공개 증거의 `after.commit` | 결정대로 보류, 방어 테스트 동작 확인 | 아래 "task 7.3 방어 테스트 실측" |
| 5. 테스트 공백 (a)~(d) | 해소 | (a)(b) `apps/api/tests/test_pipeline_e2e.py:20`, `apps/api/tests/fixtures/pipeline.py:289`의 `assert_single_trace_across_chain` · (c) `supabase/tests/0023_job_trace.sql:166`의 `reap_stale_jobs('-1 hour')` · (d) `test_pipeline_e2e.py:31`. (d)는 같은 잡의 재실행이 아니라 새 `parse` 잡으로 재처리한 것이다. `insert_usage_event`가 키 없는 INSERT라 경로가 같으므로 해소로 본다 |

"사람의 확인이 필요한 사항" 두 건(끊긴 클라이언트, squash 뒤 해시)은 `design.md:191-193`에 결정되어 있고, 구현과 스펙이 그 결정대로다. 끊긴 클라이언트는 `specs/grounded-answering/spec.md` 본문이 범위 밖으로 명시하고, `ask.py:813-814`는 `CancelledError`를 그대로 올린다.

## 이번 라운드에서 직접 실행한 검증

| 항목 | 결과 |
| --- | --- |
| 이 change의 관련 pytest 18개 파일 (로컬 스택 포함) | 230 통과, 1 스킵. 스킵은 `test_committed_code_cannot_ship_with_uncommitted_evidence` |
| `vitest` `ControlRoom` · `ControlledAiShowcase` · `AskConversation` | 28 통과 |
| `supabase/tests/0023_job_trace.sql` | `job_trace: ok`, 롤백 |
| `openspec validate ai-control-flow-accounting --strict` | valid |
| 로컬 DB `schema_migrations` 최신 번호 | `0026` |
| 로컬 DB `authenticated`의 `ask_messages` UPDATE 권한 | 테이블 단위 0건, 컬럼 단위 `answer_text`, `citations`, `control_report`, `status` 4개 |
| `_delta_text` · `AskService.ask` 프로브 (스크래치, 대역 DB) | 아래 "실측" |
| 임시 클론에서 task 7.3 절차 재현 | 아래 "task 7.3 방어 테스트 실측" |

전체 스위트(779 통과)와 대시보드 전체(463 통과), `typecheck` · `lint` · `build`는 호출자가 알린 결과를 인용하며 재실행하지 않았다.

## 시나리오 판정

### ai-control-room

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Control Room 추적 탭 / 완료된 trace 상세 | 충족 | `apps/api/src/api/routers/control.py:332-367`, `:369-383`, 합계 `:260-266` · 화면 `ControlRoom.tsx:365-485` · 테스트 `apps/api/tests/test_control_router.py:140`, `ControlRoom.test.tsx:135` |
| Control Room 추적 탭 / 진행 중인 수집 trace | 충족 | `control.py:203-238`, `ControlRoom.tsx:433-447` · 테스트 `test_control_router.py:324`, `ControlRoom.test.tsx:227` |
| Control Room 추적 탭 / 데이터가 없는 워크스페이스 | 충족 | `ControlRoom.tsx:270-273` · 테스트 `ControlRoom.test.tsx:124` |
| (본문) 상세 표시 항목: Router 결정, 시도, 최종 상태 | 충족 | `ControlRoom.tsx:379-391`, `:440`, `:457-458`, `:472-473` · 테스트 `ControlRoom.test.tsx:156` |
| (본문) 이후 탭은 지어낸 수치 없음 | 충족 | `ControlRoom.tsx:91-93` · 테스트 `ControlRoom.test.tsx:277` |
| (본문) 운영 환경 동작 | 확인 불가 | 환경 분기는 없다. 클라우드 마이그레이션 미적용이라 운영 실측은 불가능하다 |
| 작성자와 역할 / 작성자가 자신의 Ask trace를 본다 | 충족 | `control.py:326-333` · 테스트 `test_control_router.py:140` |
| 작성자와 역할 / editor가 다른 멤버의 Ask trace를 요청한다 | 충족 | `control.py:369-386` · 테스트 `test_control_router.py:202` |
| 작성자와 역할 / viewer가 탭을 연다 | 충족 | `control.py:287-315`, `ControlRoom.tsx:159` · 테스트 `test_control_router.py:225`, `ControlRoom.test.tsx:210` |
| 작성자와 역할 / 다른 워크스페이스의 trace | 충족 | `control.py:287-288`, `:386`, `supabase/migrations/0026_ask_trace_aggregate.sql:40-43` · 테스트 `test_control_router.py:252` |
| 작성자와 역할 / 멤버십을 잃은 작성자 | 충족 | RLS `is_workspace_member` · 테스트 `test_control_router.py:274` |
| Ask 집계 / editor가 집계를 본다 | 충족 | `0026_ask_trace_aggregate.sql:18-28`, `control.py:403-414` · 테스트 `test_control_router.py:363` |
| Ask 집계 / 작성자가 보고서에 범위 밖의 값을 넣는다 | 충족 | `0026_ask_trace_aggregate.sql:53-68` · 테스트 `test_control_router.py:390` (문자열), `:415` (`1e20`, `-5`, `86400001`) |
| Ask 집계 / 집계 경계를 조금씩 옮긴다 | 충족 | `0026_ask_trace_aggregate.sql:37` · 테스트 `test_control_router.py:457` |
| trace 식별자 고정 / 작성자가 턴의 trace를 바꾸려 한다 | 충족 | `supabase/migrations/0025_ask_trace.sql:39-41`, 로컬 권한 조회 · 테스트 `test_control_router.py:439` (403, `42501`) |
| 허용 목록 / 실패한 호출을 포함한 trace | 충족 | `control.py:47-53`, `:106-112`, `:241-257` · 테스트 `test_control_router.py:169`, `:297` |

### ai-controls-showcase

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 합성 증거만 쓰는 쇼케이스 / 익명 방문자의 접속 | 충족 | `apps/dashboard/app/showcase/controlled-ai/page.tsx:18`, `apps/dashboard/middleware.ts:81` · 테스트 `apps/dashboard/tests/ControlledAiShowcase.test.tsx:82`, `:90`, `:101`, `:107` |
| 합성 증거만 쓰는 쇼케이스 / 로그인 세션이 있는 방문자 | 충족 | 미들웨어 대상 아님 · 테스트 `ControlledAiShowcase.test.tsx:90`, `:101` |
| 재현 가능한 증거 / 충돌 판정 비용 누락의 전후 비교 | 보류 (7.3, 지적 제외) | 비용, 시나리오, 수정 전 커밋은 충족 (`apps/dashboard/components/ControlledAiShowcase.tsx:133` · 테스트 `:33`). 수정 후 커밋은 `apps/dashboard/content/controlled-ai/step1.json:38`의 `uncommitted`이고 결정대로 코드 커밋 뒤에 채운다 (`design.md:193`) |
| 재현 가능한 증거 / 증거 파일의 내용 검사 | 충족 | `apps/worker/tests/test_controlled_ai_evidence.py`의 `test_evidence_contains_no_identifier_or_credential_shapes`, 정규식 자체 검증 `test_forbidden_patterns_actually_match_their_shape` |
| 재현 가능한 증거 / 아직 구현되지 않은 단계 | 충족 | 테스트 `ControlledAiShowcase.test.tsx:67`, `test_upcoming_steps_carry_no_example_numbers` |

### ai-request-tracing

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 서버 발급 / 일반 요청 | 충족 | `packages/core/src/nexuswiki_core/trace.py:106`, `:142-148` · 테스트 `apps/api/tests/test_trace_middleware.py:54`, `:123` |
| 서버 발급 / 클라이언트가 trace 값을 위조한다 | 충족 | `trace.py:151-158` · 테스트 `test_trace_middleware.py:73` |
| 서버 발급 / 오류 응답 | 충족 | `trace.py:125-139` · 테스트 `test_trace_middleware.py:82`, `:91`, `:104` |
| 내부 호출 전파 / Ask 요청 한 건 | 충족 | `apps/api/src/api/services/ask.py:127`, `apps/api/src/api/services/retrieval.py:57-58`, `apps/api/src/api/routers/ask.py:101`, `:107-109`, `llm_gateway.py:194` · 구간별 테스트 `test_trace_middleware.py:143`, `:168`, `apps/worker/tests/test_query_embedding.py:48`, `apps/worker/tests/test_llm_stream.py:52`, `apps/worker/tests/test_worker_main.py:177`, `apps/api/tests/test_ask_router.py:336` |
| 내부 호출 전파 / 워크스페이스 헤더가 없는 질의 임베딩 | 충족 | `apps/worker/src/worker/query_embedding.py:25-32`, `:148-156`, `apps/worker/src/worker/__main__.py:78-81`, `:110` · 테스트 `test_worker_main.py:216`, `:289` |
| 내부 호출 전파 / 내부 호출 호환성 | 충족 | `trace.py:151-158` · 테스트 `test_query_embedding.py:73` |
| 잡 체인 / 수집 체인 완료 | 충족 | `supabase/migrations/0023_job_trace.sql:102-108`, `apps/worker/src/worker/db/service.py:173`, `apps/worker/src/worker/queue.py:244-245` · 테스트 `test_pipeline_e2e.py:20`, `supabase/tests/0023_job_trace.sql:113`, `apps/worker/tests/test_queue.py:297` |
| 잡 체인 / 실패한 잡의 재시도 | 충족 | 해당 함수가 `trace_id`를 쓰지 않음 · 테스트 `supabase/tests/0023_job_trace.sql:145` (회수 포함, 이번 라운드 실행 통과) |
| 잡 체인 / 이미 큐에 있는 대상의 중복 인큐 | 충족 | 테스트 `supabase/tests/0023_job_trace.sql:46` |
| 잡 체인 / trace가 없던 기존 잡 | 충족 | `queue.py:244` · 테스트 `test_queue.py:318`, `supabase/tests/0023_job_trace.sql:186` |
| Router shadow / 제목과 정확히 일치하는 질문 | 충족 | `ask.py:682`, `packages/core/src/nexuswiki_core/router.py:57` · 테스트 `test_ask_router.py:302`, `packages/core/tests/test_router.py:41` |
| Router shadow / 근거가 없는 질문 | 충족 | `router.py:65`, `ask.py:689-719` · 테스트 `test_ask_router.py:166`, `:324` |
| Router shadow / 내용이 같은 원문의 재컴파일 | 충족 | `apps/worker/src/worker/handlers/compile.py:148-174` · 테스트 `apps/worker/tests/test_handlers.py:841` |
| 본문 금지 / 고유한 문자열이 담긴 Ask와 컴파일 | 충족 | `ask.py:470-509`, `packages/core/src/nexuswiki_core/observability.py:72-82`, `:319-332` · 테스트 `apps/api/tests/test_observability_e2e.py:75` (이번 라운드부터 실제 내부 라우트를 지난다) |
| 외부 내보내기 / 자격 증명이 없다 | 충족 | `observability.py:110-112` · 테스트 `packages/core/tests/test_observability.py:90`, `:99` |
| 외부 내보내기 / Ask 턴을 내보낸다 | 충족 (연결 테스트 공백) | `ask.py:151-169`, `:544-550`, `:583-590`, `apps/api/src/api/routers/ask.py:77-81`, `apps/worker/src/worker/ask_turn_export.py:39-49`, `__main__.py:255` · 테스트 `test_ask_router.py:658`, `:693`, `apps/worker/tests/test_ask_turn_export.py:44`, `test_observability_e2e.py`. 조치 항목 3 |
| 외부 내보내기 / 내부 라우트에 인증 없이 호출한다 | 충족 | `ask_turn_export.py:26-31`, `:44-45` · 테스트 `test_ask_turn_export.py:77`, `:91` |
| 외부 내보내기 / 외부 서비스 장애 | 충족 | `observability.py:294-309` · 테스트 `test_observability.py:285`, `test_ask_router.py:658` |
| 외부 내보내기 / 프로세스 종료 | 충족 | `__main__.py:414-417` · 테스트 `test_observability.py:306`, `test_worker_main.py:304` |
| (본문) API 설정에 비밀 키 없음 | 충족 | `apps/api/src`에 `LANGFUSE` 설정 필드 없음 · 테스트 `packages/core/tests/test_settings.py:17` |

### grounded-answering

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 스트림 종결 / Provider stream contains a malformed frame | 충족 | `ask.py:430-433`, `:815-831` · 테스트 `test_ask_router.py:377` |
| 스트림 종결 / Provider stream contains a frame with the wrong shape | **부분 미충족** | truthy한 틀린 값은 충족 (`ask.py:439-456` · 테스트 `test_ask_router.py:553`). falsy한 틀린 값은 `:438`, `:448`에서 통과해 `resolved`로 저장된다. 조치 항목 1 |
| 스트림 종결 / Preparation fails after the turn started | 충족 (테스트 공백) | `ask.py:647-675`, `:677-686`, `:721-750` · 테스트 `test_ask_router.py:588`, `:612`. 렌더 실패 테스트가 없고, 검색 실패 테스트는 공급자 미호출을 단언하지 않는다. 프로브로 동작 확인. 조치 항목 2 |
| 스트림 종결 / Provider reports an error mid-stream | 충족 | `ask.py:434-435`, `:446-447`, `:815-831` · 테스트 `test_ask_router.py:404` |
| 인용 지표 / A sentence cites only fabricated anchors | 충족 | `ask.py:216-262` · 테스트 `apps/api/tests/test_ask_citations.py:28` |
| 인용 지표 / Anchor follows the period | 충족 | `packages/core/src/nexuswiki_core/sentences.py` · 테스트 `test_ask_citations.py:37`, `packages/core/tests/test_sentences.py` |
| 부분 검색 / One retrieval channel fails | 충족 | `ask.py:512-522`, `:777`, `apps/dashboard/components/AskConversation.tsx:392` · 테스트 `test_ask_router.py:439`, `:449`, `apps/dashboard/tests/AskConversation.test.tsx` |
| 부분 검색 / Graph channel is disabled | 충족 | `ask.py:518-522` · 테스트 `test_ask_router.py:439`, `:460` |

### hybrid-retrieval

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 4채널 / All retrieval channels are available | 충족 | 테스트 `apps/api/tests/test_retrieval_service.py:44`, `:151` |
| 4채널 / A policy enables graph expansion | 충족 | 테스트 `test_retrieval_service.py:168` |
| 멤버십 게이트 / A non-member queries another workspace | 충족 (테스트 공백) | `apps/api/src/api/routers/retrieval.py:55-67`, `:81`, `apps/api/src/api/errors.py:235-242` · 테스트 `apps/api/tests/test_tenant_isolation_full_path.py:564`. 테스트는 상태 코드만 보고 고정 본문을 단언하지 않는다. 프로브에서 `{"detail":"forbidden"}` 확인. 조치 항목 3 |
| 멤버십 게이트 / The bearer token is forged or expired | 충족 | `retrieval.py:62-65`, `errors.py:252-254` · 테스트 `test_tenant_isolation_full_path.py:564` (실제 스택), `apps/api/tests/test_db_error_mapping.py:33` |
| 멤버십 게이트 / A member queries their workspace | 충족 (테스트 공백) | `retrieval.py:64`, `:81-109` · 테스트 `test_tenant_isolation_full_path.py:592`, `test_retrieval_service.py:223`. 대조군이 owner뿐이라 "any role"의 viewer가 없다. RPC 경로는 `test_control_router.py:225`의 viewer가 지난다. 조치 항목 3 |

### usage-guardrails

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 사용량 기록 / Provider reports successful billable usage | 충족 | `llm_gateway.py:176-219` · 테스트 `test_llm_gateway.py:108`, `:162` |
| 사용량 기록 / Structured output is retried after a validation failure | 충족 | `llm.py:248-260` · 테스트 `test_llm_gateway.py:82` |
| 사용량 기록 / Every structured attempt fails | 충족 | 테스트 `test_llm_gateway.py:95` |
| 사용량 기록 / A billed response is rejected | 충족 | `llm.py:247-263`, `embedding.py:91-101` · 테스트 `test_llm_gateway.py:246` (`content: null`, 빈 `choices`), `:285` (공급자 불일치, 차원 불일치) |
| 사용량 기록 / Conflict judgement calls the provider | 충족 | 테스트 `test_handlers.py:709` |
| 사용량 기록 / Ask stream is aborted | 충족 | `apps/worker/src/worker/llm_stream.py`, `llm_gateway.py:148-173` · 테스트 `test_llm_stream.py:315`, `:331`, `:357`, `test_llm_gateway.py:201` |
| 사용량 기록 / Query embedding completes | 충족 | `__main__.py:67-91`, `:107-113` · 테스트 `test_worker_main.py:177`, `:202`, `:258` |
| 사용량 기록 / Job is retried after usage was recorded | 충족 | `apps/worker/src/worker/db/service.py:443`의 키 없는 INSERT · 테스트 `test_pipeline_e2e.py:31`, `test_llm_gateway.py:82` |

## task 7.3 방어 테스트 실측

`test_committed_code_cannot_ship_with_uncommitted_evidence`는 실제로 동작한다. 저장소를 임시 디렉터리에 클론해 작업 트리 변경을 옮긴 뒤 다음 순서로 실행했고, 원본 작업 트리는 건드리지 않았다. 클론은 실행 후 지웠다.

| 단계 | 결과 |
| --- | --- |
| 측정 대상 코드가 더럽다 | 스킵 |
| 코드를 커밋했고 증거는 `uncommitted`다 | **실패** (`Left contains 4 more items, first extra item: 'conflict-judge-cost'`) |
| task 7.3의 `measure` · `write after` 실행 | 4개 항목의 `after.commit`이 실제 해시로 채워짐, 증거 파일 전체 19건 통과 |

CI의 `pytest` 잡이 `apps/worker/tests`를 포함해 전체를 돌리므로(`.github/workflows`의 `uv run pytest -rs`), 코드를 커밋한 브랜치에서 7.3을 잊으면 CI가 실패한다. 재생성 뒤 값 비교 테스트도 함께 통과해 `after` 측정값은 현재 코드와 일치한다.

## 실측

스크래치 프로브로 얻은 값이다. 저장소 파일은 바꾸지 않았고 프로브는 지웠다.

`_delta_text`:

```text
{"choices":0}, {"choices":""}, {"choices":false}, {"choices":{}}  → ''  (실패 아님)
{"choices":[{"delta":0}]}, "delta":"", "delta":false, "delta":[]   → ''  (실패 아님)
{"choices":[0]}, {"choices":[null]}                                → malformed_frame
{"choices":[{"delta":{"content":0}}]}, "content":false             → malformed_frame
{"choices":null}, {"choices":[{"delta":null}]}, {}                 → ''  (허용되는 부재)
```

`AskService.ask` (대역 DB, 근거 1건):

```text
{"choices":0} 만 오는 스트림     → citations.error 없음, status=resolved, answer='', 공급자 호출 1
앞부분 델타 + {"choices":[{"delta":0}]} → citations.error 없음, status=resolved, answer='앞부분 [[src:s1]].'
검색 실패                       → meta, citations(retrieval_unavailable), done / status=error, 공급자 호출 0
템플릿에 없는 자리표시자         → meta, citations(context_unavailable), done / status=error, 공급자 호출 0
형식이 깨진 템플릿 `{{ broken`   → 위와 같음
템플릿 행의 필수 키 누락         → 위와 같음
```

`/retrieval` (대역 DB):

```text
has_workspace_role = false → 403 {"detail":"forbidden"}, 임베딩 호출 0, X-Trace-Id 있음
has_workspace_role = true  → 200, 임베딩 호출 1
```

## 조치가 필요한 항목

1. **값이 falsy인 틀린 형태의 프레임이 오류로 종결되지 않는다.** `apps/api/src/api/services/ask.py:438`의 `payload.get("choices") or []`와 `:448`의 `choice.get("delta") or {}`가 `0`, `""`, `false`, `{}`(choices), `[]`(delta)를 "값 없음"으로 바꿔 뒤의 `isinstance` 검사(`:439`, `:449`)를 건너뛴다. 그래서 앞선 델타가 있으면 부분 답변이 `resolved`로 저장되고, 그런 프레임만 오면 빈 답변이 `resolved`로 저장된다. 근거 Scenario: "a parseable frame whose `choices`, `delta`, or `content` has an unexpected type ... the stored turn has status `error`", Requirement: "MUST NOT persist partial generated text as a resolved answer". 제안: 키 부재와 `null`만 허용 값으로 두고 나머지는 타입을 검사한다. `content: null`을 허용하는 `:452`와 같은 형태다. `test_ask_router.py:543`의 매개변수에 `{"choices":0}`, `{"choices":[{"delta":0}]}`, `{"choices":[{"delta":[]}]}`를 추가한다.

2. **준비 실패 Scenario의 일부를 테스트가 고정하지 않는다.** Scenario는 "retrieval, evidence content lookup, template selection, or prompt rendering"을 나열하고 "the provider is not called"를 요구한다. `test_ask_router.py:612`의 매개변수는 근거 조회와 템플릿 조회만 다루어 **프롬프트 렌더 실패**가 없다. `:588`의 검색 실패 테스트는 공급자 호출 0회를 단언하지 않는다. `_post_ask_capturing_finalize`(`:239`)가 대역 스트림을 돌려주지 않기 때문이다. 동작은 프로브로 확인했다. 제안: 형식이 깨진 템플릿 행을 돌려주는 경우를 추가해 `context_unavailable`과 `fake_llm.calls == 0`을 단언하고, 검색 실패 쪽에도 호출 수 단언을 추가한다.

3. **실제 배선과 게이트의 세부를 고정하는 테스트가 없다.** 코드는 맞으며 지워도 테스트가 실패하지 않는다. 근거 Scenario: "Ask 턴을 내보낸다", "A non-member queries another workspace", "A member queries their workspace".
   - (a) `apps/worker/src/worker/__main__.py:255`의 라우트 등록. `test_worker_main.py:33`은 라우트를 단언하지 않고, `test_observability_e2e.py`와 `test_ask_turn_export.py`는 자체 앱에 등록한다. 빠지면 API는 404를 경고로만 남겨 턴 내보내기가 조용히 사라진다. 제안: `LLM_STREAM_INTERNAL_TOKEN`이 있을 때 리스너 앱에 `/internal/ask-turn-export`가 있음을 단언한다.
   - (b) `apps/api/src/api/routers/ask.py:77-81`의 기본 조립. 모든 테스트가 `app.state.ask_service`를 주입하므로 `_ask_service`의 기본 경로를 지나지 않는다. 제안: 기본 조립이 `HttpAskTurnExporter`를 넘기는지 단언한다.
   - (c) `test_tenant_isolation_full_path.py:564`의 비멤버 경우에 `response.json() == {"detail": "forbidden"}`을 추가하고, `:592` 대조군에 viewer를 추가한다.

## 범위 밖 관찰

- 위조·만료 토큰의 401은 `errors.py:252-254`의 단일 지점이라 전 라우트에 적용된다. delta spec의 Scenario는 `/retrieval`만 다루지만 범위는 `design.md:188`의 결정대로이며, 결정을 다시 묻지 않는다. 아카이브 뒤에는 `design.md`가 현재 계약이 아니므로, 전 라우트 계약으로 남기려면 다음 스펙 동기화 때 Requirement로 옮기는 편이 낫다.
- `RESUME.md`는 호출자 안내대로 판정 대상에서 뺐다.
- 관련 pytest가 로컬 스택에 만든 데이터는 픽스처가 지웠다. 실행 후 `ask_messages`는 0행이다.

## 판정 근거

`needs_fix`다. 항목 1은 Scenario의 THEN과 Requirement의 MUST NOT이 코드에서 어긋나고, task 1.1이 `- [x]`이며, 두 줄의 기본값 처리와 테스트 매개변수로 해결된다. 항목 2와 3은 테스트 추가로 끝난다. 1라운드의 조치 항목 중 2, 3, 5는 완전히 해소됐고, 항목 4는 결정대로 보류 상태이며 그 누락을 막는 테스트가 실제로 실패함을 확인했다. 새로 추가된 시나리오(멤버십 게이트, 청구된 응답 거부, 헤더 없는 질의 임베딩, 턴 내보내기, 내부 라우트 인증, 범위 밖 보고서 값, 경계 내림, trace 고정)는 전부 동작이 충족된다. 스펙을 고쳐야 할 항목이나 사람의 결정이 필요한 항목이 없어 `blocked`가 아니다.
