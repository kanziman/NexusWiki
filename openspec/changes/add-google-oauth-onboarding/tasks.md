## 1. Google 인증 진입과 안전한 콜백

- [x] 1.1 Google 단일 인증 화면·콜백·로컬 Provider 설정을 테스트 우선으로 구현한다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/16)
  - Given: 이메일·비밀번호 로그인과 OAuth Provider 미설정 상태가 있다.
  - When: 사용자가 로그인·가입 CTA를 선택하거나 OAuth 콜백을 호출한다.
  - Then: Google OAuth만 시작되고 내부 next만 따라가며 실패는 단일 오류로 수렴한다.
  - Verification: 먼저 Vitest로 OAuth 요청·next 정규화·콜백 실패를 작성한 뒤 `pnpm test -- --run`, `pnpm typecheck`, `pnpm lint`를 통과한다.

## 2. 첫 워크스페이스 온보딩

- [x] 2.1 빈 워크스페이스 사용자의 personal 워크스페이스 생성 흐름을 테스트 우선으로 구현한다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/17)
  - Given: 인증 사용자의 RLS 결과가 빈 목록이다.
  - When: 사용자가 1~100자 이름을 제출한다.
  - Then: 전역 충돌을 해소한 slug와 owner 멤버십을 가진 personal 워크스페이스가 생성되고 UUID 경로로 이동한다.
  - Verification: 먼저 Vitest로 빈 상태·성공·중복 slug·입력 오류를 작성한 뒤 `pnpm test -- --run`, `pnpm typecheck`, `pnpm lint`를 통과한다.

## 3. 출시 전 외부 설정 확인

- [ ] 3.1 Google Cloud·Supabase Cloud Provider 설정과 기존 계정 충돌을 운영 체크리스트로 검증한다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/18)
  - Given: 코드와 로컬 설정 검증이 통과했지만 Cloud 자격 증명은 별도 관리된다.
  - When: 권한 있는 운영자가 승인 URI·Provider secret·기존 identity 분포를 확인한다.
  - Then: 실제 Google 로그인 smoke test를 기록하거나, 누락된 자격 증명 때문에 출시가 보류됨을 명시한다.
  - Verification: `select provider, count(*) from auth.identities group by 1;`와 Cloud OAuth smoke test 결과를 issue에 기록한다.
