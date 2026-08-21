# Tenant Isolation 리뷰 — dashboard-layout-density r1

- 판정: needs_fix
- 대상: `feat/dashboard-layout-density` 워킹 트리 diff (base `747d7de`)
- 일시: 2026-08-20T22:32:55Z

> ⚠️ 검토 시점에 브랜치 HEAD 가 `main`(`747d7de`)과 동일하고 변경분이 전부
> 커밋되지 않은 워킹 트리 상태였다(`git diff main...HEAD` 는 빈 출력). 따라서
> 실제 검사 대상은 `git diff HEAD` + untracked 3건
> (`apps/dashboard/lib/verification-label.ts`,
> `apps/dashboard/tests/verification-label.test.tsx`,
> `openspec/changes/dashboard-layout-density/`)이다.

## 범위 확인 — "표현 계층 전용"이라는 주장의 검증

주장은 **맞다**. 변경된 12개 파일 + 신규 2개 파일 어디에도 다음이 없다.

- `supabase/` 하위 변경 0건 (`git diff HEAD --name-only | grep '^supabase/'` → 없음).
  마이그레이션 최대 번호는 여전히 `0017_wiki_bookmarks.sql`이고 신규 파일이 없다.
- `apps/api/`, `apps/worker/` 변경 0건.
- `apps/dashboard/lib/supabase/` (`server.ts` · `public.ts`) 변경 0건 — 클라이언트
  생성 경로 자체가 손대지지 않았다.
- 쿼리 문자열(`.select(...)` · `.eq("workspace_id", ...)`) 변경 0건. diff 전체에서
  Supabase 호출이 추가·삭제·수정된 곳이 없다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 해당 없음 | 대시보드 전체에 `service_client`/service key 사용처가 없다. `app/w/[workspaceId]/page.tsx:34`·`wiki/page.tsx:28` 은 `createClient()`(요청자 세션), `app/p/[slug]/[page]/page.tsx:38` 은 `createPublicClient()`(anon). 셋 다 이번 diff에서 변경되지 않았다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블·마이그레이션 없음 |
| A-3 | anon 신규 GRANT/정책 | 해당 없음 | SQL 변경 0건. `/p/` 경로가 읽는 테이블은 여전히 사이드카 2개(`workspace_public_settings`·`wiki_page_publications`)뿐이며 조인 추가 없음 |
| A-4 | service_role 코드의 workspace_id 필터 | 해당 없음 | 워커 코드 변경 없음 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 스키마 변경 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 이번 diff에 쓰기 경로(UPDATE/DELETE) 추가·변경 없음 |
| B-7 | SQLSTATE 42501 → 403 | 해당 없음 | 동일 |
| C-8 | 핸들러 멱등성 | 해당 없음 | 신규 잡 핸들러 없음 |
| C-9 | `jobs` 직접 UPDATE | 해당 없음 | `jobs` 접근 코드 변경 없음 |
| D-10 | `hnsw.iterative_scan` | 해당 없음 | 벡터 검색 경로 변경 없음 |
| D-11 | 토크나이저 버전 일치 | 해당 없음 | 검색·색인 경로 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 시도 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 `str.format` | 해당 없음 | 프롬프트 템플릿 변경 없음 |
| D-14 | 인용 앵커 | 통과 | `AskConversation.tsx` 변경분은 헤더 eyebrow 제거 1건(:286~290)뿐이며 인용 조립 코드는 그대로. 공개 페이지의 인용은 여전히 `published_citations` 스냅샷(`page.tsx:71~73`)에서만 온다 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음 |
| 요청 1 | 공개 페이지 노출 표면 | 통과 | `app/p/[slug]/[page]/page.tsx` 변경은 `:99` className 1줄 + 주석뿐. 쿼리·필터·렌더 데이터 범위 동일 |
| 요청 2 | 라벨 파생 모듈 | 부분 위반 | 원시 enum 누출은 없다(`verification-label.ts:49` 기본값 "검증 필요"). 그러나 `disputed` 우선순위가 홈 대시보드에서 **한 번도 동작하지 않는다** — 아래 1번 |
| 요청 3 | KnowledgeGrid · WikiLibrary 상태 회귀 | 부분 위반 | `WikiLibrary` 는 회귀 없음(구 `stateLabel` 과 분기 완전 동일). `KnowledgeGrid` 는 disputed 문서를 계속 "검증됨"으로 표시한다 — 아래 1번. 부수로 같은 화면 안에서 같은 값이 두 이름으로 불린다 — 아래 2번 |
| 요청 4 | 데이터 조회 경로 | 통과 | `service_client` 사용 0건, `workspace_id` 필터 전부 유지, 쿼리 diff 0줄 |

### 요청 1 상세 — 공개 페이지(`anon`)

`apps/dashboard/app/p/[slug]/[page]/page.tsx` 의 실질 변경은 `:99` 한 줄
(`className="eyebrow"` → `className="breadcrumb-path"`)과 그 위 주석뿐이다.
불변식 §4~§5 관점에서 확인한 것:

- 클라이언트는 여전히 `createPublicClient()`(`:38`) — `authenticated` 로 승격되지
  않았다. 킬스위치가 멤버에게만 무력화되는 경로가 새로 생기지 않았다.
- 읽는 테이블은 사이드카 2개뿐(`:45`, `:57`). `workspaces`·`wiki_pages`·
  `source_chunks` 조인이 추가되지 않았다.
- `:61` 의 `.eq("workspace_id", settingsData.workspace_id)` 그대로 유지.
- 렌더되는 필드 집합 동일: 발행 스냅샷(`published_title`·`published_content`·
  `published_citations`)과 공개 설정(`public_display_name`·`public_description`)뿐.
  `stripWikiLinks`(`:187`)와 내부 라우트 미링크 규칙도 손대지 않았다.
- 시각적 차이 1건: `.eyebrow` 는 `text-transform: uppercase`
  (`nexuswiki-design-system.css:490`)라 `public_display_name` 이 대문자로 그려졌고
  이제 입력 그대로 그려진다. DOM 텍스트는 이전에도 원본이었으므로 **새로 노출되는
  데이터는 없다**. 순수 표시 변경이다.
- `.breadcrumb-path` 는 `nexuswiki-design-system.css:494` 에 정의됐고 해당 파일은
  `apps/dashboard/app/globals.css:3` 이 import 하므로 공개 라우트에도 적용된다 —
  클래스만 바뀌고 스타일이 사라지는 상태는 아니다.

결론: 공개 페이지의 노출 표면은 바뀌지 않았다.

## 조치가 필요한 항목

1. **홈 대시보드에서 `disputed` 문서가 계속 "검증됨"으로 표시된다 — 신뢰 상태의 조용한 오표시** (심각도: 높음)
   - 위치: `apps/dashboard/components/KnowledgeGrid.tsx:83`, `:98`, `:102` /
     `apps/dashboard/components/KnowledgeGrid.tsx:9~17`(타입) /
     `apps/dashboard/app/w/[workspaceId]/page.tsx:46`, `:58~66`(쿼리·매핑) /
     `apps/dashboard/lib/verification-label.ts:46`, `:57`
   - 깨지는 것: 새 모듈은 "`disputed` 가 참이면 검증 단계보다 우선해서 표시한다"
     (`verification-label.ts:31~34`)를 계약으로 못박았지만, 홈 대시보드에서는 이
     분기가 **구조적으로 도달 불가능**하다. 두 겹으로 막혀 있다.
     - (a) `app/w/[workspaceId]/page.tsx:46` 의 select 컬럼 목록에 `disputed` 가
       없고, `:58~66` 매핑도 이 필드를 만들지 않는다. `WikiPageSummary`
       (`KnowledgeGrid.tsx:9~17`)에도 `disputed` 가 없다. 따라서
       `isVerified(page)` 에 들어오는 `page.disputed` 는 **항상 `undefined`** 다.
       `VerificationLabelInput` 의 필드가 전부 optional 이라 구조적 타이핑이
       이 누락을 컴파일 에러 없이 통과시킨다 — 조용한 부분이 정확히 여기다.
       결과: `verification_status='verified' AND disputed=true` 인 문서가 홈에서
       `<b class="badge verified">검증됨</b>` 으로 그려진다. 같은 문서를 위키
       라이브러리에서 열면 "충돌 감지"다. 스펙이 요구한 "one state is never named
       differently on two destinations" 가 바로 이 값에서 깨진다.
     - (b) 설령 `disputed` 를 쿼리에 넣어도 고쳐지지 않는다. `KnowledgeGrid.tsx:98`
       이 라벨 출력을 `verified &&` 로 감싸고 있고 `isVerified`
       (`verification-label.ts:57`)는 `!page.disputed && ...` 이므로,
       disputed 문서는 "충돌 감지"로 바뀌는 게 아니라 **상태 텍스트가 통째로
       사라진다**. 즉 현재 배선에서 `disputed` 우선순위는 "잘못된 안심"(a) 또는
       "정보 은폐"(b) 중 하나로만 귀결되고, 의도한 "충돌을 먼저 알린다"는 어느
       쪽으로도 나오지 않는다.
   - 테스트가 이를 잡지 못한다: `tests/verification-label.test.tsx:62~70` 은
     `disputed` 를 **순수 함수 수준에서만** 검증한다. 같은 파일 `:19~21` 주석이
     "단위 함수만 검증하면 이 계약이 지켜지지 않는다 … 실제로 갈라졌던 방식은
     컴포넌트가 함수를 안 쓰고 자기 문자열을 들고 있던 것"이라고 스스로 적어
     놓고, disputed 케이스만 그 원칙에서 빠졌다. 4개 파일 11건 전부 green이다
     (`npx vitest run` 확인).
   - 조치: 셋 다 필요하다.
     1. `app/w/[workspaceId]/page.tsx:46` select 에 `disputed` 추가, `:58~66`
        매핑에 `disputed: p.disputed` 추가.
     2. `KnowledgeGrid.tsx:9~17` `WikiPageSummary` 에 `disputed?: boolean | null`
        추가.
     3. `KnowledgeGrid.tsx:98~105` 의 게이트를 재검토한다. disputed 를 배지로
        노출할 거면 `verified &&` 대신 "상태 텍스트는 항상 그리되 톤 클래스만
        분기"로 바꾸고, 홈에서는 검증 배지만 띄운다는 결정이면 그 결정을
        `verification-label.ts` 주석에 명시해 "우선순위가 여기서는 적용되지
        않는다"를 문서화한다. 지금처럼 계약만 선언하고 배선이 없는 상태가 가장
        나쁘다.
     4. `tests/verification-label.test.tsx` 에 **렌더 기반** disputed 케이스를
        추가한다 — `KnowledgeGrid` 에 `disputed: true, verification_status:
        "verified"` 를 넘겼을 때 "검증됨"이 나오지 않는지.

2. **위키 라이브러리 한 화면 안에서 같은 `verified` 가 두 이름으로 불린다** (심각도: 보통)
   - 위치: `apps/dashboard/components/WikiLibrary.tsx:103~106` vs `:160`
   - 깨지는 것: 요약 통계는 `verification_status === "verified"` 를 세어 "검증 완료"
     라 부르고, 바로 아래 목록은 같은 값을 `stateLabel` 을 통해 "검증됨"이라
     부른다. 이번 change 가 없애려던 "검증 완료 vs 검증됨" 이중 어휘가 목적지 간
     에서 사라지고 **한 화면 안으로 옮겨왔을 뿐**이다. 더구나 통계는
     `disputed` 를 무시하므로 "충돌 감지"로 표시된 행이 "검증 완료" 카운트에
     포함된다 — 같은 화면에서 숫자와 행이 서로 모순된다.
   - 조치: 통계 라벨을 목록과 같은 어휘로 맞추고(예: "검증됨"), 카운트 술어를
     `isVerified` 로 교체해 disputed 행이 검증 카운트에서 빠지게 한다.

3. **`.eyebrow` 관련 ⚠️ 주석 2곳이 코드와 어긋난다** (심각도: 보통 — spec-conformance 리뷰어와 중복 영역)
   - 위치: `docs/design-systems/v2/nexuswiki-design-system.css:479~480` /
     `apps/dashboard/components/WikiPageContent.tsx:134~137` /
     실제 잔존 사용처 `apps/dashboard/app/w/[workspaceId]/page.tsx:97`
   - 깨지는 것: CSS 주석은 "지금 앱 화면에서는 쓰지 않는다 — 프로토타입
     프리뷰(PreviewWorkspace)와 프로토타입 HTML 만 남는다"고 적었고
     `WikiPageContent.tsx:135` 는 "다른 다섯 화면의 eyebrow 는 제거됐다"고 적었다.
     둘 다 사실이 아니다. (a) 워크스페이스 홈 `page.tsx:97` 이
     `<p className="eyebrow">워크스페이스</p>` 로 여전히 쓰고 있고, (b)
     `PreviewWorkspace` 는 이번 diff 로 `.eyebrow` 사용처가 0이 됐다 — 주석이 지목한
     두 대상이 정확히 뒤바뀌어 있다. 게다가 잔존 사용처가 한국어 텍스트라
     `text-transform: uppercase`(한국어에 무효) + `letter-spacing: .11em` +
     모노스페이스가 걸린다. `WikiPageContent.tsx:136~137` 이 "한국어에 맞지 않는다"고
     스스로 적은 그 조합이다. `⚠️` 주석은 이 저장소에서 판단 근거로 쓰이므로,
     틀린 채로 남으면 다음 편집자가 이미 해결된 문제로 오인한다.
   - 조치: `app/w/[workspaceId]/page.tsx:97` 의 eyebrow 를 제거하거나
     `.breadcrumb-path` 로 바꾸고(스펙의 "contextual supporting labels SHALL appear
     only where they carry information the page title does not already convey" 판정
     — "워크스페이스"는 바로 아래 `h1` 의 워크스페이스 이름이 이미 말한다),
     두 주석의 잔존 사용처 서술을 실제와 맞춘다.

## 판정 근거

테넌트 경계는 뚫리지 않았다. `service_role`/service client 는 대시보드 어디에도
없고, `anon` 에 새 GRANT 나 정책이 붙지 않았으며, 공개 라우트(`/p/`)는 여전히
`createPublicClient()` 로 사이드카 2개만 읽고 `workspace_id` 필터도 그대로다.
SQL·API·워커 변경이 0건이라 A·B·C·E 그룹은 대부분 해당 없음이고, 마이그레이션
번호 충돌도 없다. 따라서 `blocked` 가 아니다.

그러나 `pass` 도 아니다. 이번 change 는 검증 상태 어휘를 단일 출처로 모으는 것을
명시적 계약(`spec.md:23`, `spec.md:29~31`)으로 삼았고 그 계약을 지키는 모듈까지
새로 만들었는데, 홈 대시보드에서는 `disputed` 가 쿼리에도 타입에도 없어 그 계약이
한 번도 실행되지 않는다. 옵셔널 필드 + 구조적 타이핑이라 타입 검사도, 통과하는
11건의 테스트도 이를 잡지 못한다 — 예외 없이 통과하면서 프로덕션에서 충돌 문서를
"검증됨"으로 보여주는, 정확히 이 리뷰가 찾도록 되어 있는 종류의 결함이다. 데이터
자체가 손상되지는 않고 코드 수정으로 해결되므로 `needs_fix` 로 판정한다.
