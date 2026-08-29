## MODIFIED Requirements

### Requirement: Google 단일 인증

시스템은 로그인과 가입에서 Google OAuth만 제공해야 한다(MUST). 로그인 화면은
데스크톱에서 지식 비주얼과 인증 영역을 나란히, 모바일에서는 인증 영역을 먼저
제공해야 한다(MUST). 인증 영역은 제품명, 로그인 안내, Google CTA, 가입 화면
연결을 제공해야 하며, 시각적 보조 영역이 없어도 인증을 완료할 수 있어야 한다.
OAuth 진행 중에는 중복 시작을 막고 진행 상태를 알려야 한다(MUST). OAuth 실패는
계정 존재 여부를 드러내지 않는 단일 오류로 처리해야 한다.

#### Scenario: 로그인 시작

- **WHEN** 사용자가 로그인 또는 가입 화면의 Google CTA를 선택하면
- **THEN** 시스템은 내부 콜백 URL을 redirect 대상으로 OAuth를 시작한다

#### Scenario: 인증 실패

- **WHEN** 콜백의 코드 교환이 실패하면
- **THEN** 시스템은 `/login?error=auth`로 이동하고 단일 오류 문구만 표시한다

#### Scenario: 데스크톱 로그인 화면

- **WHEN** 사용자가 데스크톱 너비에서 로그인 화면을 연다
- **THEN** 시스템은 지식 탐색 맥락을 보여 주는 시각적 보조 영역과 Google 인증
  영역을 나란히 제공한다

#### Scenario: 모바일 로그인 화면

- **WHEN** 사용자가 모바일 너비에서 로그인 화면을 연다
- **THEN** 시스템은 인증 영역을 먼저 한 열로 제공하고, 화면의 가로 넘침 없이
  Google 로그인과 가입 화면 연결을 사용할 수 있게 한다

#### Scenario: OAuth 요청 진행 중

- **WHEN** 사용자가 Google CTA를 선택해 OAuth 시작 요청이 진행 중이다
- **THEN** 시스템은 CTA를 비활성화하고 진행 상태를 표시하여 중복 요청을 막는다

#### Scenario: 가입 화면 연결

- **WHEN** 사용자가 로그인 화면의 가입 안내를 선택한다
- **THEN** 시스템은 `/signup`으로 이동한다
