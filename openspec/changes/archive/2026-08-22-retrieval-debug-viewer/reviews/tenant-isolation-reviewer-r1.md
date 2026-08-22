# Tenant Isolation 리뷰 — retrieval-debug-viewer r1

- 판정: pass
- 대상: `git diff main...HEAD` (321d000035c4f434e54987a98e6217bbb8479c96)
- 일시: 2026-08-22T00:00:00+09:00

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `apiFetch`(`apps/dashboard/lib/api-client.ts:53-61`)는 `createClient().auth.getSession()`으로 매 호출마다 요청자 세션 토큰을 새로 읽어 `Authorization: Bearer <access_token>`으로만 보낸다. `RetrievalDebugViewer.tsx:226`의 `loadContent`도 동일 파일의 브라우저 `createClient()`(`apps/dashboard/lib/supabase/client.ts:19-24`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` + 쿠키 세션 기반)만 쓴다. diff 전체에서 `service_role`/service client 문자열이 전혀 없다. 백엔드 `POST /workspaces/{id}/retrieval`(`apps/api/src/api/routers/retrieval.py:44-51,76`)도 이번 diff 대상이 아니며 기존부터 `_user_db`로 요청자 JWT만 쓴다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 이번 diff는 `supabase/migrations/`를 전혀 건드리지 않는다(`git diff --stat` 확인) |
| A-3 | anon 신규 GRANT/정책 | 해당 없음 | 마이그레이션 변경 없음. `0004_rls_policies.sql`은 모든 정책을 `to authenticated`로 한정하고 `anon`에는 정책이 없다(전면 거부) — 이 상태를 건드리지 않았다 |
| A-4 | service_role 워커의 workspace_id 명시 필터 | 해당 없음 | 워커/service_role 코드 변경 없음. 순수 프론트엔드(`apps/dashboard`)만 변경됨 |
| A-5 | 신규 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 이번 diff에 UPDATE/DELETE 경로가 없다. `loadContent`(`RetrievalDebugViewer.tsx:210-247`)는 SELECT(`.single()`)만 하며, RLS로 0행이 걸리면 Supabase가 `PGRST116` 오류를 돌려주고 코드는 이를 "조회 실패" UI로 표시한다(`:232-236`) — 데이터 노출도, "성공"으로 보이는 것도 아니다 |
| B-7 | 42501 → 403 매핑 | 해당 없음 | WITH CHECK가 걸리는 쓰기 경로 없음 (전부 읽기 전용) |
| C-8 | 멱등 upsert 키 | 해당 없음 | 잡 핸들러·쓰기 경로 없음 |
| C-9 | jobs 직접 UPDATE 금지 | 해당 없음 | `jobs` 테이블 접근 없음 |
| D-10 | hnsw iterative_scan strict_order | 해당 없음 | 벡터 검색 백엔드(`apps/api`)는 이번 diff에서 변경되지 않음 |
| D-11 | tsv_tokenizer_version 일치 | 해당 없음 | 어휘 검색 백엔드 변경 없음 |
| D-12 | search_tsv 생성 컬럼화 시도 | 해당 없음 | 스키마 변경 없음 |
| D-13 | 프롬프트 템플릿 str.format | 해당 없음 | 프롬프트 템플릿 관련 코드 없음 |
| D-14 | LLM 컨텍스트 인용 앵커 | 해당 없음 | 이 화면은 LLM 컨텍스트를 조립하지 않는다 — evidence를 그대로 노출하는 관찰 전용 디버그 뷰다 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음 |

## 상세 확인 — `resolveContentTarget` + `createClient()` 직접 조회

지시받은 대로 신규로 추가된 `RetrievalDebugViewer.tsx:111-125`(`resolveContentTarget`)와 `:210-247`(`loadContent`)를 `CitationSidePanel.tsx:78-95`와 대조했다.

- **패턴 동일성**: 두 컴포넌트 모두 브라우저 `createClient()`(user-JWT, `@supabase/ssr`의 `createBrowserClient`)로 `wiki_pages` / `source_chunks` / (`RetrievalDebugViewer`만 추가로) `wiki_embeddings`를 `.eq("id", <evidence.id>).single()`로만 조회한다. `workspace_id` 조건을 앱 코드에 걸지 않는 것도 동일하다.
- **RLS로 실제로 막히는지 확인**: `supabase/migrations/0004_rls_policies.sql:232-234`(`wiki_pages_select_member`), `:266-268`(`source_chunks_select_member`), `:270-272`(`wiki_embeddings_select_member`) 세 정책 모두 `using (public.is_workspace_member(workspace_id))` — 정책이 요청자의 멤버십을 행 자신의 `workspace_id` 컬럼으로 판정하므로, `.eq("id", ...)` 하나만 걸어도 다른 워크스페이스의 행은 RLS가 조용히 0행으로 걸러낸다(`is_workspace_member`는 `auth.uid()`를 SECURITY DEFINER로 고정해서 보므로 클라이언트가 위조할 수 없다). `.eq("id", ...)` 외에 `workspace_id` 필터가 없어도 격리가 뚫리지 않는다는 뜻이며, `CitationSidePanel.tsx`가 이미 같은 근거로 안전하다고 판단된 패턴을 그대로 재사용한 것이다.
- **evidence.id의 출처**: `POST /workspaces/{id}/retrieval`(`apps/api/src/api/routers/retrieval.py:54-77`, 이번 diff 대상 아님)는 `_user_db`(요청자 JWT)로 RPC를 호출하고, `apps/api/src/api/services/retrieval.py`의 각 RPC 호출이 `p_workspace_id`를 명시적으로 넘긴다(`:187-267`). 즉 `evidence.id`는 애초에 호출자 자신의 워크스페이스 안에서만 나온 id이고, 프론트의 `.eq("id", ...)` 조회는 여기에 RLS라는 두 번째 방어선을 더할 뿐이다.
- **테이블 매핑 정확성**: `resolveContentTarget`의 kind→table 매핑(`wiki_vector`→`wiki_embeddings.chunk_content`, `wiki_lexical`→`wiki_pages.content`, `source`→`source_chunks.content`)은 코드 주석(`:107-110`)이 인용한 `apps/api/src/api/services/retrieval.py`의 `_wiki_vector_hit`/`_wiki_lexical_hit`/`_source_hit`와 대조했을 때 일치한다. 매핑이 어긋나는 경우가 있어도(예: UUID 우연 충돌 없음이 사실상 보장되므로) 잘못된 테이블에서 같은 id의 행을 찾지 못해 `not_found`로 표시될 뿐이며, 어느 경우든 조회는 여전히 같은 워크스페이스 소속 테이블의 RLS 정책 하에서만 실행된다 — 테넌트 경계를 넘는 경로는 없다.

## 상세 확인 — 프로덕션 게이트 (`layout.tsx`)

- `apps/dashboard/app/w/[workspaceId]/debug/retrieval/layout.tsx:16-18`는 `process.env.NODE_ENV !== "development"`일 때 `notFound()`를 던진다. App Router에서 레이아웃의 `notFound()`는 자식(`page.tsx`, 즉 `RetrievalDebugViewer`)의 렌더링 자체를 막으므로, 프로덕션(`next start` → `NODE_ENV=production`)에서는 클라이언트 컴포넌트가 마운트되지 않아 `apiFetch`도 `loadContent`도 실행되지 않는다.
- 이 게이트는 `apps/dashboard/app/preview/layout.tsx:12-14`와 동일한, 이미 검증된 패턴이다(`local-product-preview` change 근거, `design.md:10` 인용).
- 미들웨어 우회(CVE-2025-29927, `x-middleware-subrequest` 헤더 위조로 미들웨어 스킵) 영향 여부: 이 게이트는 미들웨어가 아니라 서버 컴포넌트 레이아웃의 런타임 분기이므로 해당 CVE의 공격 표면과 무관하다. 또한 `package.json`상 Next.js `15.5.22`로 CLAUDE.md가 요구하는 `>= 15.2.3`을 만족한다(`middleware.ts:16` 주석도 동일 버전을 명시).
- `/w/[workspaceId]` 상위 레이아웃(`apps/dashboard/app/w/[workspaceId]/layout.tsx:29-37`)이 `workspaces` 테이블을 RLS로 조회해 멤버가 아니면 `/`로 리다이렉트하므로, 개발 환경에서도 `/debug/retrieval` 접근은 실제 워크스페이스 멤버로 한정된다.
- (참고, 이번 diff의 범위는 아님) `POST /workspaces/{id}/retrieval` 백엔드 엔드포인트 자체는 환경 게이트가 없어 프로덕션에서도 인증된 워크스페이스 멤버가 API를 직접 호출하면 동일 데이터를 얻을 수 있다. 이는 `design.md:61`의 Risks/Trade-offs에서 "기존에 API로 가능하던 걸 화면으로 옮기는 것뿐"이라고 명시적으로 인지·수용된 사항이며, 백엔드가 이번 diff에서 변경되지 않았으므로 새로운 노출이 아니다.

## 조치가 필요한 항목

없음.

## 판정 근거

diff는 순수 프론트엔드이며 새 쓰기 경로·새 테이블·새 GRANT·워커 코드가 전혀 없다. 유일하게 새로 생긴 위험 표면인 `resolveContentTarget` + `createClient()` 직접 조회는 `CitationSidePanel.tsx`가 이미 쓰고 있는 user-JWT + RLS 패턴을 정확히 재사용하며, `0004_rls_policies.sql`의 `wiki_pages_select_member`/`source_chunks_select_member`/`wiki_embeddings_select_member` 세 정책 모두 행 자신의 `workspace_id` 컬럼을 `is_workspace_member`로 검증하므로 `.eq("id", ...)` 단독 조회로도 테넌트 경계가 유지된다. 프로덕션 게이트(`layout.tsx`)는 검증된 기존 패턴을 그대로 따르고, App Router의 `notFound()` 의미론상 자식 렌더링 자체를 막아 API 호출 경로가 실행되지 않는다. A-1/A-3/A-4 등 `blocked` 기준에 해당하는 위반이 없어 `pass`로 판정한다.
