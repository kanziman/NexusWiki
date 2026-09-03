# Tenant Isolation 리뷰 — backlog-redesign r1

- 판정: pass
- 대상: working tree diff (HEAD `1ef411f`, 브랜치 `feat/knowledge-grid-design-polish`, 미커밋 상태). `feat/backlog-redesign` → `feat/sources-redesign` 위에 스택
- 일시: 2026-09-03T10:03:16Z

검사 범위(5개 파일, +786/-214):

- `apps/dashboard/components/BacklogList.tsx` (+381/-168)
- `apps/dashboard/app/w/[workspaceId]/backlog/page.tsx` (+21/-3)
- `apps/dashboard/tests/BacklogList.test.tsx` (+262/-16 상당)
- `apps/dashboard/tests/backlog-page-route.test.tsx` (+51/-4 상당)
- `docs/design-systems/v2/nexuswiki-design-system.css` (+94/-32, 주석만)

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `git diff \| grep -i "service_role\|SERVICE_ROLE\|service_client"` 결과 0건. `backlog/page.tsx:66`는 여전히 `createClient()`(`apps/dashboard/lib/supabase/server.ts`, 요청자 쿠키 기반)만 쓴다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음. 마이그레이션 파일이 diff에 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 해당 없음 | `git diff \| grep -i "anon\|grant\|create policy"` 결과 0건 |
| A-4 | 워커의 명시적 `workspace_id` 필터 | 해당 없음 | 워커 코드 변경 없음 |
| A-5 | 자식 테이블 복합 FK `(id, workspace_id)` | 해당 없음 | 스키마 변경 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 이 화면은 UPDATE/DELETE를 하지 않는 순수 조회 화면이다. 행 액션은 다른 라우트(`/sources`)로의 링크뿐 |
| B-7 | SQLSTATE 42501 → 403 | 해당 없음 | 위와 동일 이유 |
| C-8 | 핸들러 멱등성 / upsert 키 | 해당 없음 | 잡 핸들러 변경 없음. 순수 표시 계층 |
| C-9 | `jobs` 직접 UPDATE 금지 | 해당 없음 | `jobs` 접근 코드 없음 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 벡터 검색 경로 변경 없음. 이 화면의 검색은 클라이언트 `includes()` 필터(`BacklogList.tsx:83-94`)로 DB와 무관 |
| D-11 | 색인/질의 토크나이저 일치 | 해당 없음 | tsvector 경로 없음 |
| D-12 | `search_tsv` 생성 컬럼화 시도 | 해당 없음 | 해당 DDL 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 프롬프트 코드 없음 |
| D-14 | 인용 앵커 보존 | 통과 | `referencing_pages`는 `wiki_id`가 아닌 `page.slug` 라우팅(`BacklogList.tsx:404`)을 유지하고, `BacklogDetailModal`(이 change에서 미변경)이 발췌를 전량 노출한다. 칩 2개 + `+N개 더` 축약(`:362-364`, `:413-417`)으로 화면에서 숨겨지는 인용도 모달을 통해 되짚을 수 있다 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음. 최대 번호는 여전히 `0021_source_deletion_integrity.sql` |
| 추가-1 | `wiki_links`·`wiki_pages` 조회 error 검사 및 `loadFailed` 전달 | 통과 | 아래 「보조 확인 1」 |
| 추가-2 | `loadFailed`일 때 단정 문구를 실제로 피하는지 | 통과 | 아래 「보조 확인 2」 |
| 추가-3 | 신규 벤토 지표의 워크스페이스 밖 데이터 노출 | 통과 | 아래 「보조 확인 3」 |
| 추가-4 | `BacklogDetailModal`·해결 액션 링크·`Pagination` 보존 | 통과 | 아래 「보조 확인 4」 |
| 추가-5 | 3번째 조회(본문 content)의 조용한 실패 | 관찰(회귀 아님) | 아래 「보조 확인 5」 |

### 보조 확인 (호출자 질의에 대한 답)

**1. error 검사와 `loadFailed` 전달.** `backlog/page.tsx:66-100`이 `wiki_links`·`wiki_pages` 두 조회 모두에서 `error`를 구조분해하고, `loadFailed = Boolean(linksError) || Boolean(pagesError)`를 계산해 `console.error`로 기록한 뒤 `BacklogList`에 prop으로 넘긴다(`:196-201`). `backlog-page-route.test.tsx:151-179`가 두 조회 각각의 실패를 개별 픽스처로 재현해 `props.loadFailed === true`를 확인하고, `linksData ?? []`처럼 실패를 빈 배열로 흘려보내지 않는지(`props.initialItems`가 빈 배열이면서도 `loadFailed`가 따로 true인지)까지 검증한다(`:159-163`). 조회 경로 자체(select 컬럼·`.eq("workspace_id", workspaceId)`·`.is("to_wiki_id", null)`)는 `git diff`상 손대지 않았다 — 변경은 `error` 구조분해와 `loadFailed` 계산·전달뿐이다.

**2. `loadFailed`가 참일 때 단정 회피.** `BacklogList.tsx:250-261`은 `loadFailed`가 참이면 `LOAD_FAILED_HEADING`(`"지식 공백을 불러오지 못했습니다"`)·`LOAD_FAILED_BODY`(`"잠시 후 다시 시도해주세요."`)만 렌더하고, `EMPTY_HEADING`/`EMPTY_BODY`(`"모든 위키 링크가 정상적으로 연결되어 있습니다."`) 분기(`:316-328`)는 `loadFailed`가 거짓인 `else` 블록 안에만 존재해 물리적으로 도달 불가능하다. 우선순위 요약 벤토도 `!loadFailed && items.length > 0 && ...` 가드(`:145`)로 실패 시 렌더되지 않는다 — sources-redesign r1이 지적했던 "삼켜진 오류가 단정 문구로 승격"되는 패턴이 구조적으로 막혀 있다. `BacklogList.test.tsx`의 `"조회가 실패하면 빈 상태 문구 대신 불러오지 못했음을 알린다"` 테스트가 `LOAD_FAILED_HEADING`은 보이고 `EMPTY_HEADING`/`EMPTY_BODY`는 부재함을 직접 단언하며, 실행 결과 통과했다(`vitest run tests/BacklogList.test.tsx tests/backlog-page-route.test.tsx` → PASS 31, FAIL 0).

**3. 벤토 지표는 새 데이터를 만들지 않는다.** 네 지표(`items.length`·`distinctReferringPages.size`·`mostCited`·`longestWaiting`)와 필터 카운트(`multiCitedCount`·`singleCitedCount`)는 전부 이미 workspace-scoped인 `initialItems`(`page.tsx`가 `.eq("workspace_id", workspaceId)`로 조회한 결과)의 순수 파생이다(`BacklogList.tsx:73-127`). 새 조회·새 API 호출이 없으므로 워크스페이스 밖 데이터가 섞일 경로 자체가 없다. `distinctReferringPages`는 이미 화면에 보이던 `referencing_pages` 배열의 id 집합일 뿐이라 추가로 추론 가능해지는 사실도 없다.

**4. 재사용 컴포넌트 보존.** `BacklogDetailModal`은 diff에 등장하지 않고(`git diff --stat`에 파일 없음) `BacklogList.tsx:480-484`에서 그대로 `item={openTopic}` prop으로 호출된다. 해결 액션 링크의 `href`는 `` `${workspacePath(workspaceId)}/sources?prefillTitle=${encodeURIComponent(item.display_title)}&tab=text` ``로 HEAD(`git show HEAD:...BacklogList.tsx` 239행대)와 문자 단위로 동일하다(`BacklogList.tsx:451-453`). `Pagination`도 동일한 `currentPage`/`totalItems`/`pageSize={8}`/`onPageChange` 시그니처로 재사용된다(`:468-474`). 행 안에서 주제 버튼(`onClick={() => setOpenTopic(item)}`)·위키 칩 `Link`·소스 추가 `Link`가 각자 독립 엘리먼트이고 행(`role="row"` div) 자체에는 클릭 핸들러가 없어, HEAD의 `<tr>` 구조와 마찬가지로 한 컨트롤 조작이 다른 컨트롤을 발화시키지 않는다.

**5. 3번째 조회(본문 content) — 회귀 아님, 사전 존재하는 범위 밖 gap.** `page.tsx:106-116`의 `wiki_pages`(id, content) 조회는 `error`를 구조분해하지 않는다(`const { data: contentData } = ...`). 이 조회가 실패하면 `contentByPageId`가 비고, `resolveDisplayTitle`이 모든 항목에서 `null`을 반환해 `deslugify(item.target_slug)` 폴백으로 떨어진다(`:169-171`). 다만 이 실패는 **`items`·`impact`·`referencing_pages`·벤토 수치에 영향을 주지 않는다** — 이들은 1·2번 조회에서만 나온다. 즉 "공백 없음"이라는 거짓 단정으로 이어지는 경로가 아니라, 표시 제목이 이미 존재하는 폴백 경로(원문 표기를 못 찾았을 때와 동일한 slug 역변환)로 저하될 뿐이다. `git diff`상 이 조회의 error 미검사는 이 change가 새로 도입한 것이 아니다 — `linksData`/`pagesData` 두 줄만 변경되고 `contentData` 줄은 diff에 없다(변경 없음). `proposal.md`(Impact)와 `tasks.md` 4.1도 명시적으로 "`wiki_links`·`wiki_pages` 조회"로 범위를 한정했고, 3번째 조회의 error 처리는 이 change의 계약(`specs/backlog-ask/spec.md`의 "Backlog aggregate load failure" 요구사항도 `unresolved-link or referencing-page query`로 한정)에 포함되지 않는다. 따라서 이 change의 판정에는 영향을 주지 않지만, 향후 change에서 다룰 여지가 있는 기존 gap으로 기록해 둔다.

**검증 실행.** `apps/dashboard`에서 `pnpm vitest run tests/BacklogList.test.tsx tests/backlog-page-route.test.tsx` → PASS 31, FAIL 0. `pnpm exec tsc --noEmit -p tsconfig.json` → 오류 없음. `pnpm exec eslint components/BacklogList.tsx "app/w/[workspaceId]/backlog/page.tsx" tests/BacklogList.test.tsx tests/backlog-page-route.test.tsx` → 오류 없음.

## 조치가 필요한 항목

없음.

## 판정 근거

테넌트 경계는 이 diff 어디에서도 흔들리지 않는다 — `service_role`·`anon` GRANT·마이그레이션·워커 코드가 diff에 전혀 없고, 유일한 서버 조회 파일(`backlog/page.tsx`)은 조회 경로(select 컬럼·`workspace_id` 필터·`to_wiki_id is null` 조건)를 그대로 두고 `error` 검사만 더했다는 주장이 실측과 일치한다.

이번 change가 특히 겨냥한 `sources-redesign` r1의 결함(조회 오류를 삼켜 워크스페이스 단정 문구로 승격) 패턴은 여기서 재발하지 않았다. `page.tsx`가 두 조회 모두의 `error`를 개별 픽스처로 테스트 가능한 `loadFailed` boolean으로 전달하고, `BacklogList`는 `loadFailed`가 참일 때 `EMPTY_HEADING`/`EMPTY_BODY` 분기 자체에 물리적으로 도달할 수 없는 구조(별도 `if` 가지)로 짰다. 새 벤토 지표는 전부 이미 workspace-scoped된 props의 산술 파생이라 새로운 데이터 노출 경로가 없고, `BacklogDetailModal`·해결 액션 링크의 쿼리 파라미터·`Pagination`은 바이트 단위로 보존됐다. 3번째 조회(본문 content)의 `error` 미검사는 실재하지만 이 change가 새로 만든 회귀가 아니며(diff에 해당 줄 변경 없음), items·impact·벤토 수치의 정확성에 영향을 주지 않고 이 change의 명시적 범위(`tasks.md` 4.1, delta spec) 밖이라 판정에는 반영하지 않았다 — 다만 향후 change를 위해 기록해 둔다.
