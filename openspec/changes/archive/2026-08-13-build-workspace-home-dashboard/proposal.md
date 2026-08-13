## Why

워크스페이스 홈은 현재 placeholder라 사용자가 자료 등록, 질문, 위키 탐색의 다음 행동을 발견하기 어렵다. 기존 workspace-scoped 표면과 데이터를 활용해 첫 사용과 재방문 모두를 안내하는 진입 화면이 필요하다.

## What Changes

- 워크스페이스 이름, 자료·위키의 간단한 상태 요약, 주요 행동을 홈에 표시한다.
- `자료 추가`, `질문하기`, 위키 탐색 링크를 기존 URL-scoped 화면으로 연결한다.
- 최근 자료와 최근 위키 페이지를 RLS-scoped query로 표시하고, 비어 있으면 첫 자료 등록을 안내한다.

## Capabilities

### New Capabilities

- `workspace-home-dashboard`: workspace-scoped 첫 진입과 최근 활동 dashboard 계약

### Modified Capabilities

- 없음.

## Impact

- 영향 영역: workspace home route, 기존 sources/wiki read query
- 새 API·스키마·권한 모델은 추가하지 않으며 요청자 JWT/RLS만 사용한다.
