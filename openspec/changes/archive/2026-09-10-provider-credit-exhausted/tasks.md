## 1. Worker Exception & Non-Retryable Classification

- [x] 1.1 `apps/worker/src/worker/errors.py`에 `ProviderCreditExhausted(ProviderError)` 정의 및 `NON_RETRYABLE_ERRORS`에 등록
- [x] 1.2 `apps/worker/src/worker/llm.py` 및 `embedding.py`에서 HTTP 402 응답 시 `ProviderCreditExhausted` 발생하도록 분기 추가
- [x] 1.3 `apps/worker/src/worker/queue.py`의 `sanitize_error`에서 `ProviderCreditExhausted`를 `provider_credit_exhausted provider={error.provider} kind={error.kind}`로 정제
- [x] 1.4 `apps/worker/tests/test_queue.py`, `test_llm.py`, `test_embedding.py`에 402 발생 시 즉시 dead-letter 종결 및 에러 정제 단위 테스트 추가

## 2. Dashboard Failure Mapping & Non-Retryable UI

- [x] 2.1 `apps/dashboard/components/JobStepper.tsx`의 `describeFailure`에 크레딧 소진(`provider_credit_exhausted` 및 `provider_error` 402) 매핑 및 `retryable: true` 적용
- [x] 2.2 `apps/dashboard/tests/JobStepper.test.tsx`에 크레딧 소진 실패 시 한국어 안내 문구 노출 및 재시도 버튼 유지 검증 테스트 추가

## 3. Verification & Specs Sync

- [x] 3.1 워커 및 대시보드 테스트, 린트, 타입체크 실행 및 통과 확인
- [x] 3.2 delta spec을 `openspec/specs/`에 반영하고 `openspec validate --specs --strict` 검증
