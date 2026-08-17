## Why

Sources와 Wiki는 모두 workspace 문서 라이브러리지만, 항목을 선택한 뒤의 상세 전환 구조와 맥락이 달라 사용자가 화면마다 다른 탐색 방식을 익혀야 한다.

## What Changes

- Sources와 Wiki에 동일한 목록 행·선택 상태·상세 header·목록 복귀 구조를 적용한다.
- 기존 URL, RLS, source 처리 상태, wiki 검증과 읽기 기능은 유지한다.

## Capabilities

### New Capabilities

- `library-selection-layout`: workspace 자료·위키 라이브러리의 일관된 선택 및 상세 탐색 계약

### Modified Capabilities

- 없음.

## Impact

- dashboard Sources/Wiki routes, shared row and detail primitives, tests
- API and database contracts unchanged
