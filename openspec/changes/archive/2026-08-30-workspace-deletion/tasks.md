## 1. Danger Zone UI & Confirmation Modal Implementation

- [x] 1.1 `WorkspaceGeneralSettings.tsx`에 위험 구역(Danger Zone) 카드 및 워크스페이스 삭제 버튼 추가
- [x] 1.2 소유자 권한에 따른 활성화 제어 및 비소유자 안내 노트 렌더링
- [x] 1.3 Radix Dialog 기반의 확인 모달 구현 (워크스페이스 이름 일치 검증 인풋, 에러/로딩 상태, 배경 블러)
- [x] 1.4 Supabase delete 호출(`workspaces_delete_owner` RLS 검증) 및 삭제 후 남은 워크스페이스 조회/리다이렉트 로직 구현

## 2. Test & Verification

- [x] 2.1 `WorkspaceGeneralSettings.test.tsx`에 Danger Zone 렌더링, 비소유자 비활성화, 이름 불일치 시 삭제 버튼 비활성화, 일치 시 삭제 호출 및 리다이렉트 테스트 작성
- [x] 2.2 전체 대시보드 테스트 슈트(`pnpm test`), 타입체크(`pnpm typecheck`), 린트(`pnpm lint`) 검증
