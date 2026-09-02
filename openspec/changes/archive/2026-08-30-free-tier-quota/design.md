# Design: 무료 사용자 크레딧 쿼터 및 사용량 한도 안내 시스템

## 1. 아키텍처 및 설계 원칙

### 기본 무료 크레딧 쿼터
- 모든 워크스페이스는 기본 `monthly_budget_micros`를 기반으로 동작하며, 초과 시 백엔드에서 `402 budget_exceeded`를 반환합니다.
- 클라이언트는 402 에러를 감지하면 단순히 기술적 에러 메시지를 띄우는 대신 비즈니스 친화적인 `CreditLimitModal`을 렌더링합니다.

### 컴포넌트 설계 (`CreditLimitModal.tsx`)
- **Radix Dialog 기반 모달**:
  - `backdrop-blur-md` 오버레이 및 모던 스타일링
  - 타이틀: "이번 달 무료 크레딧을 모두 소진했습니다"
  - 설명: "무료 플랜에서 제공하는 월간 AI 질의 및 소스 분석 크레딧 한도($1.00)에 도달했습니다. 크레딧은 매월 1일에 자동으로 초기화됩니다."
  - 액션:
    - [운영 및 사용량 확인하기]: `/w/[workspaceId]/settings?tab=operations`로 이동
    - [닫기]: 모달 닫기

### 질문창 및 소스 업로드 연동
- `AskConversation.tsx`: SSE 연결 중 `res.status === 402` 또는 이벤트 에러 메시지에 `budget_exceeded`가 포함된 경우 `CreditLimitModal`을 엽니다.
- `Dropzone.tsx`: 소스 인제스천 fetch 결과가 402인 경우 `CreditLimitModal`을 엽니다.
- `OperationsPanel.tsx`: 월별 예산과 현재 사용량을 비교하는 시각적 프로그레스 바(Progress Bar)를 렌더링합니다.
