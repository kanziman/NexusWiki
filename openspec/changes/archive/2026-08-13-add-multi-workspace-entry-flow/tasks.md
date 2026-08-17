## 1. Entry resolution

- [x] 1.1 Root route의 요청자 JWT 기반 workspace 조회를 결정적 정렬과 zero/one/many 분기로 정리한다.
- [x] 1.2 다중 workspace 사용자에게 RLS 조회 결과만 사용하는 서버 렌더링 선택 화면을 추가한다.
- [x] 1.3 로그인 완료 후 루트 진입이 새 entry resolver를 거치도록 기존 세션 전환 흐름을 확인·보완한다.

## 2. Scoped navigation and accessibility

- [x] 2.1 선택 화면의 workspace 항목을 키보드 접근 가능한 URL-scoped 링크로 만들고, 기존 `workspacePath` 계약을 재사용한다.
- [x] 2.2 workspace layout과 header switcher가 RLS-visible 목록만 사용하고 접근 불가 URL의 일반 보호 경로 결과를 유지하는지 검증한다.

## 3. Verification

- [x] 3.1 zero, one, multiple workspace entry 및 선택 후 경로를 검증하는 route/component 테스트를 추가한다.
- [x] 3.2 접근 불가 workspace URL에서 데이터나 존재 여부가 노출되지 않는 회귀 테스트를 추가한다.
- [x] 3.3 dashboard 테스트, typecheck, lint 및 `openspec validate add-multi-workspace-entry-flow --strict`를 실행한다.
