## 1. 검증된 위키를 리더에서 공개 발행하고 링크를 복사한다

- [x] 1.1 editor 이상이 검증된 문서를 리더에서 발행하면 스냅샷이 저장되고 공개 링크가 복사된다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/83)
  - Given: 워크스페이스 공개 슬러그가 있고, editor 이상이 검증된 위키 문서를 리더에서 보고 있다.
  - When: 리더의 공개 발행 동작을 실행한 뒤 공개 링크 복사를 실행한다.
  - Then: `wiki_page_publications`에 현재 제목·본문·슬러그·인용 출처 스냅샷이 요청자 `published_by`로 저장되고, 클립보드에는 `/p/[workspace_slug]/[page_slug]`가 들어간다. 남의 워크스페이스 발행 시도는 HTTP 403이다.
  - Verification: `cd apps/api && uv run pytest tests/test_wiki_publication.py tests/test_workspaces_isolation.py -q -k "publication or verify_foreign"`, `cd apps/dashboard && pnpm exec vitest run tests/WikiPageContent.test.tsx`

## 2. 발행을 취소하고, viewer·미검증 문서는 발행하지 못한다

- [x] 2.1 발행된 문서는 리더에서 내릴 수 있고, viewer와 미검증 문서에는 발행 동작이 없다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/84)
  - Given: 슬라이스 1이 통과해 발행된 문서가 있고, 같은 워크스페이스에 viewer와 미검증 문서가 있다.
  - When: editor가 발행 취소를 실행하고, viewer 또는 미검증 문서 리더를 연다.
  - Then: 해당 발행 행이 삭제되어 리더가 다시 공개 발행 동작을 보여 준다. viewer와 미검증 문서에는 동작하는 공개 발행 컨트롤이 없다. viewer의 삭제 시도는 HTTP 403이다.
  - Verification: `cd apps/api && uv run pytest tests/test_wiki_publication.py -q`, `cd apps/dashboard && pnpm exec vitest run tests/WikiPageContent.test.tsx tests/wiki-page-route.test.tsx`

## 3. 공개 뷰어 본문을 내부 리더와 같은 조판으로 맞춘다

- [x] 3.1 공개 `/p/` 본문이 내부 리더와 같은 마크다운 조판을 쓰고, 위키 링크·관련 문서 원문 목록을 노출하지 않는다.
  - Given: 발행본 마크다운에 제목·리스트·강조와 끝의 `## 관련 문서` 구간이 있다.
  - When: 비로그인 방문자가 `/p/[workspace_slug]/[page_slug]` 를 연다.
  - Then: 리스트와 강조가 HTML로 렌더되고 원문 `**`·`- ` 문법이 보이지 않으며, `/w/` 링크와 관련 문서 원문 목록이 없다.
  - Verification: `cd apps/dashboard && pnpm exec vitest run tests/public-wiki-page-route.test.tsx tests/wiki-document.test.ts tests/WikiPageContent.test.tsx`
