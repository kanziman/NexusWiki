# Phase 6: Dashboard - Context

**Gathered:** 2026-08-12 (interactive discussion for auth/workspace-switching, dropzone/job-progress, Ask UI citation areas; remaining implementation details for wiki viewer/canvas left to Claude's discretion per user's explicit "recommend best practice and apply" instruction mid-session)
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the browser-only surface for operating a workspace end to end: authenticate, switch/invite within a workspace, drop sources in and watch real job-chain progress, ask questions and see dual-cited answers, browse the read-only compiled wiki, and (last, lowest-priority surface) explore the knowledge graph. This phase consumes Phase 5's Ask/read APIs and Phase 2's auth/RLS spine as-is — it does not add backend capabilities, does not change the SSE contract or citation-anchor scheme, and does not introduce a graph database. 6 requirements: UI-01 (auth + `/w/[workspaceId]` tenancy source of truth), UI-02 (workspace switching + invite + roles), UI-03 (dropzone + real job-stage progress), UI-04 (Ask UI + inline dual-citation), UI-05 (read-only wiki viewer + red links), UI-06 (Cytoscape canvas, last surface, 1000-row cap handling).

</domain>

<decisions>
## Implementation Decisions

### 인증 & 세션 (Auth & Session)
- **D-01:** 로그인은 이메일 + 비밀번호만 지원한다 (매직링크/OAuth 없음). Supabase Auth 기본 흐름을 그대로 사용. — **Reversibility:** costly — 이후 매직링크/OAuth를 추가하려면 로그인 폼과 auth 상태 분기를 다시 설계해야 한다.
- **D-02:** 세션/쿠키는 `@supabase/ssr` 공식 패키지로 처리하며, `middleware.ts`가 **유일한 쿠키 기록자**다 — UI-01의 명시적 요구("`/w/[workspaceId]`가 테넌시의 단일 진실 소스")와 CLAUDE.md의 CVE-2025-29927(미들웨어 우회) 제약을 동시에 만족한다. — **Reversibility:** one-way — 이 프로젝트의 테넌트 게이트가 미들웨어이므로, 커스텀 쿠키 구현으로 되돌리면 검증된 CVE 회피 경계가 깨진다.

### 워크스페이스 전환 & 멤버 초대
- **D-03:** 워크스페이스 전환은 상단 네비게이션 드롭다운으로 하고, 선택 시 `/w/[workspaceId]`로 이동한다 (URL이 소유 — React state의 낡은 id가 조용히 빈 결과를 내는 것을 방지, UI-01 rationale).
- **D-04:** 멤버 초대(이메일 입력 + owner/editor/viewer 3역할 부여)는 워크스페이스 설정 페이지의 전용 폼에서 이루어진다 (모달 아님).

### 소스 드롭존 & 잡 진행 상태 (best-practice 적용, 사용자 확인)
- **D-05:** 잡 진행은 실제 단계 이름의 스테퍼/체크리스트로 표시한다 — "업로드 → 파싱 → 컴파일 → 링크 동기화 → 임베딩" (ING-06 요구사항 문구 그대로, 불확정 스피너 금지 — 4분짜리 컴파일이 멈춘 것처럼 보이면 재투입으로 비용이 2배가 된다).
- **D-06:** 드롭존은 파일 드래그앤드롭 + URL 입력 + 텍스트 붙여넣기를 탭 전환으로 한 컴포넌트에 통합한다.
- **D-07:** 동일 `content_hash` 재투입 시 "이미 수집됨 — 건너뜀"을 눈에 띄는 배너로 표시한다 (ING-02 — 조용한 성공 금지).
- **D-08:** `dead` 상태 잡에는 재시도 버튼을 노출한다 (ING-07).

### Ask UI — 인용 마커 & 이중 Citation 카드 (best-practice 적용, 사용자 확인)
- **D-09:** 인용 마커는 근거가 되는 절 옆에 위첨자 번호 배지(`[1]`, `[2]`) 형태로 인라인 배치한다. 스트리밍 중에는 회색 placeholder로 나타났다가, `citations` 이벤트 도착 시 in-place로 실제 링크로 치환된다 (API-01의 `meta`→`delta*`→`citations`→`done` 이벤트 순서를 그대로 소비 — 마커는 스트림 종료 전까지 활성화되지 않는다).
- **D-10:** 마커 클릭 시 사이드 패널에 위키 카드와 원문 카드(`char_start`/`char_end` 구간 하이라이트)를 나란히 표시한다.
- **D-11:** 근거 없음 상태("근거를 찾지 못했습니다", CITE-04)는 채팅 버블과 시각적으로 구분되는 경고 카드로 렌더링한다.

### Claude's Discretion
- **위키 뷰어(UI-05)와 Cytoscape 캔버스(UI-06)의 세부 UX는 이번 세션에서 논의되지 않았다** — 사용자가 이 두 영역을 논의 대상으로 선택하지 않았고, 이후 "recommend best practice and apply"로 남은 흐름을 진행했다. planner/researcher가 다음 제약 위에서 설계한다:
  - 읽기전용 배너("이 페이지는 컴파일됩니다") 강조, WikiLink 내비게이션, 레드 링크 CTA("아직 작성되지 않음 · 지금 생성"), 검증 상태 콜아웃 (UI-05)
  - 렌즈 필터는 `wiki_pages.category` 재사용, PostgREST 1000행 상한을 페이지네이션 또는 서브그래프 제한으로 처리, 그래프 읽기는 `05-CONTEXT.md`의 D-07.1/D-11이 이미 고정한 depth≤2·fan-out cap·cycle guard RPC를 그대로 소비 (UI-06)
- 정확한 컴포넌트 분해, 파일/디렉토리 구조, 상태관리 라이브러리(또는 미사용) 선택은 planner 재량.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract and requirements
- `.planning/ROADMAP.md` §Phase 6 (242-256행) — goal, 6 requirements, 5 success criteria.
- `.planning/REQUIREMENTS.md` §Frontend (UI-01…06, 239-246행) — requirement text.
- `.planning/PROJECT.md` §Key Decisions — "v1 위키 페이지는 읽기 전용, UI가 명시" row (자유 편집이 `(workspace_id, slug)` 업서트와 충돌하는 이유).

### Design system (already exists — reuse, do not reinvent)
- `docs/design-systems/design-tokens.css` — Airbnb 스타일 컬러/타이포/radius/spacing CSS 커스텀 프로퍼티. 시각 언어는 이미 결정되어 있다.
- `docs/design-systems/design-tokens.json` — 동일 토큰의 machine-readable 버전 (`$schema: design-tokens.github.io`).
- `apps/dashboard/app/globals.css:7` — "디자인 토큰(`docs/design-systems/design-tokens.css`)의 `@theme` 편입은 Phase 6 UI 작업 범위" — 이미 명시적으로 마킹된 진입점.

### Prior-phase decisions this phase inherits (do not re-litigate)
- `.planning/phases/01-bootstrap-and-ground-truth/01-CONTEXT.md` > **D-09/D-10** — `apps/dashboard`는 uv 워크스페이스 멤버가 아니고 pnpm 단독 `package.json`. Next.js 15.5.22+ · Tailwind 4 · TS strict · Vitest+Testing Library.
- `.planning/phases/02-security-spine-and-shared-domain/02-CONTEXT.md` > **D-11~D-13** — 0 rows affected → 403, no 404(enumeration 방지), 단일 예외 핸들러(`api/errors.py`). Ask/read API 클라이언트 에러 처리가 이 계약을 소비한다.
- `.planning/phases/05-citation-integrity-and-answer-apis/05-CONTEXT.md` > **D-01~D-11 전체** — SSE 이벤트 순서(`meta`→`delta*`→`citations`→`done`, POST+fetch+ReadableStream 필수, `EventSource` 불가), 인용 앵커 별칭 스킴(`[[wiki:w1]]`/`[[src:s1]]`, request-scoped, 실제 UUID 노출 안 함), `double_citation` = 파싱된 앵커 ∩ 발급된 앵커, 그래프 읽기 RPC 경계(D-07.1/D-11: depth≤2·fan-out cap·cycle guard, RTV-07과 동일 상수). Phase 6은 이 계약을 그대로 소비하고 재설계하지 않는다.

### Existing schema/API (reuse, do not reimplement)
- `apps/api/src/api/routers/` — Ask SSE 엔드포인트 · 읽기 API(위키/소스/그래프/잡 상태) — Phase 5에서 구현·검증 완료.
- `supabase/migrations/0001_core_schema.sql` — `workspaces`/`workspace_members` (role: `owner(3) > editor(2) > viewer(1)`), 소유자 자동 등록 트리거.
- `supabase/migrations/0007_search_and_queue_extensions.sql:239-260` — `verified_by`/`verified_at`/`expires_at` — UI-05 상태 콜아웃이 읽는 필드.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/dashboard/lib/workspace-path.ts` — `workspacePath(workspaceId)` 헬퍼, `/w/[workspaceId]` 경로 규약을 이미 인코딩. D-03의 워크스페이스 전환이 이걸 재사용한다.
- `apps/dashboard/components/HealthBadge.tsx` — 기존 컴포넌트 작성 패턴(스타일링 방식, export 관례) 참고용.
- `docs/design-systems/design-tokens.css` / `.json` — 컬러/타이포/radius/spacing 토큰 그대로 재사용, 재발명 금지.

### Established Patterns
- Next.js 15 App Router, Tailwind 4, TS strict, Vitest + Testing Library (`01-CONTEXT.md`).
- 한국어 주석/커밋 메시지, 영어 식별자 — 프로젝트 전역 관례, Phase 6 코드도 동일하게 맞춘다.
- Worker가 provider secret을 소유하고 API가 내부 리스너를 프록시하는 경계(Phase 4/5) — 대시보드는 이 경계에 개입하지 않고 `apps/api`만 호출한다.

### Integration Points
- `apps/dashboard/app/layout.tsx` — 루트 레이아웃. 인증 프로바이더/전역 네비게이션(워크스페이스 드롭다운)이 여기 연결된다.
- `apps/dashboard/middleware.ts` (아직 없음 — Phase 6에서 신설) — D-02에 따라 유일한 쿠키 기록자이자 테넌시 게이트.
- `apps/dashboard/app/globals.css` — 디자인 토큰 `@theme` 편입 지점, 이미 주석으로 마킹됨.

</code_context>

<specifics>
## Specific Ideas

사용자가 세 영역(인증/워크스페이스 전환, 드롭존/잡 진행, Ask UI 인용)에 대해서는 각 질문마다 권장(recommended) 옵션을 직접 확인했다. 나머지(드롭존 세부·Ask UI 카드 레이아웃 일부)는 "recommend best practice for each, and apply this" 지시에 따라 베스트 프랙티스를 Claude가 선택해 적용했다 — 위 decisions의 D-05~D-11이 그 결과다. 위키 뷰어·캔버스는 논의되지 않았으므로 Claude's Discretion으로 남긴다.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (위키 뷰어/캔버스 세부 UX는 다른 페이즈로 미룬 것이 아니라 여전히 Phase 6 범위이며, 단지 이번 세션에서 대화형으로 논의되지 않아 planner/researcher 재량으로 남았다 — 위 Claude's Discretion 참조.)

</deferred>

---

*Phase: 6-Dashboard*
*Context gathered: 2026-08-12*
