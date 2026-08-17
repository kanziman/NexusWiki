# Proposal: backlog-ask

## Why

NexusWiki에서는 컴파일된 위키 문서에서 참조되었으나 아직 대상 문서가 생성되지 않은 `[[WikiLink]]`를 레드링크 백로그(`wiki_links` 중 `to_wiki_id IS NULL`)로 관리한다.
Phase 4에서는 다음을 완결한다:
1. 미완성 백로그 화면(`/w/[workspaceId]/backlog`): 미해결 레드링크를 주제(`target_slug`)별로 집계하고, 인용 빈도(impact) 내림차순으로 정렬하여 표시하며, `[소스 추가]` 액션을 통해 `/sources?prefillTitle=...&tab=text`로 연결하여 결손 주제의 자료 보강을 유도한다.
2. 질문 응답(Ask) 화면(`/w/[workspaceId]/ask`): SSE 스트리밍 기반 다자간 대화(`meta` -> `delta*` -> `citations` -> `done`), 템플릿 선택, 질문 입력 및 실시간 인용 마커 렌더링, 우측 통합 콘텐츠 뷰어(위키/원시 소스/그래프/마인드맵) 연동.

## What Changes

1. **레드링크 백로그 화면 (`BACKLOG-01`, `BACKLOG-02`)**:
   - `apps/dashboard/components/BacklogList.tsx`: 미해결 레드링크 집계, 인용 빈도 정렬, 상단 통계 2종(미해결 백로그, 영향받는 위키), 검색 필터, 소스 추가 CTA, 인용 중인 위키 문서 링크
   - `apps/dashboard/app/w/[workspaceId]/backlog/page.tsx`: Server Component로 `wiki_links` (to_wiki_id is null) 및 `wiki_pages` 조회 후 `BacklogList`에 전달
2. **질문 응답(Ask) 통합 뷰어 (`ASK-01`, `ASK-02`)**:
   - `apps/dashboard/components/AskConversation.tsx`: SSE 스트리밍 응답 바인딩, 프롬프트 템플릿 로드, 인라인 인용 마커 연동 점검
   - `apps/dashboard/app/w/[workspaceId]/ask/page.tsx`: 대화창과 콘텐츠 뷰어 나란히 렌더링

## Validation Plan

- 단위 테스트: `BacklogList.test.tsx`, `AskConversation.test.tsx`, `ContentViewer.test.tsx`
- TypeScript typecheck, ESLint, Next.js build 전체 통과
- GitHub Issue #31 연결
