## Why

PR #206의 SEC-03 검사는 API 테스트가 워커 특권 DB 모듈을 직접 가져와 실패했다. 기존 보안 검사를 유지하면서 승인·적용 실DB 검증을 올바른 책임 위치로 이동한다. 추적: https://github.com/kanziman/NexusWiki/issues/207

## What Changes

- 승인·적용 통합 테스트의 워커 실행 부분을 워커 테스트 영역으로 이동한다.
- API의 승인·권한·제안 조회 검증과 워커의 반복 적용·색인·개정 검증을 보존한다.
- 기존 SEC-03 검사를 실행하고 PR 재실행 결과를 확인한다.
- Vercel 로그에서 확인한 `next/font/google` 파일 확장자 파싱 실패를 해소한다. 기존 Inter·Plus Jakarta Sans·JetBrains Mono를 고정된 Fontsource 패키지에서 `next/font/local`로 로드한다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

없음. 사용자 동작과 검증 계약을 바꾸지 않는 테스트 책임 이동이므로 `skip_specs: true`를 사용한다. 정본은 `tenant-data-isolation`의 특권 처리 경계다.

## Impact

API·worker 테스트, dashboard 폰트 로딩과 고정 의존성, 이 change 산출물. 보안 탐지 스크립트·DB·서체 종류와 CSS 변수는 변경하지 않는다.
