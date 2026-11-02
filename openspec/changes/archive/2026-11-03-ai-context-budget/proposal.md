## Why

Step 1(`ai-control-flow-accounting`)과 중단 Ask 정산(`reconcile-interrupted-ask-cost`)으로 요청 추적과 사후 회계가 확립되었으나, Ask 근거 컨텍스트 크기와 구조화 출력(`compile`·`conflict_check`)의 출력 토큰 상한이 강제되지 않고 동일 원문 재컴파일도 매번 LLM을 호출한다. 또한 Control Room의 `[예산]` 탭이 빈 상태로 남아 있어, 멤버와 편집자가 워크스페이스 예산 현황·호출 경로별 비용 분해·토큰 예산 및 단락 효과를 한 화면에서 확인할 수 없다.

## What Changes

- Ask 컨텍스트 조립에 총 토큰 예산과 위키·원문 근거 쿼터 배분을 적용해, 긴 문서가 다른 종류의 근거를 밀어내 이중 Citation이 깨지지 않게 하고 잘림 여부를 `control_report`에 본문 없이 기록한다.
- RRF 융합 시 동일 문서의 채널별 메타데이터(`title`, `slug` 등)를 병합해 벡터 채널이 먼저 적중한 위키 근거도 제목·슬러그를 보존하고 `LOOKUP` 판정이 누락되지 않게 한다.
- 구조화 출력 호출(`compile`, `conflict_check`)에 입력 길이 상한과 명시적 `max_tokens` 출력 상한을 적용하고 `LlmGateway`가 이를 공급자 요청과 사용량 메타데이터에 반영한다.
- 컴파일 잡에서 입력 지문(`content_hash` + `template_id` + `model`)이 직전 성공과 같고 해당 원문의 위키 페이지가 이미 존재할 때(`SKIP_UNCHANGED`), LLM 호출을 건너뛰고 후속 체인(`link_sync`)으로 진행하며 생략 사실을 관측 가능하게 남긴다.
- Control Room의 `[예산]` 탭(`Step 2`)을 활성화해 월간 크레딧 한도·공급자 보고 비용·미확정 점유·판정액, 호출 경로별(`ask`, `compile`, `conflict_check`, `embed`, `query_embedding`) 비용·토큰 분해(`editor` 이상), 적용 중인 토큰 상한 정책과 잘림·단락 집계(본인 Ask 및 워크스페이스 집계)를 실제 데이터로 표시한다.
- 공개 쇼케이스(`/showcase/controlled-ai`)에 Step 2 통제 전후 합성 시나리오 증거를 추가하고 준비 중 목록을 Step 3~4로 갱신한다.

### 용어

- **컨텍스트 토큰 예산 (Context Token Budget)**: Ask 프롬프트에 실리는 위키·원문 근거 블록 전체의 토큰 상한과 종류별 최소 보장 쿼터.
- **출력 토큰 상한 (`max_tokens`)**: 공급자 호출 요청에 명시적으로 싣는 최대 생성 토큰 수.
- **재컴파일 단락 (`SKIP_UNCHANGED`)**: 원문 해시·템플릿·모델 지문이 직전 성공 컴파일과 같고 산출된 위키 페이지가 존재할 때 LLM 호출을 생략하고 후속 체인을 잇는 동작.
- **Control Room 예산 탭**: 워크스페이스 월간 예산 상태, 호출 경로별 비용·토큰 분해, 토큰 예산 정책 및 잘림·단락 집계를 보여주는 탭.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `grounded-answering`: Ask 컨텍스트 토큰 예산과 위키·원문 근거 쿼터 배분(이중 Citation 보존) 및 RRF 위키 메타데이터 보존
- `usage-guardrails`: 구조화 출력(`compile`, `conflict_check`)의 입력·출력 토큰 상한(`max_tokens`) 강제와 메타데이터 기록
- `ai-request-tracing`: 컴파일 `SKIP_UNCHANGED` 결정의 실제 단락 실행과 관측 기록
- `ai-control-room`: Control Room `[예산]` 탭 활성화 및 역할·작성자 경계를 지키는 예산·호출 경로별 분해·단락 집계 조회
- `ai-controls-showcase`: Step 2 합성 증거 시나리오 추가 및 준비 중 단계 갱신

## Impact

- `packages/core`: RRF 메타데이터 병합, 컨텍스트 토큰 예산·쿼터 순수 계산기
- `apps/api`: `ApiSettings` Ask 컨텍스트 예산 설정, `AskService` 근거 예산 적용 및 `control_report.budget` 기록, `control.py`의 `GET /workspaces/{id}/control/budget` 라우트
- `apps/worker`: `WorkerSettings` 구조화 출력 토큰·슬러그·충돌 판정 입력 상한, `llm.py`·`llm_gateway.py`의 `max_tokens` 전달, `compile.py`의 `SKIP_UNCHANGED` 단락 및 `existing_slugs` 예산, `conflict.py`의 입력 예산과 `max_tokens`, 합성 증거 생성기(`test_controlled_ai_evidence.py`)
- `supabase/migrations`: `0028` 추가 전용 마이그레이션(`control_budget_snapshot` RPC — 요청자 JWT 기반 역할·작성자 경계 준수)
- `apps/dashboard`: `ControlRoom.tsx`의 `[예산]` 탭 화면과 `step1.json` / `ControlledAiShowcase.tsx` 갱신
- 추적: https://github.com/kanziman/NexusWiki/issues/183 . change 이름: `ai-context-budget`.
