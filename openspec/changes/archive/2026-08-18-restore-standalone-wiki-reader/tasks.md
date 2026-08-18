## 1. 리더 라우트 복원

- [x] 1.1 `/w/[workspaceId]/wiki/[slug]`가 리다이렉트 대신 리더를 렌더링한다.
  - Given: 워크스페이스 멤버가 존재하는 위키 슬러그를 연다.
  - When: 라우트가 요청자 세션으로 페이지를 조회한다.
  - Then: 같은 라우트에서 문서 본문과 목차가 렌더링되고 `/ask`로 이동하지 않는다.
  - Verification: `pnpm test -- --run`, `pnpm typecheck`, `pnpm lint`.

- [x] 1.2 malformed 슬러그와 조회 실패는 기존 not-found 문구를 그대로 유지한다.
  - Given: 슬러그가 깨졌거나 워크스페이스 밖 문서를 가리킨다.
  - When: 라우트가 이를 처리한다.
  - Then: 500 없이 고정 not-found 문구만 노출한다.
  - Verification: 위와 같음.

## 2. 리더 조판

- [x] 2.1 프로토타입의 본문 조판과 목차 패널을 적용한다.
  - Given: 리더가 컴파일된 마크다운과 인용 앵커를 받는다.
  - When: 사용자가 문서를 읽는다.
  - Then: `.reader`/`.article`/`.governance`/`.cite`/`.toc` 계약대로 렌더링되고 960px 이하에서 목차가 숨는다.
  - Verification: `pnpm build` 후 번들 CSS에 해당 클래스 정의 존재 확인.
