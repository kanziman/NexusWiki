## Why

공개 `/p/` 뷰어는 발행본 마크다운 조판은 내부 리더와 맞춰 두었지만, 헤더와 본문 폭이 어긋나고 같은 워크스페이스의 다른 공개 문서로 안전하게 이동할 표면이 없다. 외부 방문자는 승인본 한 장만 보고 끝나며, 시안 `nexuswiki-public-wiki-reader-v2.html` 과 실제 화면의 갭이 제품 신뢰로 읽힌다.

GitHub umbrella: https://github.com/kanziman/NexusWiki/issues/88

## What Changes

- 공개 셸을 헤더·본문이 같은 3단 트랙(`260px` · `1fr` · `240px`)을 공유하는 레이아웃으로 맞춘다.
- 사이드카 `wiki_page_publications` 만으로 공개 문서 LNB와 연관 문서 카드를 그리고, 링크는 `/p/[workspace_slug]/[page_slug]` 만 허용한다.
- 익명 게스트에게 Ask 입력 표면을 두지 않는다.
- 렌더링 UI에서 이모지를 제거하고 토큰·라인 아이콘만 쓴다.
- 워크스페이스 공개 메타와 발행 스냅샷으로 신뢰 카드를 구성하고, 하단 가입 CTA는 `/signup` 으로 보낸다.

## Capabilities

### New Capabilities

- 없음.

### Modified Capabilities

- `public-sharing`: 공개 뷰어 셸·사이드카 탐색·Ask 배제·가입 전환의 표시 계약을 보강한다.

## Impact

- `apps/dashboard/app/p/[slug]/[page]/page.tsx` 및 공개 셸 전용 클라이언트 섬
- `docs/design-systems/v2/nexuswiki-design-system.css` 섹션 18
- `docs/design-systems/v2/nexuswiki-public-wiki-reader-v2.html` 시안
- 공개 라우트 테스트. FastAPI·마이그레이션·로그인 리디자인 파일은 건드리지 않는다.
