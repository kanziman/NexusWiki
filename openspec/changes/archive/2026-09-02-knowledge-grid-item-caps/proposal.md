## Why

홈 지식 그리드가 카드형 행으로 개편되면서(`workspace-home-redesign`) 행 하나가 차지하는 세로 공간이 늘었다. 기존 상한(위키 10개 · 백로그 8개)은 구분선으로만 나뉜 조밀한 목록을 전제한 값이라, 카드 레이아웃에서는 두 열의 높이가 화면을 크게 넘겨 홈이 "요약"이 아니라 "긴 목록"으로 읽힌다.

홈은 전체 목록을 대신하는 화면이 아니다. 두 섹션 모두 `전체 보기` / `보완하기` 링크로 각각의 전용 화면(`/wiki`, `/backlog`)을 이미 갖고 있으므로, 홈에서는 더 적은 수를 보여주고 나머지는 전용 화면에 맡기는 편이 맞다.

## What Changes

홈 지식 그리드의 노출 상한을 낮춘다.

- 좌측 컴파일된 위키 문서: **10개 → 5개**
- 우측 작성 대기 백로그: **8개 → 4개**

상한을 넘는 항목은 지금과 같이 각 섹션의 전용 화면 링크로 도달한다. 정렬 기준, 필터 동작, 각 행이 보여 주는 정보(카테고리·검증 상태·인용 수·CTA)는 바뀌지 않는다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `workspace-home-dashboard`: `Two-column knowledge grid with wiki pages and backlog` 요구사항의 노출 상한을 10/8에서 5/4로 조정한다. 시나리오의 `up to 10` · `up to 8` 표현도 함께 바뀐다.

## Impact

- `apps/dashboard/components/KnowledgeGrid.tsx` — `MAX_WIKI_PAGES` · `MAX_BACKLOG_ITEMS` 상수
- `apps/dashboard/tests/KnowledgeGrid.test.tsx` — 상한 단언과 테스트 제목
- `openspec/specs/workspace-home-dashboard/spec.md` — 동기화 대상

API·스키마·RLS 변경은 없다. 상한은 서버에서 이미 워크스페이스 범위로 조회한 결과를 클라이언트에서 자르는 값이라, 데이터 접근 경계에는 영향이 없다.
