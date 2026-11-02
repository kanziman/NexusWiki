# Design — ai-control-flow-accounting

## Context

동기는 `proposal.md`의 "Why"를, 요구사항은 이 change의 delta spec을 본다. 여기서는 접근을 정하는 현재 제약만 적는다.

- LLM 호출 함수는 `worker.llm`의 `complete_structured`·`stream_chat`, 임베딩은 `worker.embedding`의 `embed_texts`뿐이다. 공급자 키는 워커에만 있다.
- API는 `service_role`을 쓸 수 없다. API가 저장하는 값은 요청자 JWT로 호출하는 RPC를 타야 한다.
- `ask_messages`는 작성자 전용 RLS이고, `jobs`·`usage_events`는 멤버 전체가 SELECT할 수 있다.
- `jobs`는 완료 시 `locked_at`을 지우므로 시작 시각이 남지 않는다. 종료 시각은 `updated_at` 트리거로 알 수 있다.
- `retry_dead_job`은 새 행을 만들지 않고 같은 행을 되살리므로 `trace_id`가 그대로 유지된다.
- 내부 경계의 요청 모델은 `extra="forbid"`다. `QueryEmbeddingRequest`는 `text`만 받아 `workspace_id`를 모른다.
- `middleware.ts`의 matcher는 `/w/:path*`, `/login`, `/signup`, `/`뿐이라 새 공개 라우트는 인증 미들웨어를 지나지 않는다.
- Vercel Root Directory는 `apps/dashboard`이므로, 대시보드가 읽을 파일은 그 아래에 두는 것이 가장 단순하다.
- 그래프 채널은 이미 `_disabled_meta`로 보고된다. 4채널 정정에는 검색 코드 변경이 필요하지 않다.

## Goals / Non-Goals

**Goals:**

- 요청 하나를 추가 전용 스키마 변경만으로 끝까지 추적한다.
- 공급자가 보고한 모든 비용을 공급자 호출 직후 기록해, 이후의 어떤 실패에도 사라지지 않게 한다.
- Ask 작성자 경계를 새 정책을 만들지 않고 기존 RLS로 지킨다.
- 이후 Step이 게이트웨이와 `control_report`에 값을 더하는 것만으로 화면까지 연결되게 한다.

**Non-Goals:**

- 프롬프트 크기 제한, 근거 쿼터, `max_tokens` 지정(Step 2).
- 재시도 횟수 변경, 코드 펜스 처리, 의미 검증, Ask 수리, 결정론적 Fallback(Step 3). 3회 시도는 그대로 두고 비용만 빠짐없이 기록한다.
- 공통 정책 주입, `data_collection` 강제, 위키 쓰기 분류, Evaluator-Optimizer(Step 4).
- Router 결정의 실행. `NO_EVIDENCE` 외의 결정은 기록만 하며 LLM 호출을 건너뛰지 않는다.
- 그래프 채널 활성화와 `RetrievalPolicy` 변경.
- 중단된 스트림의 비용을 공급자 생성 ID로 사후 대조하는 작업. 이번에는 `incomplete` 표시로 드러내기만 한다.
- `usage_events`의 Ask 행을 작성자 전용으로 바꾸는 작업. 예산 합계 경로까지 바뀌므로 범위 밖이다.
- 기존 잡과 사용량 행의 `trace_id` 백필, trace 보관 기간 정책, OpenTelemetry 도입, Langfuse 자체 호스팅과 평가 데이터셋.
- 공개 쇼케이스에 운영 수치를 싣는 일.

## Decisions

### D1. 저장 구조: 기존 행 확장 후 읽을 때 조립 (Gate 2 승인)

`jobs`, `usage_events`, `ask_messages`에 컬럼을 추가하고 조회 API가 조립한다.

- `jobs`: `trace_id uuid`, `last_claimed_at timestamptz`
- `usage_events`: `trace_id uuid`, `duration_ms int`. 호출 종류, 시도 번호, `incomplete`, Router 결정은 본문 없는 값만 허용하는 기존 `metadata`에 둔다.
- `ask_messages`: `trace_id uuid`, `control_report jsonb`. 남용을 막기 위해 크기 CHECK를 둔다.
- 조회용 부분 인덱스 `(workspace_id, trace_id) where trace_id is not null`을 `jobs`와 `usage_events`에 둔다.

기각한 안:

- **전용 span 테이블**: 작성자 컬럼과 2단계 RLS를 새로 구현해야 하고, 구현 실수가 곧 격리 사고가 된다. 원본 행과 이중 기록되어 어긋날 수 있다.
- **trace당 요약 1행**: API와 워커가 같은 행을 갱신해 at-least-once 재실행에서 병합 규칙이 필요하다.

구간별 분석이 부족해지면 전용 span 테이블을 추가 전용으로 얹을 수 있다.

### D2. trace 발급과 전파

core에 contextvars 기반 trace 컨텍스트를 두고 structlog에 병합한다. API는 순수 ASGI 미들웨어로 값을 발급한다.

- `BaseHTTPMiddleware`는 쓰지 않는다. 스트리밍 응답에서 컨텍스트 전파와 취소 동작이 불안정할 수 있기 때문이다.
- `ServerErrorMiddleware`는 사용자 미들웨어 바깥에 있어서, 처리되지 않은 500은 미들웨어의 `send`를 지나지 않는다. 응답이 시작되기 전의 예외는 미들웨어가 직접 500을 보내고 다시 던지며, 이를 테스트로 고정한다. 처음에는 전역 예외 핸들러를 계획했지만 `api.errors`가 넓은 `Exception` 핸들러를 금지하므로 구현 중 변경했다.
- CORS `expose_headers`에 `X-Trace-Id`를 추가한다.
- 내부 호출은 본문이 아니라 `X-Trace-Id` 헤더로 전달한다. `extra="forbid"` 모델에 필드를 추가하면 배포 순서에 따라 422가 나기 때문이다. 내부 호출은 토큰으로 인증되므로 값을 신뢰하고, 없으면 워커가 발급한다.
- 잡은 `process_next_job`이 `job.trace_id`를 `job_id`와 함께 컨텍스트에 묶는다. `clear_job_context`가 전부 지우므로 수명이 일치한다.

### D3. 잡 체인 상속은 SQL이 맡는다

`complete_job_and_chain`이 `v_job.trace_id`를 후속 잡에 복사한다. 핸들러 다섯 곳의 `next_payload`에 넣는 방식은 하나만 빠져도 조용히 끊기므로 기각한다.

- `enqueue_source_job`, `start_ask_turn`, `finalize_ask_turn`은 인자를 기본값과 함께 추가한다. 기존 시그니처를 DROP한 뒤 다시 만들고 GRANT를 재발행한다. 오버로드가 남으면 PostgREST 호출이 모호해진다.
- 기본값 덕분에 기존 코드의 이름 있는 호출은 마이그레이션 후에도 그대로 동작한다.
- `parse`가 직접 인큐하는 `embed` 잡은 컨텍스트의 값을 행에 싣는다.
- 원문 삭제가 만드는 Storage 정리 잡은 LLM과 무관하므로 값을 비워 둔다.
- `claim_job`은 `last_claimed_at`을 함께 갱신한다. `jobs`를 직접 UPDATE하지 않는 규칙을 지키는 변경이다.
- `start_ask_turn`은 저장된 `trace_id`를 함께 돌려준다. 같은 `client_turn_id`의 재전달은 기존 턴을 돌려주므로, API는 돌려받은 값을 컨텍스트에 다시 묶어 사용량과 턴을 같은 trace로 모은다.

### D4. `LlmGateway`는 동작을 바꾸지 않는 호출 경계다

`worker/llm_gateway.py`가 세 호출 함수를 감싸고 호출 맥락(워크스페이스, 잡, 호출 종류)을 받는다. 요청 본문과 재시도 흐름은 바꾸지 않는다.

- `complete_structured`에 시도별 콜백을 추가하고, 게이트웨이가 공급자 응답을 받은 **즉시** 사용량을 기록한다. 검증보다 먼저이므로 전 시도가 실패해도 비용이 남는다.
- `compile`과 `embed` 핸들러의 기존 `insert_usage_event`는 게이트웨이로 옮겨 이중 계상을 막는다. `conflict_check`는 이 경로로 처음 기록된다.
- 핸들러가 공급자 호출 함수를 직접 부르지 못하도록 구조 테스트로 고정한다.

기각한 안: 핸들러마다 기록 코드를 추가하는 방식은 `conflict_check`의 누락이 생긴 원인을 그대로 남긴다.

정책 주입 자리(Step 4)와 예산 자리(Step 2)는 이 경계에 생기지만, 이번 change에서는 비워 둔다.

### D5. 중단된 스트림과 질의 임베딩의 기록

- `LlmStreamService._stream_chunks`는 `try/finally`에서 `asyncio.shield`로 기록해 취소와 `aclose` 양쪽을 처리한다. 최종 usage를 받지 못하면 `metadata.incomplete=true`로 남긴다. 그 비용은 0으로 기록될 수 있음을 화면에 드러낸다.
- 질의 임베딩은 `X-Workspace-Id`, `X-Trace-Id` 헤더를 추가하고, `QueryEmbeddingClient.embed`가 `workspace_id`를 받는다. 기록은 응답 후 수행하며 실패는 로그만 남긴다. 헤더가 없는 이전 버전 호출은 기록을 건너뛰고 경고를 남긴다.

### D6. Ask 스트림의 종결과 인용 지표

- 깨진 프레임, `error` 필드, `finish_reason == "error"`를 `llm_unavailable` 오류 경로로 보낸다. 기존 오류 경로와 같이 답변 텍스트는 저장하지 않는다. 이미 화면에 표시된 델타는 오류 상태가 대체한다.
- 인용 지표는 `rendered_text`로 계산한다. `split_sentences`는 문장 부호 뒤의 앵커를 앞 문장에 붙인다.
- 지표는 `citations`가 아니라 `control_report`에 저장한다. 복원되는 턴의 `citations` 계약을 바꾸지 않기 위해서다.
- `missing_channels`는 `result.meta`에서 `status == "failed"`인 채널만 모아 `meta` 이벤트로 보낸다. `disabled`는 제외한다.

### D7. Router는 core의 순수 함수로 기록만 한다

- Ask 결정: `NO_EVIDENCE`, `LOOKUP`, `SINGLE_KIND`, `STANDARD`. `LOOKUP`은 정규화한 질의가 근거 메타데이터의 제목이나 slug와 일치하고, 위키와 원문 근거가 모두 있을 때다. 별칭은 현재 근거 메타데이터에 없어 이번 판정에서 제외한다. RRF가 처음 본 hit의 메타데이터만 유지하므로 벡터 채널이 먼저 잡은 위키에는 제목이 없을 수 있고, 이 경우 `LOOKUP`이 실제보다 적게 기록된다. 실행 여부를 정하는 Step 2에서 함께 다룬다.
- Compile 결정: `SKIP_UNCHANGED`, `TRUNCATED`, `STANDARD`. 지문은 원문 해시, 템플릿 식별자, 모델을 합쳐 만든다.
- 이전 지문은 해당 원문의 최근 컴파일 `usage_events.metadata`에서 읽는다. 읽기가 실패하면 `STANDARD`로 판정하며 잡을 실패시키지 않는다.

기각한 안: `raw_sources`에 지문 컬럼을 추가하는 방식은 Step 2에서 실행을 결정한 뒤 다시 검토한다.

### D8. 관측 내보내기

core의 `TraceRecorder`가 구간을 모아 `control_report`와 내보내기 양쪽에 전달한다. 내보내기는 Langfuse Python SDK를 지연 import하는 어댑터 하나로 둔다.

- 키가 없으면 SDK를 초기화하지 않는다. import에 부작용을 두지 않는 기존 규칙을 따른다.
- 입력과 출력을 싣지 않고, `mask`를 2차 방어선으로 둔다.
- Langfuse trace ID는 `create_trace_id(seed=trace_id)`로 만들고, 워크스페이스는 SHA-256 해시로 보낸다.
- 내보내기 호출은 모두 예외를 삼키고 경고만 남긴다.
- SIGTERM 경로의 flush는 3초로 제한한다. `WORKER_GRACE_SECONDS`를 소모하지 않게 하기 위해서다.
- `langfuse_secret_key`를 `REDACTED_KEYS`와 커플링 테스트에 추가한다.
- 키는 워커만 갖는다. API는 종결된 턴의 보고서를 `POST /internal/ask-turn-export`로 넘기며, `LLM_STREAM_INTERNAL_TOKEN`을 공유한다. 호출자와 경계가 LLM 스트림과 같기 때문이다. 처음에는 API에도 키를 두었으나, 같은 키로 SDK가 trace 읽기와 삭제를 노출해 API 침해가 RLS 바깥의 교차 테넌트 능력이 되므로 뒤집었다. `ApiSettings`의 "secret 필드 부재" 불변식도 이로써 그대로 유지된다. 내보내기는 응답과 분리한 태스크에서 2초 제한으로 보내므로 답변을 지연시키지 않는다. API가 그 사이에 종료되면 해당 턴의 사본은 사라지며, 원천인 Postgres에는 영향이 없다.

구현에서 확인해 반영한 사실은 다음과 같다. 대상은 `langfuse==4.18.0`이다.

- SDK는 구간 시작 시각을 소급 지정할 수 없다. 내보내는 순간에 관측 객체를 만들기 때문에 실제 소요 시간은 `duration_ms` 메타데이터로 보낸다.
- SDK의 `flush`에는 시간 제한이 없다. `shutdown`을 데몬 스레드에서 돌리고 `join(3초)`으로 기다린다. `shutdown`을 쓰는 이유는 SDK의 atexit 처리기를 먼저 해제해, 인터프리터 종료 시점에 제한 없는 flush가 다시 돌지 않게 하기 위해서다.
- 응답하지 않는 서버를 상대로 측정한 결과 flush는 2.05초에 돌아왔고, 프로세스는 기동을 포함해 3.67초 만에 종료되었다. SDK의 HTTP 타임아웃을 2초로 둔 결과다.
- flush는 큐 루프가 끝난 뒤에 돌므로 잡 반납을 지연시키지 않는다. 잡 종결 내보내기는 메모리 큐에 넣을 뿐 네트워크를 기다리지 않는다.
- SDK 기본 리전은 EU다. 지정을 잊어 다른 지역으로 전송되지 않도록 `LANGFUSE_BASE_URL`의 코드 기본값을 JP로 둔다.
- `trace_id`가 없는 작업(마이그레이션 이전 잡)은 이을 trace가 없어 내보내지 않는다.

기각한 안: OpenRouter Broadcast는 LLM 호출만 보여 검색, 큐, Router 구간이 빠진다.

### D9. Control Room API와 화면

`GET /workspaces/{id}/control/traces`, `GET .../control/traces/{trace_id}`, `GET .../control/ask-aggregate`를 추가한다.

접근 판정은 다음 순서를 따른다.

1. 요청자 JWT로 `ask_messages`에서 trace를 찾는다. 작성자가 아니면 RLS가 0행을 돌려준다.
2. 없으면 `has_workspace_role(editor)`를 확인한 뒤 `jobs`에서 찾는다.
3. 둘 다 아니면 `WorkspaceForbidden`(403)으로 끝낸다. 부재와 격리 위반을 구분하지 않는다.
4. 게이트를 통과한 뒤에만 `usage_events`를 trace로 읽는다.

Ask 집계는 `security definer` RPC `ask_trace_aggregate`가 함수 첫머리에서 editor 역할을 확인하고 집계값만 돌려준다. `enqueue_source_job`과 같은 패턴이며, 사용자·스레드·trace 식별자를 반환하지 않는다.

응답은 `/operations`처럼 허용 목록으로 조립한다. 화면은 사이드바에서 진입하는 `/w/[workspaceId]/control`이고, 탭 네 개 중 추적만 데이터를 보여준다. 나머지 탭은 Step 번호와 빈 상태만 표시한다.

### D10. 합성 증거와 공개 쇼케이스

- 증거 파일은 `apps/dashboard/content/controlled-ai/*.json`에 둔다. Vercel Root Directory 안에서 저장소 파일을 빌드 시점에 읽고 정적으로 렌더링한다.
- 앞서 제안한 `docs/portfolio/evidence/` 위치는 Root Directory 밖이라 변경한다.
- `after` 값은 pytest 시나리오가 생성하고, `before` 값은 기준 커밋 `79b68fe`에서 같은 시나리오로 한 번 측정해 커밋한다.
- 증거에 UUID, 이메일, 자격 증명 형태가 없음을 테스트로 검사한다.
- 라우트는 `force-static`이며 Supabase나 API 클라이언트를 import하지 않는다.
- `/showcase`는 미들웨어 대상이 아니므로 세션 조회가 일어나지 않는다. 다른 라우트로 가는 `Link`는 프리페치를 끈다. 켜 두면 페이지를 열기만 해도 홈 라우트의 미들웨어와 서버 렌더링이 돌아, 브라우저 실측에서 `/?_rsc=` 요청으로 확인되었다.
- `before`는 시나리오 파일을 그대로 두고 기준 커밋의 worktree를 `PYTHONPATH` 앞에 놓아 측정한다. 시나리오가 두 커밋에 모두 있는 경계만 쓰기 때문에 가능하다.
- 코드가 커밋되기 전에는 `after.commit`을 `uncommitted`로 기록하고 화면에 "커밋 전"으로 표시한다. 커밋 후 재생성은 task 7.3이다.
- 실측 결과 깨진 프레임의 기준 동작은 부분 답변 저장이 아니라 처리되지 않은 예외로 인한 미종결 턴이었다. 증거 문구는 이 측정값을 따른다.

## Risks / Trade-offs

- [API 프로세스가 스트림 도중 죽으면 Ask 구간이 남지 않는다] → 화면에 미완료로 표시한다. 비용은 워커가 기록하지만, 워커에게는 클라이언트 끊김과 같아 최종 사용량 전이면 0으로 기록된다. 아래 끊긴 호출 항목과 같다.
- [작성자가 RPC를 직접 호출해 자신의 `control_report`를 조작할 수 있다] → 월 상한은 `service_role`이 쓴 `usage_events`만 읽는다. Ask 집계의 결정 분포는 참고 수치로 표시하고, 크기 CHECK로 남용을 제한한다.
- [중단된 스트림의 실제 비용이 0으로 기록될 수 있다] → `incomplete` 건수를 화면에 표시한다. 빈도가 높으면 후속 change에서 사후 대조를 도입한다.
- [Ask 사용량 행의 `trace_id`와 시각, 비용이 다른 멤버에게 보인다] → 시각과 비용은 지금도 보이는 값이고 상세 조회는 막힌다. Gate 1에서 범위 밖으로 확인했다.
- [질의마다 사용량 INSERT가 늘어 경미한 부하가 생긴다] → 응답 후 수행하므로 사용자 지연에 더해지지 않는다.
- [Langfuse SDK가 프로세스에 백그라운드 전송 스레드를 추가한다] → 키가 없으면 초기화하지 않고, 운영에서 키를 지우면 재시작 후 꺼진다.
- [멤버가 새 턴이나 잡의 `trace_id`를 직접 고를 수 있다] → 턴은 `ask_messages`의 `before insert` 트리거가, 사용량이나 잡에 이미 있는 값을 42501로 거부한다. RPC 없이 직접 INSERT할 수 있어 함수가 아니라 트리거에 둔다. 잡은 `enqueue_source_job`이 Ask 턴의 값만 거부한다. 영상 배치 등록의 잡들이 한 trace를 공유하기 때문이다. 멤버는 `usage_events`에서 다른 멤버의 trace를 읽을 수 있어, 이 검사가 없으면 상세가 403에서 200으로 바뀌었다. 돌아오는 값은 어차피 RLS로 읽을 수 있는 것뿐이므로 이 검사는 Ask 턴이 있는 trace에 한해 표시 합계의 오염과 화면 계약을 지키는 것이지 새 값을 숨기는 경계가 아니다. 남은 경우는 수용한다. (1) 아직 행이 없는 값은 멤버가 알 수 없다. (2) `enqueue_source_job`은 definer라 Ask trace 여부를 판정할 수 있으나 editor 전용이고, 그 값은 사용량 행으로 대부분 이미 보인다. (3) 두 워크스페이스의 멤버는 한쪽의 trace로 다른 쪽에 턴을 만들 수 있다. Postgres의 조회는 `workspace_id`로 갈라져 섞이지 않지만, Langfuse trace ID는 이 값만으로 만들어 개발자용 사본에서는 한 trace로 묶일 수 있다. 원래 워크스페이스의 상세는 계속 403이다. (4) editor 이상은 PostgREST를 직접 호출해 Ask 턴이 없는 trace로 잡을 만들 수 있다. 작성자가 스레드를 지운 Ask trace, 다른 멤버의 `/retrieval` trace, 다른 사람의 수집 trace가 여기 해당한다. 앞의 둘은 상세가 403에서 200이 되고, 마지막은 표시되는 호출 수와 합계가 늘어난다. 돌아오는 값은 RLS로 이미 읽을 수 있는 사용량과 잡 단계뿐이고 본문은 나가지 않는다. 월 상한 합계에는 그 잡이 실제로 쓴 비용만 더해지며, trace를 재사용한다고 더 늘지는 않는다. 작성자의 계정 삭제로 스레드가 cascade 삭제된 경우도 스레드를 지운 경우와 같다.
- [턴이 끝나기 전에 클라이언트가 끊으면 턴이 `streaming`에 남는다] → 기준 커밋에도 있는 동작이고, 델타를 받는 중이든 검색을 기다리는 중이든 같다. 스펙의 종결 의무를 서버가 쓸 수 있는 실패로 좁히고 #170으로 분리했다.
- [최종 사용량 프레임 전에 끊긴 Ask 호출은 비용 0으로 기록된다] → 공급자는 청구할 수 있는데 상한에는 쌓이지 않으므로, 끊기를 반복하면 Ask 비용이 상한을 비켜 간다. 실제 청구액은 확인하지 않았다. `incomplete` 건수를 표시하고, 속도 제한(`LLM_STREAM_RATE_*`)이 규모를 제한한다. 사후 대조는 후속 작업 #172으로 분리했다.
- [집계의 건수와 결정, 지연은 작성자가 넣을 수 있는 행에서 나온다] → 작성자는 자기 스레드에 `ask_messages`를 직접 INSERT할 수 있어 미래 시각의 `resolved` 행으로 건수를 부풀릴 수 있다. 참고 수치로 표시하며 비용과 상한은 `usage_events`만 읽는다. 일 단위 내림으로 경계 이동은 막았지만, 짧은 간격의 폴링으로 새 턴의 값을 분리하는 것은 막지 못한다. 현재 소규모 운영에서 수용하고, 질문 본문과 식별자는 어느 쪽으로도 나가지 않는다.
- [턴 내보내기와 종료 시 사용량 기록에 유실이 있을 수 있다] → API의 내보내기는 2초, 워커의 기록은 2초까지 기다리고 못 끝낸 건수를 로그로 남긴다. 리스너는 15초 뒤 진행 중 스트림을 취소하며 그 호출은 `incomplete`로 기록된다.
- [회수된 뒤 늦게 끝난 워커가 Langfuse에 `succeeded`로 보일 수 있다] → `complete_job`의 0행은 핸들러가 체인을 완료한 정상 경우와 구분할 수 없다. 영향이 개발자용 사본에 한정되어 수용한다.
- [`complete_structured` 시그니처 변경이 기존 테스트에 영향을 준다] → 콜백은 선택 인자로 추가하고 반환값은 그대로 둔다.
- [OpenRouter 오류 프레임의 실제 형식이 다를 수 있다] → 구현 전에 공식 문서로 확인하고, 깨진 프레임 분기가 안전망이 된다.

## Migration Plan

1. 클라우드에 적용된 최신 번호를 확인하고 그 다음 번호부터 추가한다. 현재 저장소의 최신은 `0022`이므로 `0023`부터 쓴다.
2. 배포 순서는 DB, 워커, API, 대시보드 순이다. 모든 컬럼은 null 허용이고 함수 인자에는 기본값이 있어 각 단계에서 이전 버전 코드가 동작한다. 트리거와 인큐 검사는 `trace_id` 컬럼을 추가하는 `0025`에 두어, 앞선 파일만 적용된 구간에서도 원문 등록이 실패하지 않는다.
3. 워커는 trace가 없는 호출을 허용하고, 이전 버전 워커는 알 수 없는 헤더를 무시하므로 API와 워커 사이에 순서 의존이 없다.
4. 적용 결과를 `docs/ops/`의 마이그레이션 기록과 `docs/reference/stack.md`에 남긴다.
5. **롤백**: 코드를 되돌리면 된다. 추가한 컬럼과 인자는 이전 코드에 영향을 주지 않으므로 스키마는 되돌리지 않는다. 내보내기만 끄려면 Langfuse 키를 제거하고 프로세스를 재시작한다.

## 리뷰 1라운드 후 결정

2026-11-02에 사용자가 리뷰 게이트가 넘긴 결정을 권장안대로 진행하라고 위임했다.

| 항목 | 결정 | 이유 |
| --- | --- | --- |
| 비멤버 `/retrieval` | 200과 빈 근거에서 403으로 변경 | 임베딩 호출 전에 막아야 다른 테넌트의 월 상한을 소진하는 경로가 사라진다 |
| 위조·만료 토큰 | 전 라우트에서 500 대신 401 (`errors.py`의 단일 지점). PostgREST의 JWT 오류(`PGRST30x`)만 해당하고, 게이트웨이의 401은 배포 설정 문제이므로 500을 유지한다 | 라우트마다 다르게 처리하면 SEC-04의 "한 곳" 조건이 깨진다. 42501 판정을 먼저 해 격리 위반은 계속 403이다 |
| `0026`의 결함 | 번호를 늘리지 않고 `0025`, `0026`을 직접 수정 | 클라우드에 적용한 적이 없어 번호 순서 규칙에 걸리지 않는다. 로컬은 이 수정본으로 적용했다 |
| API의 Langfuse 키 | 제거하고 워커에 위임 | D8 참고 |
| 끊긴 클라이언트의 턴 | 스펙을 좁히고 후속 작업으로 분리 | Risks와 #170 참고 |
| 병합 후 `after.commit` | PR에는 브랜치 해시를 기록하고, 병합 직후 후속 PR로 `main` 해시로 교체 | squash 후에도 공개 커밋을 `main`에서 찾을 수 있어야 한다. #171 |
| 7.3과 게이트의 순서 | 7.3만 남은 상태에서 게이트를 돌려 통과시키고, 코드 커밋 뒤의 증거 커밋은 재리뷰하지 않는다 | 7.3은 코드를 커밋해야 끝나고 바뀌는 값은 증거 파일의 해시뿐이다. `test_committed_code_cannot_ship_with_uncommitted_evidence`가 누락을 막는다 |
| 쇼케이스 진입점 | 링크를 추가하지 않는다 | 스펙 요구가 아니고, 포트폴리오에서 직접 URL로 연다 |

## Open Questions

- Langfuse 리전은 JP를 기본으로 하되, 가입 시점의 요금 페이지에서 Hobby 제공 여부를 다시 확인한다. 설정값만 달라지며 계약과 작업 분할은 바뀌지 않는다.
- Langfuse SDK 정확한 버전은 구현 시점의 안정 버전으로 고정한다.
