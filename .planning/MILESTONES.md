# Milestones

## v1.0 Living Wiki MVP (Shipped: 2026-08-13)

**Phases completed:** 7 phases, 55 plans, 85 tasks

**Key accomplishments:**

- 단일 uv lockfile 위에서 공용 structlog를 쓰는 FastAPI와 worker가 기동하고, readiness와 SIGTERM 종료까지 검증되는 tracer를 구축했다.
- 비공개 `sources` 버킷에서 UUID 3세그먼트 경로와 워크스페이스 역할을 함께 강제하고, 거부 동작을 재실행 가능한 SQL로 증명했다.
- Singapore Supabase Cloud now carries migrations `0001`~`0006` in order, with a private sources bucket, three storage policies, and sanitized audit evidence.
- Supabase Auth가 로컬·클라우드 모두 최소 12자와 이메일 확인을 강제하며, 실제 HTTP 거부와 계정 정리를 재실행 가능한 스크립트로 증명한다.
- Next.js 15.5.22 대시보드가 Tailwind 4 CSS-first, strict TypeScript, 정확히 2건의 Vitest와 재현 가능한 dev 스모크 경로를 갖췄다.
- 비루트 venv-only Docker 이미지 하나가 Railway Singapore의 api와 worker에서 실행되며, 서비스별 비밀 격리와 paired deployment 관측으로 동일 코드를 증명했다.
- Python과 dashboard에 좁게 적용되는 커밋 게이트와 실제 운영 설정을 기록한 루트 README를 구축했다.
- Railway Singapore에서 Supabase Singapore로 향하는 배포 worker 왕복을 실측해 p50 29.093 ms, p95 37.610 ms 기준선과 5채널 환산치를 확정했다.
- Structured logging now redacts sensitive values through mixed mapping/list/tuple payloads without changing safe scalars or container semantics.
- 50,000행 중 타깃 750행(1.5%) 적대적 코퍼스에서 RPC와 asyncpg를 각각 3회 실측해 트랜스포트를 rpc로 확정했고, 그 과정에서 `authenticated`·`service_role`이 9개 테이블에 DML 권한을 전혀 갖고 있지 않아 `0004`의 RLS 정책이 현재 무력하다는 사실을 발견했다
- api 프로세스가 service key를 담을 필드 자체를 갖지 않도록 pydantic-settings 3계층을 세우고, 그 규칙을 집행할 ruff TID와 worker 테스트 수집을 켰다
- service key 클라이언트를 인자 없이는 만들 수 없게 만들고, RLS가 되돌려준 0행이 조용한 성공이 되지 않도록 0행·다중행·42501을 한 함수에서 Forbidden으로 렌더한다
- 02-03이 `MockTransport`로 가정했던 "RLS가 막은 쓰기는 0행으로 돌아온다"를 로컬 스택 상대의 실제 왕복으로 확인하고, 그 테스트가 공허하지 않음을 정책을 실제로 깨서 증명했다
- 색인과 질의가 같은 함수를 쓰도록 강제하는 `normalize`/`bigram` 쌍과, LLM이 아니라 순수 함수가 소유하는 `slugify`를 `packages/core`에 세웠다
- 이후 페이즈가 딛고 설 스키마를 `0007` 한 파일에 담아 단일 트랜잭션으로 로컬과 `ap-southeast-1`에 같은 순서로 올렸고, 그 과정에서 `0004`의 RLS 정책 20여 개를 무력하게 만들고 있던 권한 공백을 닫았다
- LLM 비용 0인 상태에서 claim→complete 왕복 · `attempts`를 소모하지 않는 SIGTERM 반납 · 미등록 type의 데드레터 세 경로를 고정했고, 그 과정에서 0행 RPC가 성공으로 읽히던 어댑터 결함을 잡았다
- Railway `asia-southeast1` worker가 `ap-southeast-1` Supabase를 상대로 `noop` claim→complete 왕복 219회를 실측해 p99 127.054 ms를 얻었고, 그 숫자가 실제로 말해 주는 것은 "reap 타임아웃을 정하는 것은 전송이 아니라 핸들러 지속시간"이라는 사실이다
- 위반 픽스처에 자격증명 모양의 값을 쓰지 않았다.
- 1. [Rule 1 - Bug] 함수 인자의 typmod는 저장되지 않는다 — 계약 5를 행동 단언으로 교체
- 1. [Rule 1 - Bug] 월 경계 비교식이 세션 TimeZone에 의존했다
- 1. [Rule 1 - Bug] 오버랩이 산문에서 아예 생기지 않았다
- 1. [Rule 1 - Bug] `LLM_MODEL` 슬러그가 404였다
- 1. [Rule 1 - Bug] PostgREST가 비용 상한 SQLSTATE 53400을 opaque 500으로 마스킹했다.
- 1. [Rule 3 - Blocking] 프로젝트 실행 경로의 pre-commit 이진 파일 부재
- 1. [Rule 1 - Bug] wiki 재처리가 이미 같은 version인 벡터를 다시 호출했다
- 해시로 고정된 12/12/8 코퍼스와 다국어 골든 36문항 위에서 fail-closed 하는 벤치마크 CLI, 그리고 "측정하지 않았음"을 덮지 않는 순서 모드·그래프 결정 기록과 정책 변경 증거 게이트
- The worker’s private query-embedding listener now has a bounded monotonic token bucket that recovers capacity without weakening authentication, validation, redaction, or concurrency controls.
- A reset local Supabase stack now proves both vector retrieval shapes choose their exact deployed HNSW indexes through authenticated, security-equivalent direct JSON-plan queries.
- Deterministic 100,000-vector paired HNSW records retained with strict-order and graph-off approved as unchanged defaults.
- Fixed the exact runner-identity gap 04-VERIFICATION.md found in `compare_order_records()` — `_pins()` now includes `git_sha` and the comparator asserts a distinct `{strict_order, relaxed_order}` pair — then used the fixed comparator to produce and validate a genuinely comparable v5 strict/relaxed pair from one identical commit, closing RTV-04.
- Worker-owned `/internal/llm-chat` streaming listener plus `POST /workspaces/{id}/ask` — SSE-streamed, dual-cited answers where citations are computed as parsed-anchor ∩ server-issued-alias-map, never the raw retrieval list.
- Migration `0012_ask_citation_and_graph.sql` — corrected ask-template citation wording to D-02's short-alias scheme, added a bounded SECURITY INVOKER graph-read RPC (`wiki_graph_neighborhood`), a bounded service_role-only conflict-candidate RPC (`find_similar_wiki_pages`), and a DB-enforced verification-transition audit trigger (`stamp_wiki_verification`) — applied to both local stack and Supabase Cloud.
- Ask responses now measure citation coverage, ingested sources lose forged anchors before chunking, and callers can safely choose visible prompt templates.
- Ask now enforces the workspace's monthly cost cap before contacting OpenRouter and records each completed stream as a usage event.
- 위키 검증 전이는 RLS와 DB 트리거가 보증하고, 그래프 조회는 요청 전에 엄격한 상한을 검증한다.
- Each completed wiki embedding now triggers a bounded, write-time contradiction check that marks both genuinely conflicting pages disputed.
- Ask budget preflight now reads the complete database aggregate, while service-role conflict automation preserves human verification audit history.
- Email+password login via `@supabase/ssr`, `middleware.ts` as the sole D-02 session-cookie writer, and `/w/[workspaceId]` reading real workspace data through RLS with the requester's own JWT — plus the Tailwind 4 `@theme` integration every later Phase 6 component consumes.
- Radix dropdown-menu workspace switcher wired to `workspacePath()` navigation, plus a `NavShell` replacing 06-01's bare header with real links to all five remaining Phase 6 surfaces — UI-01 is now fully satisfied end to end.
- A working member roster + email-based invite for UI-02/D-04, closing a real backend gap (no email->user_id resolution path existed anywhere) with two new SECURITY DEFINER RPCs (migration 0014) mirroring 0001's established idiom, wired end to end through MembersList.tsx and a TDD-built InviteForm.tsx.
- Authenticated fetch wrapper (`apiFetch`/`ApiError`) mirroring apps/api's error taxonomy, plus a generic chunk-boundary-safe SSE frame parser (`parseSseStream`) — the two shared modules every later Phase 6 plan calling `apps/api` or consuming the Ask stream will import.
- Real 3-tab source ingest (file/URL/text, raw-bytes upload, D-06) wired to a live 5-stage job-chain stepper (D-05) with dead-job retry and cost-disclosure cancel confirmation (D-08), backing the `/sources` route with an SSR-first, RLS-scoped source list.
- 1. [Rule 2 - Missing Critical Functionality] Added optional `workspaceId` prop to `CitationSidePanelProps`
- Read-only wiki viewer — `[[WikiLink]]` navigation with a client-side `_base_slug` port, four verification-status callouts, a disputed-conflict callout that always outranks them, and a red-link CTA that routes to source creation rather than any page-edit surface. This is the final plan of Phase 6 (8/8) — all six Phase 6 requirements (UI-01 through UI-06) are now delivered.
- Cytoscape knowledge-graph canvas (`GraphCanvas.tsx`) built on direct `wiki_pages`/`wiki_links` PostgREST reads with an explicit, visible 1000-row-cap notice, plus a `GraphLensFilter.tsx` category chip filter driving the `?category=` URL param — UI-06 is now satisfied, completing all 6 Phase 6 requirements.

---
