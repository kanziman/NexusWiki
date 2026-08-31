## 1. 워크스페이스 설정 BYOK UI 구현

- [x] 1.1 `WorkspaceGeneralSettings.tsx`에 OpenRouter API 키 등록/수정/삭제 및 마스킹 카드 UI 추가
- [x] 1.2 소유자(Owner) 권한 검증 및 키 저장/삭제 로직 연동

## 2. 크레딧 소진 모달 및 네비게이션 연계

- [x] 2.1 `CreditLimitModal.tsx`에 "내 API 키 등록하고 무제한 이용하기" 액션 버튼 추가
- [x] 2.2 `AccountMenu.tsx` 및 `WorkspaceSidebar.tsx`에 커스텀 키 등록 상태(무제한 뱃지) 렌더링 지원

## 3. 테스트 및 전체 검증

- [x] 3.1 `WorkspaceGeneralSettings.test.tsx`, `CreditLimitModal.test.tsx`, `AccountMenu.test.tsx` 단위 테스트 작성 및 업데이트
- [x] 3.2 `pnpm test && pnpm typecheck && pnpm lint` 전체 검증 실행
