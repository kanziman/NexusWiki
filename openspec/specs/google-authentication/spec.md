# google-authentication Specification

## Purpose
사용자가 Google 계정 하나로 가입·로그인하고, 인증 코드와 리다이렉트 대상이 안전하게 처리되도록 한다.

## Requirements

### Requirement: Google 단일 인증

시스템은 로그인과 가입에서 Google OAuth만 제공해야 한다(MUST). OAuth 실패는 계정 존재 여부를 드러내지 않는 단일 오류로 처리해야 한다.

#### Scenario: 로그인 시작
- **WHEN** 사용자가 로그인 또는 가입 화면의 Google CTA를 선택하면
- **THEN** 시스템은 내부 콜백 URL을 redirect 대상으로 OAuth를 시작한다

#### Scenario: 인증 실패
- **WHEN** 콜백의 코드 교환이 실패하면
- **THEN** 시스템은 `/login?error=auth`로 이동하고 단일 오류 문구만 표시한다

### Requirement: OAuth 콜백은 안전한 내부 경로만 따른다

시스템은 authorization code를 한 번 교환하고, `/`로 시작하되 `//`로 시작하지 않는 경로만 다음 목적지로 허용해야 한다(MUST).

#### Scenario: 외부 리다이렉트 거부
- **WHEN** next 값이 절대 URL 또는 `//`로 시작하면
- **THEN** 시스템은 코드 교환 뒤 루트 경로로 이동한다
