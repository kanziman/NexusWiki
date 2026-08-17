## 1. Session-aware header

- [x] 1.1 workspace layout에서 현재 요청자 세션의 최소 식별 정보를 NavShell로 전달한다.
- [x] 1.2 키보드와 좁은 화면에서 접근 가능한 계정 메뉴·logout control을 NavShell에 추가한다.

## 2. Session termination

- [x] 2.1 browser Supabase client로 현재 세션을 종료하고 성공 시 전체 네비게이션으로 `/login`으로 이동한다.
- [x] 2.2 logout 실패·진행 중 상태에서 비민감 오류 안내와 중복 제출 방지를 제공한다.

## 3. Verification

- [x] 3.1 계정 affordance와 마우스·키보드 logout 동작을 검증하는 component 테스트를 추가한다.
- [x] 3.2 로그아웃 뒤 보호된 workspace route가 middleware에서 로그인으로 이동하는 회귀 테스트를 추가한다.
- [x] 3.3 dashboard 테스트, typecheck, lint 및 `openspec validate add-account-logout --strict`를 실행한다.
