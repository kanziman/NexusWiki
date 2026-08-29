## 1. 반응형 Google 로그인 경험

- GitHub sub-issue: [#87](https://github.com/kanziman/NexusWiki/issues/87)

- [x] 1.1 `nexuswiki-login-split-v3.html`의 지식 비주얼·인증 패널 구성을 `/login`에
  적용하고, Google OAuth의 시작·오류·로딩과 `/signup` 연결을 검증한다.
  - Given: 사용자가 데스크톱 너비에서 `/login`을 연다
  - When: 페이지가 렌더링된다
  - Then: 지식 비주얼과 Google 인증 패널이 나란히 보이고 Google CTA로 내부
    콜백 OAuth를 시작할 수 있다
  - Given: 사용자가 모바일 너비에서 `/login`을 연다
  - When: 페이지가 렌더링된다
  - Then: 인증 패널이 먼저 한 열로 보이며 가로 넘침 없이 로그인과 가입 연결을
    사용할 수 있다
  - Given: OAuth 시작 요청이 진행 중이거나 실패한다
  - When: CTA의 상태가 변한다
  - Then: 중복 요청이 차단되고 진행 상태 또는 계정 존재 여부를 드러내지 않는
    단일 오류가 보인다
