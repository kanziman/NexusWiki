# Spec Conformance 리뷰 — ai-control-flow-accounting r1

- 판정: needs_fix
- 대상: 기준 커밋 `79b68fe` 대비 커밋되지 않은 작업 트리 (`git diff 79b68fe` + 새 파일)
- 일시: 2026-11-02T17:04:59+09:00

## 요약

46개 Scenario 중 43개는 충족이다. 미충족은 Scenario 3개(부분 미충족 2개, 커밋 전 한정 1개)이고, Scenario에 직접 걸리지 않는 Requirement 본문 미충족이 2건 더 있다. 스펙을 바꿀 필요 없이 코드와 테스트로 해결된다. 조치 항목은 5개다.

- 스펙 밖 동작: 찾지 못했다.
- 조용한 범위 축소: 조치 항목 1, 2, 3이 해당한다. task 1.1, 3.1, 5.2는 `- [x]`이지만 명세 동작 일부가 빠져 있다.
- 미검증 완료 주장: 조치 항목 5가 해당한다. 동작은 실측으로 확인했으나 고정하는 테스트가 없다.

## 이번 라운드에서 직접 실행한 검증

| 항목 | 결과 |
| --- | --- |
| 이 change의 관련 pytest 20개 파일 (로컬 스택 포함) | 257건 통과 |
| 전체 pytest | 712건 통과, 1건 실패, 수집 오류 1건. 실패는 `test_cross_tenant_ingest_is_forbidden_with_a_fixed_body[file]`, 수집 오류는 `apps/worker/tests/test_transcript.py`로 호출자가 알린 것과 같다 |
| `vitest` `ControlRoom` · `ControlledAiShowcase` · `AskConversation` | 27건 통과 |
| `supabase/tests/0023_job_trace.sql` | `job_trace: ok`, 롤백 |
| `openspec validate ai-control-flow-accounting --strict` | valid |
| 로컬 DB 마이그레이션 최신 번호 | `0026` |
| 실제 스택에서 `process_next_job`으로 수집 체인 전체 실행 (스크래치 프로브) | 아래 "실측" 참고 |
| 기준 커밋 코드(`git archive 79b68fe`)로 증거 시나리오 재측정 | `step1.json`의 `before` 값과 전부 일치 |
| 현재 코드로 증거 시나리오 재측정 | `step1.json`의 `after` 값과 전부 일치 |

호출자 제공 사실로 인용하고 재실행하지 않은 것: 프로덕션 빌드의 브라우저 네트워크 실측, 대시보드 전체 462건, 위 두 실패가 기준 커밋에서도 나타난다는 사실. 프로덕션 빌드 산출물은 `apps/dashboard/.next/prerender-manifest.json`에 `/showcase/controlled-ai`가 정적 라우트로 있고 `.next/server/app/showcase/controlled-ai.html`이 있는 것까지 확인했다.

## 시나리오 판정

### ai-control-room

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Control Room 추적 탭 / 완료된 trace 상세 | 충족 | API `apps/api/src/api/routers/control.py:332-367`, `:369-383`, 합계 `:260-266` · 화면 `apps/dashboard/components/ControlRoom.tsx:366-476` · 테스트 `apps/api/tests/test_control_router.py:139`, `apps/dashboard/tests/ControlRoom.test.tsx:130` |
| Control Room 추적 탭 / 진행 중인 수집 trace | 충족 | `control.py:203-238`, `ControlRoom.tsx:428-441` · 테스트 `test_control_router.py:323`, `ControlRoom.test.tsx:168`. 참고: `:225` 대기 판정이 type 기준이라, 원문 `embed` 행이 있으면 아직 없는 위키 `embed` 단계는 대기로 표시되지 않는다. 세 상태의 구분 자체는 충족한다 |
| Control Room 추적 탭 / 데이터가 없는 워크스페이스 | 충족 | `ControlRoom.tsx:269-276` · 테스트 `ControlRoom.test.tsx:119` |
| (본문) 상세 표시 항목: Router 결정, 최종 상태 | **미충족** | 조치 항목 3 |
| (본문) 이후 탭은 지어낸 수치 없음 | 충족 | `ControlRoom.tsx:247-258` · 테스트 `ControlRoom.test.tsx:218` |
| (본문) 운영 환경 동작 | 확인 불가 | 환경 분기는 없다 (`apps/dashboard/app/w/[workspaceId]/control/page.tsx:8-11`). 클라우드 마이그레이션 미적용이라 운영 실측은 불가능하다 |
| 작성자와 역할 / 작성자가 자신의 Ask trace를 본다 | 충족 | `control.py:326-333`, RLS `supabase/migrations/0018_ask_history.sql:98` · 테스트 `test_control_router.py:139` |
| 작성자와 역할 / editor가 다른 멤버의 Ask trace를 요청한다 | 충족 | `control.py:369-386` · 테스트 `test_control_router.py:201`. 부재와 응답이 같음을 단언한다. 테스트의 요청자는 owner이고 editor도 같은 분기를 지난다 |
| 작성자와 역할 / viewer가 탭을 연다 | 충족 | `control.py:287-315`, `ControlRoom.tsx:158-164` · 테스트 `test_control_router.py:224`, `ControlRoom.test.tsx:151` |
| 작성자와 역할 / 다른 워크스페이스의 trace | 충족 | `control.py:287-288`, `:386`, `supabase/migrations/0026_ask_trace_aggregate.sql:36` · 테스트 `test_control_router.py:251` |
| 작성자와 역할 / 멤버십을 잃은 작성자 | 충족 | RLS의 `is_workspace_member` (로컬 `pg_policy`에서 확인) · 테스트 `test_control_router.py:273` |
| (본문) 요청자 JWT만 사용 | 충족 | `control.py:89-96`의 `UserDb`만 사용 |
| Ask 집계 / editor가 집계를 본다 | 충족 | 반환 컬럼 `0026_ask_trace_aggregate.sql:18-28`, `control.py:403-414` · 테스트 `test_control_router.py:362` |
| 허용 목록 / 실패한 호출을 포함한 trace | 충족 | `control.py:47-53`, `:106-112`, `:241-257` · 테스트 `test_control_router.py:168`, `:296` |

### ai-controls-showcase

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 합성 증거만 쓰는 쇼케이스 / 익명 방문자의 접속 | 충족 | `apps/dashboard/app/showcase/controlled-ai/page.tsx:18`, matcher `apps/dashboard/middleware.ts:81`, 프리패치 차단 `apps/dashboard/components/ControlledAiShowcase.tsx:66` · 테스트 `apps/dashboard/tests/ControlledAiShowcase.test.tsx:82`, `:90`, `:101`, `:107` · prerender manifest와 호출자의 브라우저 실측 |
| 합성 증거만 쓰는 쇼케이스 / 로그인 세션이 있는 방문자 | 충족 | 미들웨어 대상 아님, 루트 레이아웃도 세션을 읽지 않음 (`apps/dashboard/app/layout.tsx:61-70`) · 테스트 `ControlledAiShowcase.test.tsx:90`, `:101` |
| 재현 가능한 증거 / 충돌 판정 비용 누락의 전후 비교 | **미충족 (커밋 전 한정)** | 비용과 시나리오, 수정 전 커밋은 충족 (`ControlledAiShowcase.tsx:127`, `:133` · 테스트 `:33`). 수정 후 커밋은 `apps/dashboard/content/controlled-ai/step1.json:38`의 `uncommitted`이고 화면에 "커밋 전"으로 표시된다 (`ControlledAiShowcase.tsx:56-57`, `:139-140`). 조치 항목 4 |
| 재현 가능한 증거 / 증거 파일의 내용 검사 | 충족 | `apps/worker/tests/test_controlled_ai_evidence.py:538-554`, 정규식 자체 검증 `:557-571` |
| 재현 가능한 증거 / 아직 구현되지 않은 단계 | 충족 | `ControlledAiShowcase.tsx:159` · 테스트 `ControlledAiShowcase.test.tsx:67`, `test_controlled_ai_evidence.py:531` |
| (본문) 합성 명시, 시나리오 생성 | 충족 | `ControlledAiShowcase.tsx:78` · 테스트 `ControlledAiShowcase.test.tsx:25` · 생성기 `test_controlled_ai_evidence.py:422-426`, `:462`, 값 대조 테스트 `:502`. 재측정 일치 |

### ai-request-tracing

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 서버 발급 / 일반 요청 | 충족 | `packages/core/src/nexuswiki_core/trace.py:106`, `:142-148`, `packages/core/src/nexuswiki_core/logging.py:85` · 테스트 `apps/api/tests/test_trace_middleware.py:54`, `:123` |
| 서버 발급 / 클라이언트가 trace 값을 위조한다 | 충족 | `trace.py:151-158`, API는 `trust_inbound` 미사용 (`apps/api/src/api/main.py`) · 테스트 `test_trace_middleware.py:73` |
| 서버 발급 / 오류 응답 | 충족 | `trace.py:125-139` · 테스트 `test_trace_middleware.py:82`, `:91`, `:104` |
| 내부 호출 전파 / Ask 요청 한 건 | 충족 | 헤더 `apps/api/src/api/services/ask.py:117`, `apps/api/src/api/services/retrieval.py` `embed`, 워커 `apps/worker/src/worker/__main__.py:196-198`, 턴 `apps/api/src/api/routers/ask.py:96`, `supabase/migrations/0025_ask_trace.sql:125`, 사용량 `apps/worker/src/worker/llm_gateway.py:193` · 테스트는 구간별이다: `test_trace_middleware.py:143`, `:168`, `apps/worker/tests/test_query_embedding.py:48`, `apps/worker/tests/test_llm_stream.py:52`, `apps/worker/tests/test_worker_main.py:171`, `apps/api/tests/test_ask_router.py:333` |
| 내부 호출 전파 / 내부 호출 호환성 | 충족 | `trace.py:151-158` · 테스트 `test_query_embedding.py:73`, `test_worker_main.py:207` |
| 잡 체인 / 수집 체인 완료 | 충족 (테스트 공백) | `supabase/migrations/0023_job_trace.sql:102-108`, `apps/worker/src/worker/db/service.py:173`, `apps/worker/src/worker/handlers/parse.py:237`, `apps/worker/src/worker/queue.py:241` · 테스트 `supabase/tests/0023_job_trace.sql:113`, `apps/api/tests/test_sources_router.py` (`test_enqueued_parse_job_keeps_the_trace_of_the_request`), `apps/worker/tests/test_queue.py:297` · 실측으로 6단계 잡과 사용량 행의 값이 같음을 확인. 조치 항목 5 |
| 잡 체인 / 실패한 잡의 재시도 | 충족 (테스트 공백) | 해당 함수가 `trace_id`를 쓰지 않음 · 테스트 `supabase/tests/0023_job_trace.sql:145`. 제목은 회수를 포함하지만 `reap_stale_jobs`를 호출하지 않는다. 롤백 트랜잭션 실측으로 값 유지를 확인. 조치 항목 5 |
| 잡 체인 / 이미 큐에 있는 대상의 중복 인큐 | 충족 | `0023_job_trace.sql:179-191` · 테스트 `supabase/tests/0023_job_trace.sql:46` |
| 잡 체인 / trace가 없던 기존 잡 | 충족 | `queue.py:240-241` · 테스트 `test_queue.py:318`, `supabase/tests/0023_job_trace.sql:174` · 실측에서 값 없는 체인이 정상 완료 |
| Router shadow / 제목과 정확히 일치하는 질문 | 충족 | `apps/api/src/api/services/ask.py:530`, `packages/core/src/nexuswiki_core/router.py:57` · 테스트 `test_ask_router.py:299`, `packages/core/tests/test_router.py:41` |
| Router shadow / 근거가 없는 질문 | 충족 | `router.py:65`, `ask.py:542-572` · 테스트 `test_ask_router.py:163`, `:321` |
| Router shadow / 내용이 같은 원문의 재컴파일 | 충족 | `apps/worker/src/worker/handlers/compile.py:148`, `:153`, `:173`, `service.py:455` · 테스트 `apps/worker/tests/test_handlers.py:841`, `test_queue.py:1071` · 실측에서 `SKIP_UNCHANGED` 기록과 LLM 호출을 함께 확인 |
| 본문 금지 / 고유한 문자열이 담긴 Ask와 컴파일 | 충족 | `llm_gateway.py:202`, `ask.py:393-416`, `packages/core/src/nexuswiki_core/observability.py:70-80`, `:310-323` · 테스트 `apps/api/tests/test_observability_e2e.py:71` |
| 외부 내보내기 / 자격 증명이 없다 | 충족 | `observability.py:108-110` · 테스트 `packages/core/tests/test_observability.py:90`, `:99`, `apps/worker/tests/test_settings.py:118` |
| 외부 내보내기 / 외부 서비스 장애 | 충족 | `observability.py:285-300` · 테스트 `test_observability.py:285`, `apps/worker/tests/test_observability_export.py:103`, `test_queue.py:1251` |
| 외부 내보내기 / 프로세스 종료 | 충족 | `observability.py:239-267`, `__main__.py:390-393` · 테스트 `test_observability.py:306`, `test_worker_main.py:222` |
| (본문) 해시 전송과 키 마스킹 | 충족 | `observability.py:303-307`, `logging.py:36` · 테스트 `test_observability.py:152`, `packages/core/tests/test_logging_redaction.py:48` |

### grounded-answering

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 스트림 종결 / Provider stream contains a malformed frame | **부분 미충족** | 잘린 JSON은 충족 (`ask.py:365-368`, `:666-689` · 테스트 `test_ask_router.py:374`). JSON으로는 읽히지만 형태가 틀린 프레임은 턴이 종결되지 않는다. 조치 항목 1 |
| 스트림 종결 / Provider reports an error mid-stream | 충족 | `ask.py:369-375`, `:666-689` · 테스트 `test_ask_router.py:401` |
| (본문) 시작된 모든 턴의 종결 | **미충족** | 근거 조회와 템플릿 렌더 실패. 조치 항목 1 |
| 인용 지표 / A sentence cites only fabricated anchors | 충족 | `ask.py:173-185` · 테스트 `apps/api/tests/test_ask_citations.py:28`, 저장 `test_ask_router.py:270` |
| 인용 지표 / Anchor follows the period | 충족 | `packages/core/src/nexuswiki_core/sentences.py:26`, `:40` · 테스트 `test_ask_citations.py:37`, `packages/core/tests/test_sentences.py:26`, `:34` |
| 부분 검색 / One retrieval channel fails | 충족 | `ask.py:419-429`, `:621`, `apps/dashboard/components/AskConversation.tsx:392-393`, `:606` · 테스트 `test_ask_router.py:436`, `:446`, `apps/dashboard/tests/AskConversation.test.tsx:289` |
| 부분 검색 / Graph channel is disabled | 충족 | `ask.py:425-429` · 테스트 `test_ask_router.py:436`, `:457` |

### hybrid-retrieval

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 4채널 / All retrieval channels are available | 충족 | `apps/api/src/api/services/retrieval.py:155-164` · 테스트 `apps/api/tests/test_retrieval_service.py:150` |
| 4채널 / A policy enables graph expansion | 충족 | `retrieval.py:155-160`, `:236-268` · 테스트 `test_retrieval_service.py:167` |

### usage-guardrails

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| 사용량 기록 / Provider reports successful billable usage | **부분 미충족** | 정상 응답은 충족 (`llm_gateway.py:175-204` · 테스트 `apps/worker/tests/test_llm_gateway.py:108`, `:162`). 공급자가 사용량을 보고했는데 응답 판독이나 검증에서 실패하는 일부 경로는 기록이 없다. 조치 항목 2 |
| 사용량 기록 / Structured output is retried after a validation failure | 충족 | `apps/worker/src/worker/llm.py:246-260` · 테스트 `test_llm_gateway.py:82` · 재측정 `compile_retry_cost` |
| 사용량 기록 / Every structured attempt fails | 충족 | 스키마 검증 실패에 한해 충족. `test_llm_gateway.py:95` |
| 사용량 기록 / Conflict judgement calls the provider | 충족 | `apps/worker/src/worker/handlers/conflict.py:103` · 테스트 `test_handlers.py:709` · 재측정 `conflict_judge_cost` |
| 사용량 기록 / Ask stream is aborted | 충족 | `apps/worker/src/worker/llm_stream.py:135-153`, `:155-171`, `llm_gateway.py:147-172` · 테스트 `test_llm_stream.py:315`, `:331`, `:357`, `test_llm_gateway.py:201` |
| 사용량 기록 / Query embedding completes | 충족 | `__main__.py:59-93`, `apps/worker/src/worker/query_embedding.py:131-139` · 테스트 `test_worker_main.py:171`, `:194` |
| 사용량 기록 / Job is retried after usage was recorded | 충족 (테스트 공백) | `service.py`의 `insert_usage_event`가 upsert 없는 INSERT다 (`_insert_many` 기본 인자). 같은 호출을 재시도해 행이 쌓임을 단언하는 전용 테스트는 찾지 못했다. 시도별 행 테스트 `test_llm_gateway.py:82`가 가장 가까운 근거다. 조치 항목 5 |

## task 7.3 판단: `uncommitted`가 "생성 커밋" 요구를 어기는가

**현재 작업 트리 기준으로는 어긴다. 다만 구현 결함은 아니다.**

- 어기는 이유: Requirement는 "생성 커밋"을 담으라고(MUST) 하고 Scenario는 값을 만든 "커밋이 표시된다"고 한다. `uncommitted`는 커밋이 없다는 표시이므로 수정 후 측정값의 출처를 커밋으로 되짚을 수 없다.
- 구현 결함이 아닌 이유: 생성기(`test_controlled_ai_evidence.py:429-459`)와 화면(`ControlledAiShowcase.tsx:139-143`)은 해시가 있으면 그대로 동작한다. 더러운 트리에서 HEAD를 적지 않는 선택도 스펙의 "그 값을 만든 커밋"에 더 충실하다. 7.3이 `- [ ]`로 남아 있고 7.1에서의 분리도 tasks에 적혀 있어 조용한 축소도 아니다.
- 스펙 변경이 필요 없으므로 `blocked`가 아니다. 커밋 전에는 해소할 수 없으므로, 공개되기 전에 끝내야 하는 조건으로 다룬다.

남은 위험은 두 가지이고, 둘 다 조치 항목 4에 담았다.

1. **잊어도 아무것도 막지 않는다.** `test_controlled_ai_evidence.py:524`가 `uncommitted`를 계속 허용하므로, 7.3을 건너뛰어도 테스트와 빌드가 통과해 운영 화면에 "커밋 전"이 나간다.
2. **squash merge와 맞지 않는다.** 이 저장소는 squash merge를 쓴다 (`.claude/commands/create-pr.md:33`). task 7.3의 절차대로 PR 브랜치에서 해시를 기록하면 병합 뒤 그 해시는 `main`의 이력에 없다. 7.3의 Then은 이 경우를 다루지 않는다.

## 실측

스크래치 프로브로 얻은 값이다. 저장소 파일은 바꾸지 않았다.

수집 체인 (`process_next_job`, 실제 로컬 스택, 공급자만 대역):

```text
parse / embed(source) / compile / link_sync / embed(wiki) / conflict_check → 전부 같은 trace_id
usage: embed_source, compile(STANDARD), embed_wiki → 같은 trace_id
trace 없는 compile 재인큐 → 체인 정상 완료, compile 사용량에 SKIP_UNCHANGED 기록, LLM 호출 있음
```

Ask 종결 (`AskService.ask`, 대역 DB):

```text
잘린 JSON                 → citations, done / status=error        정상
{"choices":["x"]}         → AttributeError / 종결 없음
{"choices":5}             → TypeError / 종결 없음
{"choices":[{"delta":"x"}]}             → AttributeError / 종결 없음
{"choices":[{"delta":{"content":1}}]}   → delta 후 TypeError / 종결 없음
근거 조회 전송 실패       → ConnectTimeout / 종결 없음
템플릿 렌더 실패          → ValueError / 종결 없음
```

게이트웨이 (`LlmGateway`, 공급자가 `usage.cost=0.002`를 보고):

```text
embed 정상                → 1행, 2000 micros
embed 공급자 불일치       → EmbeddingProviderMismatch / 0행
embed 차원 불일치         → ValueError / 0행
LLM choices 빈 배열       → ProviderError / 0행
LLM content null          → ProviderError / 0행
```

## 조치가 필요한 항목

1. **형태가 틀린 프레임과 스트림 전 실패에서 Ask 턴이 종결되지 않는다.** `apps/api/src/api/services/ask.py:357-376`의 `_delta_text`는 JSON 파싱 실패와 최상위 비객체만 잡는다. `choices`나 `delta`의 형태가 틀리면 `AttributeError`·`TypeError`가 `:666`의 `except (RuntimeError, httpx.HTTPError)`를 지나쳐 올라가고, `content`가 문자열이 아니면 `:692`의 `join`에서 try 밖의 `TypeError`가 난다. `:574-611`의 근거 조회와 템플릿 렌더 실패도 try 밖이다. 어느 경우든 클라이언트는 `citations`와 `done`을 받지 못하고 턴은 `streaming`으로 남으며, 대시보드는 `AskConversation.tsx:206-218`에서 그 턴을 800ms마다 계속 폴링한다. 근거: "The system MUST finish every started Ask turn with a terminal state", "A malformed provider frame ... MUST end the turn with the `llm_unavailable` error outcome". 제안: `_delta_text`에서 `choices[0]`, `delta`, `content`의 타입을 확인해 `_AnswerStreamFailed`로 보낸다. 근거 조회와 렌더 구간도 오류 종결로 수렴시킨다. 형태별 프레임과 두 구간을 `test_ask_router.py`에 추가한다.

2. **공급자가 사용량을 보고했는데 기록되지 않는 경로가 남았다.** `apps/worker/src/worker/llm.py:246`의 `_read_completion`이 빈 `choices`나 `content: null`에서 예외를 던져 `:247`의 `on_attempt`에 닿지 못한다. `apps/worker/src/worker/embedding.py:64-70`은 공급자 불일치와 차원 불일치에서 `:72`의 비용 계산 전에 예외를 던지고, 게이트웨이의 기록(`llm_gateway.py:119`)은 정상 반환 뒤에만 돈다. 근거: "SHALL record provider usage for every billable generation and embedding provider call", design D4 "검증보다 먼저이므로 전 시도가 실패해도 비용이 남는다", Goals의 "이후의 어떤 실패에도 사라지지 않게". 부수적으로 Router 결정도 사용량 메타데이터에 실리므로(`compile.py:173`) 이 경로의 컴파일 잡에는 결정 기록이 남지 않는다. 제안: 사용량 판독을 내용 검사와 분리해 어떤 판독 실패보다 먼저 기록한다. 임베딩도 같은 순서로 바꾼다. 각 실패 경로의 비용이 남는 테스트를 `test_llm_gateway.py`에 추가한다.

3. **Control Room 상세가 수집 trace의 Router 결정과 최종 상태를 보여주지 않는다.** 수집 trace는 `control.py:198`에서 `route: None`이고, 호출별 값은 `control.py:250`이 돌려주지만 `apps/dashboard/components/ControlRoom.tsx:49-59`의 `Call` 타입과 `:447-456`의 표에 그 필드가 없다. 그래서 컴파일 결정(`SKIP_UNCHANGED`, `TRUNCATED`, `STANDARD`)이 화면 어디에도 나오지 않는다. 최종 상태도 `TraceDetailView`(`:366-476`)에 없고 목록 항목의 배지(`:297-301`)에만 있다. 근거: "trace 상세는 ... Router 결정, 시도 횟수, 최종 상태를 SHALL 보여준다". 제안: 호출 표에 결정 열을 추가하고 상세 머리에 상태를 표시한다. `ControlRoom.test.tsx`에 두 표시의 단언을 추가한다.

4. **공개 증거의 `after.commit`이 아직 커밋이 아니다 (task 7.3).** 근거 Scenario: "수정 전후의 기록 비용과 그 값을 만든 시나리오 이름, 커밋이 표시된다". 제안: (a) 커밋 후 7.3 절차로 재생성한다. (b) 재생성과 함께 `test_controlled_ai_evidence.py:524`에서 `uncommitted`를 빼서 이후 회귀를 막는다. `ControlledAiShowcase.test.tsx:58`의 커밋 전 테스트도 함께 정리한다. (c) squash merge 뒤의 해시를 어떻게 다룰지 정한다. 아래 "사람의 확인이 필요한 사항"을 본다.

5. **동작은 맞지만 테스트로 고정되지 않은 완료 주장.** 실측으로 동작은 확인했다. 제안: (a) `parse`가 직접 인큐하는 `embed` 잡의 trace 상속 테스트를 추가한다. `service.py:173`의 분기를 지나는 테스트가 없고, `PipelineHarness.drain`은 trace를 묶지 않으며 `conflict_check`를 실행하지 않는다. (b) 전 단계 잡과 사용량 행의 trace가 같음을 단언하는 체인 테스트를 추가한다. 근거 Scenario: "수집 체인 완료". (c) `supabase/tests/0023_job_trace.sql:145` 계약 5에 `reap_stale_jobs` 호출을 추가한다. 제목이 회수를 말하지만 실행하지 않는다. 근거 Scenario: "실패한 잡의 재시도". (d) 같은 잡의 재실행이 앞선 사용량 행을 덮어쓰지 않음을 단언한다. 근거 Scenario: "Job is retried after usage was recorded".

## 사람의 확인이 필요한 사항

판정을 `blocked`로 올리지는 않았지만 결정이 필요한 두 가지다.

- **클라이언트 연결 끊김.** 델타 수신 뒤 스트림이 닫히면 `ask.py:664-665`가 `CancelledError`를 다시 던지거나 제너레이터가 닫혀 턴이 `streaming`으로 남는다. 실측으로 확인했고, 기준 커밋에도 있는 동작이다. "every started Ask turn"을 문자 그대로 읽으면 미충족이지만, Requirement 제목이 "failed answer streams"이고 design D6과 Scenario가 공급자 실패만 다루므로 이번 판정에서는 미충족으로 세지 않았다. 범위 밖이라면 문장을 좁히고, 범위 안이라면 후속 작업으로 분리하는 결정이 필요하다.
- **squash merge 뒤의 `after.commit`.** 선택지는 (가) 병합 후 `main` 해시로 후속 PR에서 갱신, (나) PR 브랜치 해시를 그대로 공개하고 그 의미를 받아들임이다. (가)면 7.3은 PR 병합 뒤에 끝나므로 아카이브 시점이 달라진다. 현재 게이트는 PR 직전에 돌지만 7.3은 커밋 뒤에만 끝나므로, 7.3 하나만 남은 경우 어느 시점에 게이트를 통과시킬지도 함께 정해야 한다.

## 범위 밖 관찰

- 작업 트리에 이 change와 무관해 보이는 변경이 있다: `docs/ref/ref0.png`와 `docs/ref/ref2.png` 삭제, 추적되지 않은 `skills-lock.json`. 스펙 판정 대상은 아니지만 커밋 범위를 정할 때 확인이 필요하다.
- 메인 스펙 `openspec/specs/hybrid-retrieval/spec.md:9`의 5채널 제목은 `/opsx:sync` 전의 정상 상태다.

## 판정 근거

`needs_fix`다. 항목 1, 2, 3은 Requirement가 MUST·SHALL로 요구한 동작이 코드에서 빠졌고, 해당 task가 `- [x]`이며, 스펙을 고치지 않고 코드로 해결된다. 항목 4는 커밋 후 해소되고 항목 5는 테스트 추가로 끝난다. 테넌트 경계와 접근 판정의 스펙 시나리오는 전부 충족이다. 스펙 자체의 모순으로 진행이 막히는 항목은 없어 `blocked`가 아니다.
