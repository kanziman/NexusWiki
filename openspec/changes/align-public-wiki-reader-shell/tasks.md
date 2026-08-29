## 1. 공개 뷰어 3단 셸을 맞추고 Ask·이모지를 배제한다

- [x] 1.1 넓은 뷰포트에서 헤더와 본문이 같은 3단 트랙을 공유하고, Ask와 이모지 없이 신뢰 카드·승인 인용이 보인다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/90)
  - Given: 워크스페이스 공개 슬러그가 있고 검증된 문서가 발행되어 있다.
  - When: 비로그인 방문자가 넓은 뷰포트에서 `/p/[workspace_slug]/[page_slug]` 를 연다.
  - Then: 헤더 마크와 본문 왼쪽 가장자리가 한 수직선에 맞고, 질문 입력과 이모지 글리프가 없으며, 워크스페이스 표시명·검증 배지·발행일·승인 인용 카드가 보인다.
  - Verification: `cd apps/dashboard && pnpm exec vitest run tests/public-wiki-page-route.test.tsx tests/wiki-document.test.ts`

## 2. 사이드카 공개 문서 탐색과 가입 전환을 제공한다

- [x] 2.1 같은 워크스페이스의 다른 발행본이 LNB와 연관 카드로 `/p/` 링크만 노출되고 가입 CTA는 `/signup` 이다. (GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/91)
  - Given: 슬라이스 1이 통과한 공개 뷰어가 있고, 같은 워크스페이스에 다른 발행본이 하나 더 있다.
  - When: 비로그인 방문자가 한 발행본의 `/p/` 페이지를 연다.
  - Then: 공개 문서 목록과 연관 카드가 그 다른 발행본의 제목을 `/p/[workspace_slug]/[page_slug]` 로만 연결하고 `/w/` 링크가 없으며, 전환 동작은 `/signup` 으로 이동한다.
  - Verification: `cd apps/dashboard && pnpm exec vitest run tests/public-wiki-page-route.test.tsx tests/wiki-document.test.ts`
