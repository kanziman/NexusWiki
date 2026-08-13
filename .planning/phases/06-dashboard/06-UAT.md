---
status: complete
phase: 06-dashboard
source: [06-VERIFICATION.md]
started: 2026-08-13T00:20:00+09:00
updated: 2026-08-13T10:35:00+09:00
---

## Current Test

[testing complete]

## Tests

### 1. Full ingest flow — dropzone to job-chain completion
expected: 실제 단계 이름으로 진행 표시, dead job 재시도 버튼, 종료 상태에서 폴링 정지·재시도 시 재개
result: pass
source: automated
evidence: |
  이전 세션의 .env 접근 차단이 해소되어(worker-parse-jsondecodeerror 디버그 세션에서 확인)
  apps/api(port 8000)+worker를 로컬 스택 대상으로 실제 기동하고, plain Playwright 스크립트로
  dev-test@example.test 로그인 후 dev-test-workspace에서 텍스트 소스를 실제로 등록했다.
  JobStepper가 업로드→파싱→컴파일→링크 동기화→임베딩 5단계를 실제 잡 타입으로 순서대로
  표시했고(스크린샷으로 진행 중 "컴파일" 단계가 강조 표시됨을 확인), 임베딩 단계가 실제로
  dead 상태가 되어 "임베딩 단계에서 실패했습니다 — ... 재시도를 눌러 다시 시도하세요." 배너와
  재시도 버튼이 렌더됨을 확인했다(폴링은 4단계 모두 종결 상태에 도달하자 자동 정지 — WR-04).
  재시도 버튼을 클릭하자 폴링이 재개되고 임베딩 단계가 성공으로 전환, 5단계 전부 초록 체크로
  귀결되는 것을 확인했다. 테스트에 쓴 raw_source/wiki_page/jobs/usage_events는 전부 삭제,
  0행 확인.
  ⚠️ 실제 발견된 문제(코드 결함 아님): 임베딩 단계가 처음에 dead로 간 원인은
  `.env`에 `EMBEDDING_MODEL`/`EMBEDDING_PROVIDER`가 없어 OpenRouter에 `model: null`을
  보내 400을 받은 것 — `worker/settings.py`가 의도적으로 코드 기본값을 두지 않는 필드라
  이 프로젝트의 로컬 개발 환경이 이 코드 경로를 처음 실행했을 때만 드러나는 설정 누락이었다.
  `.env.sample`에 이미 관측·기록된 값(`docs/ops/openrouter-contract-record.md`)을
  `.env`에 추가해(EMBEDDING_MODEL=baai/bge-m3, EMBEDDING_PROVIDER=deepinfra/fp32) 해결.
  코드는 변경하지 않았다.

### 2. Full ask flow — dual-citation markers
expected: |
  Ask a real question against seeded evidence. Placeholder markers are inert during
  streaming; after the citations SSE frame they become clickable numbered badges. Clicking
  a wiki-kind marker and a source-kind marker within the same dual-cited sentence each opens
  exactly its own cited content (single-card-per-click is the accepted interpretation of
  D-10 per the applied override — this test also confirms/refutes whether that's sufficient
  in practice).
result: pass
source: automated
evidence: |
  Test 1이 만든 위키 페이지("NexusWiki 인제스트 흐름 UAT 검증")를 근거로, 실 로그인 세션에서
  Ask UI에 실제 질문("...무엇을 확인하기 위해 등록되었나요?")을 제출했다. apps/api의 /ask
  SSE 스트림이 실제 OpenRouter LLM 호출(LLM_STREAM_INTERNAL_URL/TOKEN 경유 worker 내부
  리스너)로 답변을 스트리밍했고, citations 프레임 도착 후 답변 본문에 클릭 가능한 숫자
  배지 6개가 렌더됐다. 6개 마커를 전부 순서대로 클릭해 CitationSidePanel이 매번 실제
  콘텐츠로 열리는 것을 확인: source/wiki/source/wiki/source/wiki로 정확히 교차하며, 각각
  "원문 인용"/"위키 인용" 헤더와 실제 청크·위키 본문이 표시됨(위키 카드에는 "위키
  페이지에서 전체 보기" 링크까지 확인). D-10 accepted override(마커별 단일 카드, 인접
  마커 클릭으로 양쪽 확인)가 실제로 충분히 작동함을 확인 — 같은 문장의 wiki/source 마커가
  각자 정확히 자신의 인용만 보여주고 섞이지 않았다. 테스트 데이터는 test 1과 함께 정리,
  0행 확인.

### 3. Wiki viewer — all verification states + red links
expected: |
  Seed wiki_pages covering all 4 verification states (verified/expired/partial/unverified) +
  disputed + a resolved/red WikiLink pair. Read-only banner always shown. Correct callout per
  state. Disputed always takes visual priority over the verification callout. Resolved
  WikiLinks navigate; red links show the "아직 작성되지 않음 · 지금 생성" CTA and route to
  /sources with prefill (WINDOWS.md #12).
result: pass
source: automated
evidence: |
  Seeded a throwaway workspace with 6 wiki_pages (verified/expired/partial/unverified/disputed
  + a resolved-link target) plus a resolved and an unresolved wiki_link, via docker exec psql
  against the local Supabase stack. Drove the dashboard (next dev, port 3000) with a plain
  Playwright script (no gstack) as a real logged-in user. Confirmed: read-only banner on every
  page; exact callout text per state (검증됨/검증 만료됨/부분 검증됨/no callout for
  unverified); disputed page shows the disputed callout and NOT the verified callout (priority
  confirmed); resolved WikiLink renders as a real link; red WikiLink renders the CTA with
  aria-label="지금 생성". All seed data deleted afterward, verified 0 rows remaining.
  ⚠️ Found and fixed a real bug along the way (unrelated to this test's own assertions but
  discovered while getting the dashboard running): lib/env.ts's requireEnv() used
  `process.env[name]` (dynamic bracket access), which Next.js/webpack cannot statically inline
  into the client bundle — this broke EVERY client-side env read, including login itself. This
  was a regression from this session's own WR-05 code-review fix. Fixed with a switch-based
  lookup (see commit 1a11a1d) that stays both statically analyzable and per-call fresh (a
  first attempt using a module-scope object literal broke 14 vitest tests that mock
  process.env between calls — reverted in favor of the switch).

### 4. Graph canvas — 1000-node cap notice
expected: |
  Seed a workspace with >1,000 wiki_pages, load the graph canvas. The exact cap notice
  "이 워크스페이스는 그래프 표시 한도(1,000개 노드)를 초과했습니다 — 카테고리 필터로 범위를
  좁혀주세요." appears — never a silent truncation — and does NOT appear at exactly 1,000
  rows (WR-01 off-by-one fix).
result: pass
source: automated
evidence: |
  Seeded 1001 wiki_pages in a throwaway workspace via psql, loaded /graph as a real logged-in
  user via Playwright. First attempt failed: found and fixed a second real bug —
  GraphCanvas.tsx's edge query filtered `from_wiki_id IN (...)` with up to 1000 UUIDs, producing
  a URL long enough that the request failed outright (browser reported it as a CORS error; the
  real cause was URL-length rejection) — this broke the graph canvas completely exactly in the
  large-workspace case UI-06 exists to handle gracefully. Fixed by scoping the edge query to
  workspace_id only and relying on the client-side nodeIdSet filter the component already had
  (commit 613e5bc). After the fix: PostgREST content-range header confirmed count=1001, the
  exact cap-notice copy rendered. All seed data deleted afterward, verified 0 rows remaining.

### 5. Member removal under RLS-blocked condition
expected: |
  Attempt to remove a member in a state where RLS should block the delete. The
  "멤버를 제거하지 못했습니다." banner is shown and the member stays in the list (06-REVIEW-FIX.md
  WR-03 fix — confirms a 0-row delete result is detected, not silently treated as success).
result: pass
source: automated
evidence: |
  Created a throwaway workspace with an owner + a second (editor) member. Loaded /settings as
  the owner in a real browser session (client caches isOwner=true from the initial fetch).
  Without refreshing, transferred real ownership to the second member out-of-band via psql
  (workspaces.owner_id, then both members' workspace_members.role — the protect_owner_membership
  trigger requires owner_id to move first). Clicked the still-rendered "제거" button on the
  now-actual-owner: the RLS policy blocked the delete (0 rows, no error), the fix's
  post-delete .select() row-count check detected it, and the "멤버를 제거하지 못했습니다." error
  banner rendered. Confirmed via psql that the member was NOT removed. Restored original
  ownership and cleaned up all seed data afterward, verified 0 rows remaining.

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

## Bugs Found and Fixed During UAT (not user-reported issues — found via automated live testing)

- **lib/env.ts dynamic env access** (test 3): broke all client-side env reads including login.
  Fixed in commit `1a11a1d`.
- **GraphCanvas.tsx edge-query URL-length failure** (test 4): broke the graph canvas entirely
  near the 1000-node cap. Fixed in commit `613e5bc`.
- **worker `_rpc()` didn't handle PostgREST 204 No Content** (test 1, found in the preceding
  `/gsd-debug` session): `returns void` lexical-index RPCs crashed the parse handler with
  `JSONDecodeError`. Fixed in commit `bf338a8` (separate debug session, resolved at
  `.planning/debug/resolved/worker-parse-jsondecodeerror.md`).
- **Local `.env` missing `EMBEDDING_MODEL`/`EMBEDDING_PROVIDER`** (test 1): not a code defect —
  worker/settings.py intentionally has no code default for these two fields, and this local
  dev environment had never exercised the embed job's live path before. Added the values
  already verified and recorded in `.env.sample` / `docs/ops/openrouter-contract-record.md`.

All fixes verified: `tsc --noEmit` clean, 77/77 vitest passing (dashboard fixes), 410/410
pytest passing (worker fix), and live Playwright re-runs confirming each fix in the browser
against the real local stack.
