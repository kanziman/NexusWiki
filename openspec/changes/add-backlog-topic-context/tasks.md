Umbrella: https://github.com/kanziman/NexusWiki/issues/37

## 1. 백로그 주제의 원문 표기 복원

Issue: https://github.com/kanziman/NexusWiki/issues/38

- [ ] 1.1 목록 라벨이 인용 문서 본문에서 복원한 `[[표기]]`를 쓴다.
  - Given: 결손 주제 `rls-정책v2`를 인용하는 위키 본문에 `[[RLS 정책(v2)]]`가 들어 있다.
  - When: 멤버가 `/w/[workspaceId]/backlog`를 연다.
  - Then: 행 라벨이 `RLS 정책(v2)`로 표시되고, 원본 slug는 보조 줄에 그대로 남는다.
  - Then: 인용 문서들이 서로 다르게 표기하면 최빈 표기가, 동수면 위키 제목 오름차순 첫 문서의 표기가 선택되며 렌더를 반복해도 값이 바뀌지 않는다.
  - Then: 어느 본문에서도 표기를 찾지 못하면 기존 slug 역변환으로 폴백한다.
  - Verification: `cd apps/dashboard && pnpm vitest run tests/BacklogList.test.tsx && pnpm typecheck && pnpm lint`

- [ ] 1.2 인용 문서 조회를 결손이 있는 문서로 제한한다.
  - Given: 워크스페이스에 위키 문서가 다수 있고 그중 일부만 미해결 링크를 품는다.
  - When: 백로그 라우트가 본문을 읽는다.
  - Then: `wiki_pages.content` 조회가 미해결 링크의 `from_wiki_id` 집합으로 제한되고, 백로그가 비어 있으면 본문 조회가 발생하지 않는다.
  - Then: 조회는 요청자 세션으로 나가며 `service_client`를 쓰지 않는다.
  - Verification: `cd apps/dashboard && pnpm vitest run tests/backlog-page-route.test.tsx && pnpm typecheck`

## 2. 백로그 주제 상세 패널

Issue: https://github.com/kanziman/NexusWiki/issues/39

- [ ] 2.1 행을 열면 주제 상세가 패널로 열린다.
  - Given: 백로그 목록에 주제가 하나 이상 있다.
  - When: 멤버가 주제 행을 연다.
  - Then: 패널이 표기, 최초 감지 시각, 인용 중인 위키 목록, 소스 추가 동선을 보여준다.
  - Then: 패널의 소스 추가가 목록 행과 동일하게 `/w/[workspaceId]/sources?prefillTitle=<표기>&tab=text`로 이동한다.
  - Then: 인용 문서를 누르면 해당 위키 문서로 이동한다.
  - Verification: `cd apps/dashboard && pnpm vitest run tests/BacklogList.test.tsx && pnpm build` 후 번들 CSS에 섹션 17 패널 클래스 정의 존재 확인

## 3. 인용 문맥 발췌

Issue: https://github.com/kanziman/NexusWiki/issues/40

- [ ] 3.1 패널이 인용 문서마다 링크 주변 발췌를 보여준다.
  - Given: 인용 문서 본문에 결손 주제로의 링크가 포함돼 있다.
  - When: 멤버가 그 주제의 패널을 연다.
  - Then: 인용 문서마다 링크 등장 지점 주변을 자른 스니펫이 하나씩 표시되고, 잘린 쪽에 말줄임이 붙는다.
  - Then: 한 문서에 같은 링크가 여러 번 나오면 첫 등장만 쓴다.
  - Then: 발췌와 라벨 어디에도 `[[` `]]`가 노출되지 않는다.
  - Then: 위키 본문 전문이 클라이언트로 전달되지 않는다 — 서버가 만든 스니펫만 내려간다.
  - Verification: `cd apps/dashboard && pnpm vitest run && pnpm typecheck && pnpm lint && pnpm build`
