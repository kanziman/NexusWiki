## Why

현재 dashboard는 사용자가 로그인한 상태를 확인할 수 없고 로그아웃할 경로도 제공하지 않는다. 공유 기기와 다중 워크스페이스 환경에서 세션 종료를 명확히 제공해 사용자 제어와 보호 경로의 기대 동작을 완성해야 한다.

## What Changes

- 헤더에 현재 인증 세션을 식별하는 최소한의 계정 affordance를 추가한다.
- 계정 affordance에서 명확하고 키보드 접근 가능한 로그아웃 동작을 제공한다.
- 로그아웃이 Supabase Auth 세션을 종료하고 `/login`으로 이동하도록 한다.
- 로그아웃 뒤 보호된 workspace 경로가 기존 middleware에 의해 로그인으로 이동하는지 검증한다.

## Capabilities

### New Capabilities

- `account-session-control`: 인증된 dashboard 사용자의 세션 식별과 로그아웃 계약

### Modified Capabilities

- 없음.

## Impact

- 영향 영역: dashboard header/nav shell, Supabase browser client, middleware 보호 경로, 로그인 화면
- API·DB 스키마: 새 API나 스키마는 추가하지 않으며 기존 Supabase Auth 세션만 종료한다.
- 보안: logout은 browser client에서 현재 사용자 세션만 종료하고, 보호 경로의 인증 gate를 우회하지 않는다.
