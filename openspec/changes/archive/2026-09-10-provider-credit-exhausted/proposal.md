# Proposal: provider-credit-exhausted

## Why

외부 모델 공급자(OpenRouter) 크레딧 소진(HTTP 402 Payment Required)은 단순 재시도로는 복구될 수 없으며, 계정 충전 또는 워크스페이스 BYOK 키 등록이 있어야만 복구됩니다.
그러나 현재 시스템은 HTTP 402를 일반 `ProviderError`로 처리하여 `max_attempts`까지 무의미한 재시도를 반복해 큐 처리량을 갉아먹고, UI에서도 기계 토큰(`provider_error kind=chat_completion provider=openrouter status=402`)과 잘못된 안내("재시도를 눌러 다시 시도하세요")를 노출합니다.
HTTP 402를 재시도 불가 에러로 분류해 즉시 dead-letter로 종결하고, 사용자에게 친절한 크레딧 소진 안내를 제공해야 합니다.

## What Changes

- **Worker**:
  - `ProviderCreditExhausted(ProviderError)` 예외 신설 (`status_code=402`).
  - `NON_RETRYABLE_ERRORS`에 `ProviderCreditExhausted` 추가하여 402 발생 시 `max_attempts` 백오프 반복 없이 1회 시도로 즉시 `dead-letter` 종결.
  - `llm.py`에서 `chat/completions` HTTP 402 응답 시 `ProviderCreditExhausted` raise.
  - `queue.py:sanitize_error`에서 `provider_credit_exhausted provider={error.provider}` 정제 토큰 생성.
- **Dashboard**:
  - `JobStepper.tsx`의 `describeFailure`에 크레딧 소진(`provider_credit_exhausted` 및 기존 `status=402` 호환) 실패 매핑 추가.
  - 사용자 친화적 한국어 메시지 제공: `"AI 사용 크레딧이 소진되어 위키를 만들지 못했습니다. 크레딧을 충전하거나 워크스페이스 API 키를 확인해 주세요."`
  - 즉각적인 단순 재시도 버튼을 비활성화/숨기거나 무의미한 재시도 유도를 방지 (`retryable: false`).

## Capabilities

### Modified Capabilities
- `background-job-lifecycle`: 모델 공급자 크레딧 소진(HTTP 402) 시 재시도 없이 즉시 dead-letter 종결 및 정제 토큰 기록 요구사항 추가.
- `source-processing-status`: 크레딧 소진 실패 시 단순 재시도 안내 대신 크레딧 충전 안내 메시지를 표시하는 요구사항 추가.

## Impact

- `apps/worker/src/worker/errors.py`: `ProviderCreditExhausted`, `NON_RETRYABLE_ERRORS` 튜플.
- `apps/worker/src/worker/llm.py`: HTTP 402 예외 분기.
- `apps/worker/src/worker/queue.py`: `sanitize_error` 토큰 처리.
- `apps/dashboard/components/JobStepper.tsx`: 에러 메시지 번역 및 retryable 플래그.
- 관련 워커 및 대시보드 테스트 스위트 추가/갱신.
