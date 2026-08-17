# Design: backlog-ask

## Architecture & Invariants

1. **백로그의 본질 (Derived State)**:
   - 백로그는 별도의 테이블이 아니며 `wiki_links` 중 `to_wiki_id IS NULL`인 행이다.
   - `distinct target_slug`로 집계하여 주제 수를 도출하고, `impact`(`count(*)`) 기준 내림차순 정렬한다.
   - 불변식 §1(2계층 브레드크럼), 불변식 §7(토큰 전용 색상) 준수.
2. **소스 보강 동선**:
   - `[소스 추가]` 버튼은 `/w/[workspaceId]/sources?prefillTitle=${encodeURIComponent(target_slug)}&tab=text`로 이동.
3. **Ask 대화 상태 머신**:
   - `AskConversation`은 `meta -> delta* -> citations -> done` SSE 스트림을 처리하며 `CitationMarker`로 인라인 칩을 렌더링한다.

## Components & Data Contracts

- `BacklogItem`:
  ```typescript
  export type BacklogItem = {
    target_slug: string;
    impact: number;
    first_detected_at: string;
    referencing_pages: { id: string; slug: string; title: string }[];
  };
  ```
- `BacklogListProps`:
  ```typescript
  export type BacklogListProps = {
    workspaceId: string;
    initialItems: BacklogItem[];
  };
  ```
