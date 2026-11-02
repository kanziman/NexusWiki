## Why

NexusWiki는 LLM 호출 하나를 그것을 일으킨 요청까지 되짚을 수 없고, 충돌 판정·실패한 시도·중단된 스트림·질의 임베딩의 지출이 `usage_events`에 남지 않아 월 비용 상한이 실제보다 늦게 걸린다. Ask 스트림은 깨진 프레임에서 턴을 `streaming`에 남기고, 스트림 중간 오류에서는 잘린 답변을 정상으로 저장한다. Controlled AI 4단계 도입의 첫 단계로서 이후 단계의 효과를 측정할 수 있도록 추적과 회계를 먼저 사실로 만든다. 작업 추적은 umbrella 이슈 #157을 따른다.

## What Changes

- 서버가 요청마다 `trace_id`를 발급하고 내부 호출, `jobs` 체인, `usage_events`, `ask_messages`까지 전파한다
- 지출 누락 네 경로를 메워 공급자가 보고한 비용을 빠짐없이 월 상한 계산에 포함한다
- Ask 스트림의 깨진 프레임과 중간 오류를 오류로 종결하고, 위조 앵커가 인용 지표를 부풀리지 않게 한다
- 일부 검색 채널이 실패했음을 Ask 메타데이터로 실제 전달해 기존 안내 문구가 동작하게 한다
- LLM 호출을 막지 않고 Router 결정만 기록한다(shadow). 근거 0건 단락은 기존대로 실행한다
- 모든 LLM·임베딩 호출을 동작 변경 없이 하나의 게이트웨이로 모은다
- 본문을 제외한 메타데이터를 외부 관측 서비스(Langfuse Cloud)로 내보낼 수 있게 한다. 자격 증명이 없으면 비활성이다
- Control Room 추적 탭(`/w/[workspaceId]/control`)을 추가한다
- 합성 증거만 쓰는 공개 쇼케이스(`/showcase/controlled-ai`)를 추가한다
- `hybrid-retrieval` 스펙을 운영 정본인 4채널로 정정한다. 그래프 웨이브는 정책으로 켤 때만 실행한다

### 용어

- **trace**: 사용자 요청 하나 또는 수집 작업 하나에서 시작된 모든 처리를 묶는 단위. `trace_id`로 식별한다
- **Ask trace / 수집 trace**: Ask 턴에서 시작된 trace와 원문 수집 잡 체인에서 시작된 trace
- **Router 결정**: 요청을 어느 처리 경로로 보낼지 정한 결정론적 판단과 그 사유 코드
- **Control Room**: 워크스페이스 멤버가 trace와 통제 결과를 확인하는 운영 화면
- **합성 증거**: 테스트 시나리오가 합성 입력으로 생성한, 실제 테넌트 데이터를 담지 않은 파일

## Capabilities

### New Capabilities

- `ai-request-tracing`: trace 발급과 전파, Router 결정 기록, 본문 없는 외부 관측 내보내기
- `ai-control-room`: 역할과 작성자 경계를 지키는 추적 화면
- `ai-controls-showcase`: 합성 증거로 통제 전후를 보여주는 공개 화면

### Modified Capabilities

- `usage-guardrails`: 호출별 사용량 기록 범위를 실패·중단·질의 임베딩·충돌 판정까지 넓히고 trace와 연결한다
- `grounded-answering`: 스트림 실패의 종결 계약, 인용 지표 계산 기준, 부분 검색 실패 전달을 추가한다
- `hybrid-retrieval`: 5채널 2웨이브 요구를 4채널과 선택적 그래프 웨이브로 정정한다

## Impact

- `apps/api`: 추적 미들웨어, 내부 호출 헤더, Ask 서비스, 추적 조회 라우터
- `apps/worker`: LLM·임베딩 게이트웨이, 충돌 판정과 재시도의 사용량 기록, 내부 리스너, 잡 컨텍스트
- `packages/core`: trace 컨텍스트, 로그 마스킹 키, 인용 지표, Router 판정
- `supabase/migrations`: `0023` 이후 추가 전용 마이그레이션. `jobs`·`usage_events`·`ask_messages` 확장, 체인과 인큐 함수 갱신, RLS 정책
- `apps/dashboard`: Control Room 추적 탭, 공개 쇼케이스 라우트, 합성 증거 파일
- 의존성: Langfuse Python SDK 추가
- 문서: `.claude/CLAUDE.md`, `README.md`, `docs/reference/stack.md`의 5채널 서술 정리
- 비범위: 프롬프트 예산, 출력 계약 변경, Router 실행 분기, 정책 주입, 위키 쓰기 분류는 Step 2~4의 몫이다
