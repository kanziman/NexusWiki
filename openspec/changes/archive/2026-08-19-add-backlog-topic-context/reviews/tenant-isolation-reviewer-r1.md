# Tenant Isolation 리뷰 — add-backlog-topic-context r1

- 판정: pass
- 대상: `git diff main...HEAD` (`c256c64899949cf2fc5020089cb7486535944f25`), 관련 커밋 `b1e1473`·`6f66a3f`·`b83b579`·`c256c64`
- 일시: 2026-08-19T13:43:01Z

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `apps/dashboard/app/w/[workspaceId]/backlog/page.tsx:64`에서 여전히 `@/lib/supabase/server`의 `createClient()`(요청자 쿠키 세션 클라이언트)만 사용. `service_client`/`service_role` 문자열은 diff 어디에도 없음(`git diff main...HEAD -- apps/dashboard/lib/wiki-links.ts apps/dashboard/components/BacklogList.tsx | grep service_role` 결과 없음) |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 이 change는 새 테이블을 만들지 않음(`git diff main...HEAD -- supabase/migrations/` 무변경) |
| A-3 | anon 신규 GRANT/정책 | 해당 없음 | `supabase/migrations/` 변경 없음. `anon` 관련 코드 변경 없음 |
| A-4 | 워커의 workspace_id 명시 필터 | 해당 없음 | 이 change는 워커/`service_role` 코드를 건드리지 않음 |
| A-5 | 신규 자식 테이블의 복합 FK | 해당 없음 | 신규 테이블 없음. 기존 `wiki_links.from_wiki_id`는 이미 `foreign key (from_wiki_id, workspace_id) references wiki_pages (id, workspace_id)`(`supabase/migrations/0002_search_schema.sql:242-243`)로 걸려 있어, `from_wiki_id`가 다른 워크스페이스의 `wiki_pages.id`를 가리키는 것 자체가 DB 레벨에서 불가능함 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 이 라우트는 UPDATE/DELETE가 없는 순수 SELECT 경로(`page.tsx`), `wiki_links`에 대한 쓰기 정책도 없음(`0004_rls_policies.sql:274-276` SELECT 전용) |
| B-7 | 42501 → 403 매핑 | 해당 없음 | 위와 동일. INSERT/UPDATE 경로 자체가 없어 `WITH CHECK` 위반이 발생할 수 없음 |
| C-8 | 멱등 upsert 키 | 해당 없음 | 신규 쓰기 핸들러 없음. `resolveDisplayTitle`/`firstWikiLinkExcerpt`는 조회 시점에 계산되는 순수 함수이고 저장하지 않음(design.md Non-Goals "발췌 저장·캐싱") |
| C-9 | jobs 직접 UPDATE 금지 | 해당 없음 | `jobs` 테이블 미접근 |
| D-10 | strict_order 벡터 검색 | 해당 없음 | 벡터 검색 경로 아님 |
| D-11 | tsv_tokenizer_version 일치 | 해당 없음 | 전문검색 경로 아님 |
| D-12 | search_tsv 생성 컬럼 시도 | 해당 없음 | 관련 스키마 변경 없음 |
| D-13 | 프롬프트 템플릿 str.format | 해당 없음 | LLM 프롬프트 경로 아님 |
| D-14 | 인용 앵커 포함 | 해당 없음 | LLM 컨텍스트 조립 경로 아님 — 이 화면의 "인용 문맥"은 백로그 발췌이지 Ask 답변용 `raw_source_id`/`wiki_id` 앵커가 아님. 발췌는 `page.slug` + `page.id`를 그대로 들고 있어 어느 위키 문서에서 나왔는지는 클라이언트에서 추적 가능(`BacklogList.tsx:11-18`) |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 새 마이그레이션 없음. 현재 최대 번호는 `0016_public_sharing.sql` |

## 격리 경계 상세 확인 (요청 항목 1~4)

**1) `wiki_pages.content` 조회의 workspace_id 격리**
`backlog/page.tsx:96-102`의 본문 조회는 `.eq("workspace_id", workspaceId).in("id", referringPageIds)`로 앱 레벨 필터가 걸려 있고, 이 클라이언트는 요청자 세션(`authenticated` 역할)이므로 `wiki_pages_select_member` RLS(`0004_rls_policies.sql:232-234`, `using (is_workspace_member(workspace_id))`)가 추가로 강제된다. 앱 필터와 RLS 두 겹이 모두 걸려 있어 다른 워크스페이스 본문이 섞여 들어올 경로가 없다.

**2) `referringPageIds`(미해결 링크의 `from_wiki_id`)의 워크스페이스 소속**
`referringPageIds`는 `links`(1단계 `wiki_links` 조회, `.eq("workspace_id", workspaceId)`로 이미 범위 제한됨)에서 `from_wiki_id`만 뽑은 집합이다(`page.tsx:81-89`). `wiki_links.from_wiki_id`는 복합 FK `foreign key (from_wiki_id, workspace_id) references wiki_pages (id, workspace_id)`(`0002_search_schema.sql:242-243`)로 걸려 있으므로, 이 FK 제약이 유효한 한 어떤 `wiki_links` 행도 자신의 `workspace_id`와 다른 워크스페이스의 `wiki_pages.id`를 `from_wiki_id`로 가질 수 없다. 즉 `referringPageIds`는 구조적으로 이 workspace 소속 id만 담을 수 있다. 설령 이 전제가 깨지더라도 3번 쿼리의 `.eq("workspace_id", workspaceId)` + RLS가 이중으로 막는다.

**3) 라우트의 읽기 전용성**
`page.tsx`에는 `wiki_links`·`wiki_pages`에 대한 `insert`/`update`/`upsert`/`delete` 호출이 없다(SELECT 3건뿐). `BacklogList.tsx`에도 Supabase 클라이언트 호출 자체가 없다(`"use client"` 컴포넌트이며 `@/lib/supabase/*` import 없음, props만 소비). `wiki_links`는 애초에 `authenticated`에게 SELECT 정책만 있고(`0004_rls_policies.sql:274-276`) INSERT/UPDATE/DELETE 정책이 없어, 설령 클라이언트 코드가 시도해도 42501로 막힌다. 이 change의 커밋 3건(`b1e1473`/`6f66a3f`/`b83b579`) 전부 diff에 `insert(`/`update(`/`upsert(`/`delete(` 패턴이 없다.

**4) 클라이언트로 내려가는 props의 워크스페이스 경계**
`display_title`은 `contentByPageId`(위 1·2에서 이미 이 workspace로 범위가 좁혀진 본문)에서만 파생되고, `excerpt`도 동일 소스에서 파생된다(`page.tsx:151-183`). `referencing_pages`는 `pagesMap`(`.eq("workspace_id", workspaceId)`로 조회한 `wiki_pages`)에서 나온 `{id, slug, title}`만 담는다(`page.tsx:74-79`, `ReferencingPage` 타입). 클라이언트 컴포넌트가 만드는 링크(`wiki/${page.slug}`, `sources?prefillTitle=...`)도 모두 같은 `workspaceId` 세그먼트 하위 경로다(`BacklogList.tsx:189, 224, 291`). 다른 워크스페이스의 slug·title이 섞일 경로가 없다.

design.md에 명시된 대로 `wiki_pages.content` 원문 전체는 서버에서 소비되고 끝난다 — `BacklogItem`/`BacklogReferencingPage` 타입에 `content` 필드가 없고(`BacklogList.tsx:11-27`), props로 실제 넘어가는 것은 `display_title`·`excerpt`(계산된 문자열)뿐이다.

## 조치가 필요한 항목

없음.

## 판정 근거

이 change는 새 마이그레이션·새 API 엔드포인트·새 쓰기 경로를 추가하지 않고, 기존 `backlog/page.tsx`가 요청자 세션 클라이언트로 수행하는 SELECT 하나에 컬럼(`content`)을 추가하고 조회 범위를 `.in()`으로 제한한 것이 전부다. 격리는 (a) 앱 레벨 `eq(workspace_id)` 필터, (b) `wiki_pages_select_member` RLS, (c) `wiki_links.from_wiki_id`의 복합 FK라는 세 겹으로 여전히 유지된다. 서버가 계산한 `display_title`/`excerpt` 외에 원문 `content`나 다른 워크스페이스 데이터가 클라이언트로 나갈 경로가 없고, `wiki_links`에 대한 쓰기 경로도 추가되지 않았다. 나머지 검사 항목(B~E)은 이 change의 범위(읽기 전용 UI 조회 확장)와 무관해 전부 해당 없음으로 기록한다. 위반 사항이 없어 `pass`로 판정한다.
