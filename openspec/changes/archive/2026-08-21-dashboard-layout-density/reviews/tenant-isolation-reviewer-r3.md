# Tenant Isolation 리뷰 — dashboard-layout-density r3 (최종)

- 판정: pass
- 대상: `feat/dashboard-layout-density` 워킹 트리 diff (base `747d7de`)
- 일시: 2026-08-20T23:09:09Z

> ⚠️ r1·r2와 동일하게 브랜치 HEAD가 `main`(`747d7de`)이고 변경분이 전부 커밋되지
> 않은 상태다(`git diff main...HEAD`는 빈 출력). 실제 검사 대상은
> `git diff HEAD`(15개 파일) + untracked 2건
> (`apps/dashboard/lib/verification-label.ts`,
> `apps/dashboard/tests/verification-label.test.tsx`) + `openspec/changes/` 문서다.
> `git status --short supabase/ apps/api apps/worker` → 0건.

## r2 지적 사항 처리 확인

| r2 항목 | 상태 | 근거 |
| --- | --- | --- |
| 1. 라이브러리 통계가 충돌 문서를 "검증 완료"로 셈 (r1-2 이월) | **닫힘** | `WikiLibrary.tsx:109` 술어가 `pages.filter((p) => isVerified(p)).length`, `:110` 라벨이 "검증됨". 목록(`:165` `stateLabel` = `verificationLabel`)과 같은 모듈·같은 어휘다. 통계 모집단도 `pages`(전체)로 "전체 문서"(`:99`)와 동일하므로 두 숫자가 같은 기준을 쓴다 |
| 2. `expires_at` 누락 | **닫힘** | 아래 「r2-2 상세」 |
| 3. select 문자열 무보호 | **닫힘(홈 한정)** | `workspace-home.test.tsx:31~36`이 `select()` 인자를 `state.wikiSelect`에 붙잡고 `:120~133`이 3종을 단언한다. 남은 구멍은 권고 2·3 |
| 4. `⚠️` 주석의 화면 개수 (낮음) | **미조치** | `WikiPageContent.tsx:140`은 여전히 "다른 다섯 화면" — 실제 제거는 여섯이다. 격리·정합성과 무관한 문서 정확도 항목이라 판정에 반영하지 않는다(spec-conformance 영역) |
| 5. 충돌 콜아웃의 모듈 파생 (낮음) | **닫힘** | `WikiPageContent.tsx:16~21`이 `verificationLabel({ disputed: true })`로 파생하고, 카피 계약 근거가 틀렸다는 사실(`grep -rl "Copywriting Contract" docs/` 0건)까지 주석에 남겼다 |

### r2-2 상세 — 만료가 네 겹 모두 배선됐다

- 모듈: `verification-label.ts:39~45`(입력 필드) · `:48~55`(`isExpired`) ·
  `:64~74`(`verified && 만료` → "검증 만료됨") · `:83~92`(`isVerified`가 만료 제외) ·
  `:98~107`(`isExpiredVerification` 신설).
- 홈: `app/w/[workspaceId]/page.tsx:52~54` select에 `expires_at`, `:73` 매핑,
  `KnowledgeGrid.tsx:22` 타입, `:103` `expired`, `:118` 배지 게이트,
  `:122` 톤 분기(`.badge.verified`는 살아있는 검증에만).
- 라이브러리: `wiki/page.tsx:33~34` `pageColumns`, `WikiLibrary.tsx:18` 타입,
  `:109` 통계, `:165` 라벨.
- 리더(대조군): `WikiPageContent.tsx:124~125`가 만료를 계산하고 `:364~373`이
  "검증 만료됨"을 띄운다. 모듈과 **같은 문자열·같은 결과**다 — 빈 문자열과 파싱
  불가 값 모두 양쪽에서 "만료 아님"으로 떨어진다(`NaN < now`는 false).
  즉 세 목적지가 이제 같은 판정을 낸다.
- `npx vitest run` 241 PASS / 0 FAIL, `npx tsc --noEmit` 오류 0 (새로 실행).

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 대시보드 전역에 `service_client`/service key 사용처 0건. 홈은 `page.tsx:34` `createClient()`(요청자 세션), 라이브러리는 `wiki/page.tsx:28` 동일, 공개 라우트만 `p/[slug]/[page]/page.tsx:38` `createPublicClient()`(anon). 이번 diff에서 클라이언트 팩토리(`lib/supabase/server.ts`·`public.ts`) 변경 0건 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블·마이그레이션 없음 |
| A-3 | anon 신규 GRANT/정책 | 해당 없음 | `supabase/` 변경 0건. `/p/`가 읽는 테이블은 여전히 사이드카 2개뿐이며 `disputed`·`expires_at` 모두 anon 표면에 닿지 않는다 |
| A-4 | service_role 코드의 workspace_id 필터 | 해당 없음 | `apps/worker/` 변경 0건 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 스키마 변경 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 이번 diff에 UPDATE/DELETE 경로 추가·변경 없음. 유일한 쓰기 경로인 검증 PATCH(`WikiPageContent.tsx:106~113`)는 무변경 |
| B-7 | SQLSTATE 42501 → 403 | 해당 없음 | 동일 |
| C-8 | 핸들러 멱등성 | 해당 없음 | 신규 잡 핸들러 없음 |
| C-9 | `jobs` 직접 UPDATE | 해당 없음 | `jobs` 접근 코드 변경 없음 |
| D-10 | `hnsw.iterative_scan` | 해당 없음 | 벡터 검색 경로 변경 없음 |
| D-11 | 토크나이저 버전 일치 | 해당 없음 | 검색·색인 경로 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 시도 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 `str.format` | 해당 없음 | 프롬프트 템플릿 변경 없음 |
| D-14 | 인용 앵커 | 통과 | `AskConversation.tsx` 변경은 eyebrow 제거 1건. 인용 조립·`CitationSidePanel`의 `raw_source_id`+`chunk_index`+char 구간·공개 페이지 `published_citations` 스냅샷(`p/…/page.tsx:71~73`) 전부 무변경 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 최대 번호는 여전히 `0017_wiki_bookmarks.sql`, 신규 파일 없음 |
| 요청 1 | 신뢰 판정 컬럼 누락 전면 훑기 | 통과 | 아래 「요청 1 상세」 |
| 요청 2 | 라이브러리 통계 숫자 ↔ 행 일치 | 통과 | `WikiLibrary.tsx:109`(`isVerified`)와 `:165`(`verificationLabel`)가 같은 입력 필드 3종을 본다. 충돌·만료 행은 카운트에서 빠지고 목록에서는 "충돌 감지"·"검증 만료됨"으로 그려진다 — 한 화면 안의 모순이 사라졌다 |
| 요청 3 | select 가드의 우회 가능성 | **부분 통과** | 가드는 실제로 발화 지점을 지킨다. 그러나 (a) `state.wikiSelect`가 `beforeEach`에서 초기화되지 않고 (b) select→props 매핑 한 겹이 무보호다 — 권고 2·3 |
| 요청 4 | 홈 배지 분기의 노출 표면 | 통과 | 아래 「요청 4 상세」 |
| 요청 5 | 클라이언트 시계 의존 | 통과(권고 있음) | 표시 계층 한정이고 리더의 기존 동작과 같은 방향이라 목적지 간 불일치를 만들지 않는다 — 아래 「요청 5 상세」·권고 1 |
| 요청 6 | 파싱 불가 `expires_at` 처리 | 통과 | DB 경로에서 도달 불가하고 리더와 같은 결과를 낸다 — 아래 「요청 6 상세」 |
| 요청 7 | 공개 라우트 `/p/` 회귀 | 통과 | 아래 「요청 7 상세」 |

### 요청 1 상세 — "신뢰 판정 컬럼을 select에서 빠뜨린 곳"을 전부 훑었다

`wiki_pages`를 읽는 모든 지점(11곳)과 검증 어휘를 그리는 모든 지점을 대조했다
(`grep -rn 'from("wiki_pages")'`, `grep -rn "검증\|충돌 감지"`).

- **리더 — 통과.** 두 진입 경로(`wiki/[slug]/page.tsx:38` 서버,
  `ContentViewer.tsx:216` 클라이언트)가 모두 `lib/wiki-lookup.ts:34~36`의 단일
  컬럼 목록을 쓰고 거기에 `expires_at`·`disputed`가 들어 있다.
- **신뢰 상태를 아예 표시하지 않는 목적지 — 컬럼을 안 읽는 게 맞다.** 백로그
  (`backlog/page.tsx:78` `id,slug,title` · `:98` `id,content`), 소스
  (`sources/page.tsx:57`), 그래프(`GraphCanvas.tsx:88`), 질문
  (`AskConversation.tsx:268` `slug`), 인용 패널(`CitationSidePanel.tsx:83`),
  통합 뷰의 인용 조회(`ContentViewer.tsx:379` `sources`). 이 여섯 곳은 검증
  라벨·배지를 하나도 렌더하지 않으므로(`검증` 문자열 등장 0건) 상태를 높게
  표시할 여지 자체가 없다.
- **프리뷰 — 해당 없음.** `PreviewWorkspace.tsx:527`·`:555`는 모듈을 쓰되 입력이
  정적 목업 픽스처다(DB 접근 0건). 픽스처에 `disputed`·`expires_at`이 없어 두
  분기가 프리뷰에서 도달 불가하지만, 실데이터가 아니라 사용자에게 잘못된 신뢰를
  보여줄 경로가 아니다.
- **공개 페이지 — 이번 change의 결함이 아니고, 고칠 자리도 select가 아니다.**
  `p/[slug]/[page]/page.tsx:108`의 `<span className="badge verified">검증 및
  승인됨</span>`은 무조건 렌더된다. 이 배지는 `wiki_pages`의 신뢰 컬럼이 아니라
  "발행본 행이 존재한다"에서 온다 — anon은 `wiki_pages`에 정책도 GRANT도 없어
  구조적으로 그 컬럼을 읽을 수 없다(불변식 §4, 사이드카가 존재하는 이유).
  실제 게이트는 `0016_public_sharing.sql:112~135`의
  `enforce_publication_verified` 트리거이고, 그 트리거는
  `verification_status = 'verified'`만 보고 `expires_at`을 보지 않는다. 따라서
  발행 후 검증이 만료돼도 공개면은 계속 "검증 및 승인됨"이다. 다만 이 diff는
  해당 파일의 className 한 줄만 건드렸고, 발행본은 "발행 시점에 사람이 승인한
  불변 스냅샷"이라는 별도 계약(PRD §4-2)을 갖는다 — 판정 대상이 아니라 후속
  이슈로 남긴다(권고 4).

결론: r1(`disputed`)·r2(`expires_at`)와 같은 부류의 **잔존 누락은 없다.**

### 요청 4 상세 — 홈 배지 분기(`verified || disputed || expired`)

- 출력은 `verificationLabel(page)`의 고정 4문자열뿐이다
  (`KnowledgeGrid.tsx:118~124`). 날짜(`verified_at`·`expires_at` 원값)나
  `verified_by`(계정 UUID)는 홈에 실리지 않는다 — 리더는 날짜를 보여주지만
  홈은 라벨만 보여주므로 노출 표면이 리더보다 **좁다**.
- 조회는 `page.tsx:55`의 `.eq("workspace_id", workspaceId)`를 그대로 유지하고
  RLS `wiki_pages_select_member`(`0004_rls_policies.sql:232~234`) 안에서 돈다.
  이번 diff에서 삭제·완화된 `.eq()` 0건.
- 새 테이블·조인·RPC 접근 0건. 읽는 컬럼 2종은 모두 이미 위키 라이브러리가
  같은 조건으로 읽던 `wiki_pages` 컬럼이다.

### 요청 5 상세 — 클라이언트 시계 의존

`verificationLabel`/`isVerified`/`isExpiredVerification`의 `now` 기본값은
`Date.now()`다(`verification-label.ts:66`·`:85`·`:100`). `KnowledgeGrid`·
`WikiLibrary`는 `"use client"`지만 홈·라이브러리 라우트가 서버 컴포넌트라
**첫 렌더는 서버 시계, 하이드레이션 이후는 브라우저 시계**로 평가된다. 결과:

1. 만료 경계를 사이에 둔 문서는 SSR 텍스트와 CSR 텍스트가 갈려 하이드레이션
   불일치가 나고, 최종 표시는 클라이언트 시계를 따른다.
2. 시계가 과거로 틀어진 클라이언트에서는 만료된 검증이 "검증됨"으로 보인다 —
   신뢰를 실제보다 높게 보이는 방향이다.

그럼에도 위반으로 보지 않는 근거는 셋이다. (a) 리더가 이미 같은 방식이라
(`WikiPageContent.tsx:124~125` — 이번 diff 이전부터) 세 목적지가 **같은 시계로
같은 답**을 낸다. 이번 change의 계약("한 상태가 두 목적지에서 다르게 불리지
않는다")이 깨지지 않는다. (b) 이 판정에 접근 제어가 걸려 있지 않다 — 발행
게이트는 DB 트리거, 검증 전이는 API+RLS, 목록 조회 범위는 RLS다. 표시 계층
한정이다. (c) 서버 판정과 어긋나는 시나리오에서도 DB의 값 자체는 손상되지
않는다. 개선안은 권고 1.

### 요청 6 상세 — `Number.isFinite` 가드

`verification-label.ts:52~54`가 파싱 불가한 `expires_at`을 "만료 아님"으로
떨어뜨린다. 「조용한 실패」 규칙에 비추어 판단하면:

- **도달 가능한 입력이 DB 경로에 없다.** `expires_at`은 `timestamptz`
  (`0007_search_and_queue_extensions.sql:255`)이고 PostgREST는 항상 ISO 8601
  오프셋 문자열로 직렬화한다. 파싱 불가 값은 픽스처·수기 입력에서만 나온다.
- **리더와 같은 결과를 낸다.** `WikiPageContent.tsx:125`의
  `new Date(expiresAt).getTime() < Date.now()`도 `NaN` 비교라 false다. 즉 이
  선택은 목적지 간 일치를 유지하는 쪽이다.

따라서 규칙 위반이 아니다. 다만 주석의 "다른 경로에서 드러나게 둔다"는 실제로
드러나는 경로가 없다(로그·텔레메트리 없음) — 권고 5.

### 요청 7 상세 — 공개 라우트 `/p/` 회귀 여부

r1·r2에서 통과였던 항목이 그대로 유지된다.

- 이번 diff의 변경은 `:99` className 한 줄(`eyebrow` → `breadcrumb-path`)과 주석
  2줄뿐(`git diff HEAD` +3/-1).
- 클라이언트는 `createPublicClient()`(`:38`) — `authenticated`로 승격되지 않았다.
- 읽는 테이블은 사이드카 2개(`:44~50`, `:56~63`)뿐. `wiki_pages` 조인 없음 →
  이번에 홈·라이브러리가 읽기 시작한 `expires_at`도 공개 표면에 닿지 않는다.
- `:61` `.eq("workspace_id", settingsData.workspace_id)` 유지. `:65~69`의
  "구분해 응답하지 않는다"(존재 여부 누출 방지) 분기 무변경.
- 렌더 필드는 발행 스냅샷 + 공개 설정뿐이고 `stripWikiLinks`(`:187~192`)도 그대로.
- CSS diff에 `display`·`visibility`·`overflow`·`opacity`·`max-height` 변경 0건
  (grep으로 확인) — 공개면에서 정보가 숨겨지거나 새로 드러나는 변경이 없다.

## 조치가 필요한 항목

없다. 이번 라운드에서 확인된 위반(A~E 및 요청 1·2·4·6·7)은 0건이다.
아래는 판정을 바꾸지 않는 후속 권고이며, 이 change에서 처리해도 되고 후속
이슈로 넘겨도 된다.

1. **만료 판정 기준 시각을 서버에서 내려보낸다** (심각도: 낮음, 권고)
   - 위치: `apps/dashboard/app/w/[workspaceId]/page.tsx:66~76` ·
     `apps/dashboard/app/w/[workspaceId]/wiki/page.tsx:80` /
     `apps/dashboard/lib/verification-label.ts:66`
   - 깨지는 것: SSR과 하이드레이션이 서로 다른 시계로 만료를 평가해, 경계에 걸친
     문서에서 하이드레이션 불일치가 나고 최종 표시는 클라이언트 시계를 따른다.
     시계가 뒤로 틀어진 단말에서는 만료된 검증이 "검증됨"으로 남는다.
   - 조치: 라우트(서버)에서 `Date.now()`를 한 번 계산해 prop으로 내리고
     컴포넌트가 `verificationLabel(page, now)`처럼 넘긴다. 모듈이 이미 `now`
     파라미터를 받으므로 배선만 하면 된다.

2. **select 가드의 상태를 테스트마다 초기화한다** (심각도: 낮음, 권고)
   - 위치: `apps/dashboard/tests/workspace-home.test.tsx:61~65`(`beforeEach`) ·
     `:24`(`wikiSelect: ""`)
   - 깨지는 것: `state.wikiSelect`가 `beforeEach`에서 리셋되지 않는다. 지금은
     무해하다(홈이 `wiki_pages`를 무조건 조회하므로 조회가 사라지면 세 테스트
     모두 빈 문자열이 된다). 그러나 홈 쿼리가 조건부로 바뀌면 — 라이브러리의
     `bookmarked` 분기(`wiki/page.tsx:55~57`)가 이미 그런 형태다 — 앞 테스트가
     남긴 문자열로 가드가 통과할 수 있다.
   - 조치: `beforeEach`에 `state.wikiSelect = "";` 한 줄.

3. **가드가 덮지 못하는 한 겹: select → props 매핑** (심각도: 보통, 권고)
   - 위치: `apps/dashboard/app/w/[workspaceId]/page.tsx:66~76` /
     `apps/dashboard/tests/workspace-home.test.tsx:11~19`(픽스처 타입) ·
     `:120~133`(가드)
   - 깨지는 것: 가드는 select **문자열 한 겹**만 지킨다. `:72`의
     `disputed: p.disputed`나 `:73`의 `expires_at: p.expires_at`를 지우면
     증상은 r1이 잡은 것과 똑같이 "충돌·만료 문서가 홈에서 검증됨으로 보인다"인데,
     `tsc`는 통과한다(`createClient()`가 제네릭 DB 타입을 안 쓰므로 `p`는 사실상
     `any`이고 `WikiPageSummary`의 두 필드는 optional이다) 그리고 241건 전부
     green이다. 홈 테스트의 픽스처 타입(`:11~19`)에도 두 컬럼이 없어 렌더 단언도
     이를 잡지 못한다. `verification-label.test.tsx`는 컴포넌트에 props를 직접
     넘기므로 이 구간을 통과하지 않는다.
   - 조치: `workspace-home.test.tsx`의 픽스처에 `disputed`·`expires_at` 필드를
     넣고, 충돌·만료 문서를 렌더해 라벨이 "충돌 감지"·"검증 만료됨"으로 나오는지
     단언한다. 그러면 select→매핑→타입→렌더 전 구간이 한 테스트로 덮인다.
     같은 자리에서 `.eq("workspace_id", …)` 호출 여부도 붙잡아 두면 워크스페이스
     필터 제거까지 막힌다(r2 조치 3의 미처리 잔여분).

4. **발행 게이트가 `expires_at`을 보지 않는다** (심각도: 보통, 이번 change 범위 밖)
   - 위치: `supabase/migrations/0016_public_sharing.sql:112~135` /
     `apps/dashboard/app/p/[slug]/[page]/page.tsx:108`
   - 깨지는 것: 트리거는 발행 시점의 `verification_status = 'verified'`만 확인하고
     만료를 보지 않는다. 발행 후 검증이 만료되면 내부 화면 세 곳은 모두
     "검증 만료됨"인데 공개면만 "검증 및 승인됨"으로 남는다 —
     `0007:240~241`이 금지한 "영원히 verified" 상태의 공개 표면 판본이다.
   - 조치: 이 change에서 고치지 않는다(발행 스냅샷 계약과 얽혀 있고 SQL 변경이
     필요하다). 후속 이슈로 등록하고, 만료를 반영할지 아니면 "승인 시점의
     스냅샷"이라는 계약을 공개면 문구에 명시할지를 결정한다.

5. **`Number.isFinite` 가드 주석의 사실 한 줄** (심각도: 낮음, 권고)
   - 위치: `apps/dashboard/lib/verification-label.ts:52~53`
   - 깨지는 것: "다른 경로에서 드러나게 둔다"고 적었으나 드러나는 경로가 없다
     (로그·텔레메트리 없음). 이 저장소에서 주석은 판단 근거로 쓰이므로 다음
     사람이 존재하지 않는 관측 경로를 전제할 수 있다.
   - 조치: "DB 경로에서는 도달 불가한 방어다(`expires_at`은 timestamptz라 항상
     ISO 8601로 온다) — 픽스처·수기 입력에서만 걸린다"로 좁힌다.

## 판정 근거

테넌트 경계는 이번 라운드에도 뚫리지 않았고, r2가 남긴 세 지적이 모두 닫혔다.
`service_role`/service client는 대시보드 전역에 0건이며 홈·라이브러리 모두
요청자 세션 클라이언트를 쓴다. 새로 읽기 시작한 `expires_at`은 이미 리더가 같은
조건으로 읽던 `wiki_pages` 컬럼이고, `.eq("workspace_id", …)`와 RLS
`wiki_pages_select_member`가 그대로라 노출 표면이 넓어지지 않았다. `anon`에는
새 GRANT·정책·테이블 접근이 붙지 않았고 `/p/`는 여전히 `createPublicClient()`로
사이드카 2개만 읽으며 CSS 변경에도 숨김 방향 선언이 없다. SQL·API·워커 변경이
0건이라 A·B·C·E는 대부분 해당 없음이고 마이그레이션 번호 충돌도 없다.

r1·r2가 두 라운드에 걸쳐 쫓던 부류 — "신뢰 판정 컬럼을 select에서 빠뜨려 목적지
마다 상태가 갈리고, 옵셔널 필드 + 구조적 타이핑 탓에 타입 검사도 테스트도 침묵
하는 것" — 은 이번에 홈·라이브러리·리더 세 목적지를 전수 대조한 결과 **잔존
사례가 없다.** 검증 어휘를 그리는 다른 지점도 없고(나머지 여섯 조회는 신뢰
상태를 아예 렌더하지 않는다), 발화 지점인 홈의 select 문자열에는 실패하는 가드가
붙었다. 만료 판정은 리더의 기존 규칙과 문자열·결과가 모두 일치하며, 클라이언트
시계 의존과 파싱 실패 처리는 리더가 이미 하던 것과 같은 방향이라 목적지 간
불일치를 새로 만들지 않는다.

남은 권고 5건은 모두 방어 심도(테스트 커버리지·주석 정확도)이거나 이번 diff가
건드리지 않은 기존 계약(발행 게이트)이다. 현재 코드가 사용자에게 잘못된 신뢰
상태를 보여주는 경로는 없고 데이터가 조용히 손상되는 경로도 없다. 따라서
`pass`로 판정한다. 권고 3은 같은 실수가 다시 들어오는 것을 막는 값이 크므로,
PR 전에 처리할 수 있으면 처리하기를 권한다 — 다만 이번 라운드의 게이트 통과
조건은 아니다.
