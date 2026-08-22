## 1. 라우트 · 환경 게이트

- [x] 1.1 `apps/dashboard/app/w/[workspaceId]/debug/retrieval/layout.tsx` 신설 — `process.env.NODE_ENV !== "development"`면 `notFound()` (design.md Decision 1·2)
- [x] 1.2 `apps/dashboard/app/w/[workspaceId]/debug/retrieval/page.tsx` 신설 — 질의 입력 폼 + `requested_k` 선택(1~8, `RetrievalRequest.requested_k` 상한과 일치) + 결과 렌더링을 얹을 클라이언트 컴포넌트를 감싼다

## 2. 조회 로직

- [x] 2.1 `apiFetch<RetrievalResponse>`로 `POST /workspaces/{workspaceId}/retrieval` 호출 — `AskConversation.tsx`처럼 SSE 파서 없이 일반 JSON 응답으로 처리
- [x] 2.2 채널 키 4종(`wiki_vector` · `source_vector` · `wiki_lexical` · `source_lexical`)을 상수로 고정한다. 응답 `meta`에 없는 키가 오면 "알 수 없는 채널"로 방어적으로 표시한다(design.md Risks)
- [x] 2.3 각 `evidence` 항목의 융합 총점을 `Object.values(contributions).reduce((a,b)=>a+b,0)`로 파생한다 — 응답에 사전 계산된 총점 필드가 없다(design.md Decision 3)

## 3. 화면 구성

- [x] 3.1 상단에 `meta.policy_version` · `meta.elapsed_ms` · 채널별 `status`/`returned`/`elapsed_ms`를 요약 표시한다
- [x] 3.2 4채널 원시 결과를 채널별 카드/열로 나란히 보여준다(순위·evidence id·metadata 일부)
- [x] 3.3 RRF 융합 랭킹을 총점 내림차순 표로 보여준다 — 문서 id · 참여 채널 목록 · 채널별 기여 점수 · 총점
- [x] 3.4 `meta.<channel>.status !== "ok"`이거나 `returned === 0`인 채널은 카드를 숨기지 않고 그 상태를 그대로 표시한다(델타 스펙 "A channel returns no results or fails" 시나리오)
- [x] 3.5 질의가 비었거나 API가 4xx/5xx를 반환하면 `ApiError.detail`을 사용해 에러 상태를 보여준다(`apiFetch`의 기존 에러 계약 그대로 사용)

- [x] 3.6 채널별 원시 결과 항목에 "내용 보기" 토글을 추가한다 — 클릭 시 `createClient()`(user JWT)로 evidence.kind·channels에 맞는 테이블(`wiki_embeddings.chunk_content` · `wiki_pages.content` · `source_chunks.content`)을 조회한다(design.md Decision 5, 4.2 실사용 검증 중 추가된 범위)

## 4. 검증

- [x] 4.1 `pnpm typecheck` · `pnpm lint` · `pnpm test` · `pnpm build` 통과
- [x] 4.2 로컬 `pnpm dev`에서 실제 로그인 세션으로 질의를 던져 4채널 결과와 융합 랭킹이 실제 응답과 일치하는지 육안 확인
- [x] 4.3 `pnpm build && pnpm start`(프로덕션 빌드)로 `/w/[workspaceId]/debug/retrieval`이 404를 반환하는지 확인 — `NODE_ENV=production`에서 게이트가 실제로 막는지가 이 change의 핵심 안전장치다
- [x] 4.4 `openspec validate retrieval-debug-viewer --strict` 통과
- [ ] 4.5 **[Claude 전용, Codex는 건너뛴다]** 리뷰 게이트: `tenant-isolation-reviewer` — 새 라우트가 `service_role`을 쓰지 않고 요청자 JWT만 쓰는지, 워크스페이스 경계를 벗어난 조회가 없는지 확인. `spec-conformance-reviewer` — 델타 스펙 시나리오 5건 충족 확인. Codex는 4.4까지 끝낸 뒤 AGENTS.md 6단계(spec sync)·7단계(archive)까지 마치고 커밋한 다음 멈춘다 — push·PR로 진행하지 않는다. 리뷰 두 건이 `pass`로 확정된 뒤에만 9단계(PR)를 재개한다.
