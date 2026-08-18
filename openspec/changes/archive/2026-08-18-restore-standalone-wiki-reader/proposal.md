## Why

`/w/[workspaceId]/wiki/[slug]`는 화면을 그리지 않고 `/ask?slug=…&tab=wiki`로 리다이렉트한다. 그래서 v2 위키 문서 리더 프로토타입이 요구하는 3열 리더(본문 + 우측 목차)가 앱 어디에도 없다 — 통합 뷰어의 우측 패널에는 목차가 들어갈 자리가 없기 때문이다.

`wiki-document-reader-prd.md`는 라우트를 `/w/[workspace_id]/wiki/[slug]`로 못박고 §2.4에서 우측 목차 패널을 요구한다. 현재 계약(`wiki-page-routing`의 "Legacy wiki route redirects into the unified viewer")은 그 PRD와 정면으로 어긋난다.

용어: **리더**는 컴파일된 위키 한 편을 읽는 전용 화면이다. **통합 뷰어**는 `/ask`에서 대화와 콘텐츠를 나란히 보는 화면이다.

## What Changes

- **BREAKING** `/w/[workspaceId]/wiki/[slug]`가 리다이렉트를 멈추고 리더를 직접 렌더링한다.
- 리더에 v2 프로토타입의 본문 조판(`.reader` · `.article` · `.governance` · `.cite`)과 우측 목차 패널(`.toc`)을 적용한다.
- 통합 뷰어(`/ask`)의 콘텐츠 탭은 그대로 둔다. 인용 마커 클릭이 뷰어 탭으로 이어지는 계약은 유지된다.

## Capabilities

### Modified Capabilities

- `wiki-page-routing`: 위키 상세 라우트가 통합 뷰어로 리다이렉트하는 대신 리더를 직접 렌더링한다.
- `unified-workspace-viewer`: 위키 탭이 위키 문서의 유일한 열람 경로라는 전제를 없앤다. 뷰어는 대화 근거 확인용으로 남는다.

## Impact

- `apps/dashboard/app/w/[workspaceId]/wiki/[slug]/page.tsx`, `WikiPageContent.tsx`, `nexuswiki-design-system.css`.
- `tests/wiki-page-route.test.tsx`의 리다이렉트 단언이 렌더링 단언으로 바뀐다.
