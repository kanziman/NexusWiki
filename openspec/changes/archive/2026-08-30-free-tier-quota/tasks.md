## 1. Credit Limit Modal & Error Interception

- [x] 1.1 `CreditLimitModal.tsx` 컴포넌트 신규 구현 (Radix Dialog, 크레딧 소진 안내, 갱신 주기 및 설정 이동)
- [x] 1.2 `AskConversation.tsx`에서 402 `budget_exceeded` 감지 시 `CreditLimitModal` 트리거
- [x] 1.3 `Dropzone.tsx`에서 402 `budget_exceeded` 감지 시 `CreditLimitModal` 트리거
- [x] 1.4 `OperationsPanel.tsx`에 월간 무료 크레딧 소진율(Progress Bar) 표시 추가

## 2. Test & Verification

- [x] 2.1 `CreditLimitModal.test.tsx` 컴포넌트 렌더링 및 인터랙션 테스트 작성
- [x] 2.2 `AskConversation.test.tsx` 및 `Dropzone.test.tsx`에 402 발생 시 모달 노출 테스트 추가
- [x] 2.3 전체 프론트엔드 테스트(`pnpm test`), 타입체크(`pnpm typecheck`), 린트(`pnpm lint`) 검증
