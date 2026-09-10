## Context

외부 모델 공급자(OpenRouter) 크레딧이 소진되었을 때 발생하는 HTTP 402 Payment Required 오류의 처리 방식을 개선한다. 상세 배경과 동기는 `proposal.md`를 참조한다.

## Goals / Non-Goals

**Goals:**
- Worker: HTTP 402 발생 시 `ProviderCreditExhausted`를 발생(LLM chat 및 embedding 모두)시키고 `NON_RETRYABLE_ERRORS`를 통해 1회 시도로 즉시 `dead-letter` 종결.
- Worker: `sanitize_error`에서 내부 기계 토큰 대신 `provider_credit_exhausted provider={provider} kind={kind}` 정제 토큰 생성.
- Dashboard: `JobStepper.tsx`에서 신규 토큰 및 기존 DB에 적재된 `provider_error` 402 오류를 한국어 친화 문구로 매핑하고, 크레딧 충전 후 재시도할 수 있도록 복구 버튼 활성화(`retryable: true`).

**Non-Goals:**
- 일시적 네트워크 또는 서버 장애(429, 500, 502, 503 등)의 재시도 정책 변경 (기존대로 지수 백오프 재시도 유지).
- 대시보드 내 인앱 결제 모달 팝업 연동 (안내 메시지로 충분).

## Decisions

### D1: `ProviderCreditExhausted(ProviderError)` 하위 클래스 도입
- **선택**: `ProviderError`를 상속하는 `ProviderCreditExhausted` 클래스를 신설하고 `NON_RETRYABLE_ERRORS`에 등록.
- **근거**: 슬라이스 4의 `TranscriptPermanentlyUnavailable`과 동일한 아키텍처 패턴. `queue.py`가 에러의 내부 속성을 일일이 파싱하지 않고 `isinstance(error, NON_RETRYABLE_ERRORS)`로 일관되게 즉시 dead-letter를 판정할 수 있음. LLM 완성(`llm.py`)뿐만 아니라 임베딩(`embedding.py`) 경로에서도 동일하게 적용.
- **대안 검토**: `queue.py`에서 `if isinstance(error, ProviderError) and error.status_code == 402` 검사. → 큐 모듈에 공급자별 상태 코드 예외 로직이 누수되므로 기각.

### D2: `sanitize_error`의 정제 토큰 명시
- **선택**: `isinstance(error, ProviderCreditExhausted)`일 때 `provider_credit_exhausted provider={error.provider} kind={error.kind}`를 반환.
- **근거**: `last_error`는 워크스페이스 멤버가 조회 가능하며, 보안상 공급자 본문과 자격증명을 숨기면서도 대시보드 및 운영자가 chat/embedding 실패 여부를 명확히 식별할 수 있는 표준 토큰 규약 유지.

### D3: Dashboard `describeFailure`의 하위 호환 매핑 및 재시도 액션 보존
- **선택**: `JobStepper.tsx`의 `describeFailure`에서 `job.last_error`가 `provider_credit_exhausted`이거나 `provider_error`의 `status=402`를 포함하는 경우를 감지 (`upstream_error`와 명확히 구분).
- **근거**: 이미 DB에 dead 상태로 저장된 기존 행(`provider_error kind=chat_completion provider=openrouter status=402`)도 UI 새로고침 즉시 올바른 안내 문구로 보여야 하며, 웹 URL 크롤링 실패(`upstream_error status=402`)와 오인되지 않아야 함.
- **안내 문구**: `"AI 사용 크레딧이 소진되어 위키를 만들지 못했습니다. 크레딧을 충전하거나 워크스페이스 API 키를 확인해 주세요."`
- **`retryable: true`**: 크레딧 충전 또는 API 키 확인 후 사용자가 즉시 해당 잡을 재시도할 수 있도록 버튼 제공.

## Risks / Trade-offs

- [Risk] 사용자가 크레딧을 충전한 후 어떻게 다시 실행하는가?
  → [Mitigation] 워크스페이스 BYOK 키 설정이나 OpenRouter 충전 후, 원본 소스를 다시 추가하거나 잡 상태가 dead이므로 향후 제공되는 명시적 재시도 경로를 통해 복구 가능. 또한 문구에서 취해야 할 조치를 명확히 제시.
