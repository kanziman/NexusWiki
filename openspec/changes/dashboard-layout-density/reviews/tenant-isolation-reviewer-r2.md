# Tenant Isolation 리뷰 — dashboard-layout-density r2

- 판정: needs_fix
- 대상: `feat/dashboard-layout-density` 워킹 트리 diff (base `747d7de`)
- 일시: 2026-08-20T22:52:12Z

> ⚠️ r1 과 동일하게 브랜치 HEAD 가 `main`(`747d7de`)이고 변경분이 전부 커밋되지
> 않은 상태다(`git diff main...HEAD` 는 빈 출력). 실제 검사 대상은
> `git diff HEAD`(14개 파일) + untracked 2건
> (`apps/dashboard/lib/verification-label.ts`,
> `apps/dashboard/tests/verification-label.test.tsx`) + `openspec/changes/` 문서다.

## r1 지적 사항 처리 확인

| r1 항목 | 상태 | 근거 |
| --- | --- | --- |
| 1. 홈 대시보드 `disputed` 누락 | **닫힘** | 아래 「r1-1 상세」 |
| 2. 위키 라이브러리 한 화면 안의 이중 어휘 · disputed 를 검증으로 카운트 | **미조치** | `WikiLibrary.tsx:101~106` 무변경. 아래 조치 1번 |
| 3. `.eyebrow` ⚠️ 주석과 실제 사용처 불일치 | **거의 닫힘** | 앱·프리뷰의 `.eyebrow` 사용처 0건 확인(잔존은 전부 "두지 않는다" 주석). 숫자 하나가 어긋난다 — 아래 조치 4번 |

### r1-1 상세 — 네 겹 전부 배선됐다

r1 이 지목한 두 겹(쿼리·타입) 과 파생 문제(렌더 게이트)가 모두 닫혔다.

- `app/w/[workspaceId]/page.tsx:50~52` — select 에 `disputed` 추가. `:53` 의
  `.eq("workspace_id", workspaceId)` 는 그대로 유지된다(신규 컬럼을 읽으면서
  워크스페이스 필터가 빠지지 않았다).
- `app/w/[workspaceId]/page.tsx:70` — 매핑에 `disputed: p.disputed` 추가.
- `KnowledgeGrid.tsx:17` — `WikiPageSummary` 에 `disputed?: boolean | null` 추가.
- `KnowledgeGrid.tsx:106~114` — r1 이 지적한 (b) "게이트가 `verified &&` 라
  disputed 문서는 표식이 통째로 사라진다"를 `(verified || disputed)` 로 열고,
  라벨은 `verificationLabel(page)`, 톤 클래스만 `verified ? "badge verified" : "badge"`
  로 분기한다. 정보 은폐 쪽으로 닫지 않은 것이 맞는 선택이다.
- 회귀 테스트 `tests/verification-label.test.tsx:62~93` — 두 컴포넌트를 실제로
  렌더해 같은 문서에서 같은 라벨("충돌 감지")이 나오는지 대조한다. r1 이 요구한
  "렌더 기반" 검증이다. `npx vitest run` 238 PASS / 0 FAIL, `tsc --noEmit` 오류 0.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 대시보드 전체에서 `service_role`/service key 사용처 0건. 이번에 수정된 홈 쿼리는 `app/w/[workspaceId]/page.tsx:34` 의 `createClient()`(요청자 세션)를 그대로 쓴다. 공개 라우트만 `createPublicClient()`(anon, `app/p/[slug]/[page]/page.tsx:38`) |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블·마이그레이션 없음 |
| A-3 | anon 신규 GRANT/정책 | 해당 없음 | `supabase/` 변경 0건. `/p/` 가 읽는 테이블은 여전히 사이드카 2개뿐이며 `disputed` 를 포함해 어떤 컬럼도 anon 표면에 추가되지 않았다 |
| A-4 | service_role 코드의 workspace_id 필터 | 해당 없음 | `apps/worker/` 변경 0건 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 스키마 변경 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 이번 diff 에 UPDATE/DELETE 경로 추가·변경 없음. 기존 매핑(`WorkspaceGeneralSettings.tsx:64~70`, `MembersList.tsx:99~106`)은 손대지 않았다 |
| B-7 | SQLSTATE 42501 → 403 | 해당 없음 | 동일 |
| C-8 | 핸들러 멱등성 | 해당 없음 | 신규 잡 핸들러 없음 |
| C-9 | `jobs` 직접 UPDATE | 해당 없음 | `jobs` 접근 코드 변경 없음 |
| D-10 | `hnsw.iterative_scan` | 해당 없음 | 벡터 검색 경로 변경 없음 |
| D-11 | 토크나이저 버전 일치 | 해당 없음 | 검색·색인 경로 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 시도 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 `str.format` | 해당 없음 | 프롬프트 템플릿 변경 없음 |
| D-14 | 인용 앵커 | 통과 | `AskConversation.tsx` 변경분은 eyebrow 제거(:289~293) 1건. 인용 조립·`CitationSidePanel.tsx:83~90`(`raw_source_id,chunk_index,char_start,char_end`)·공개 페이지 `published_citations` 스냅샷 전부 무변경 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 최대 번호는 여전히 `0017_wiki_bookmarks.sql`, 신규 파일 없음 |
| 요청 1 | 다른 목적지의 상태 컬럼 누락 | **위반** | `expires_at` 이 홈·라이브러리 어디에도 select 되지 않고 `verification-label.ts` 도 만료를 모른다 — 아래 조치 2번. 라이브러리·리더의 `disputed` 는 정상(`wiki/page.tsx:31`, `lib/wiki-lookup.ts:35`) |
| 요청 2 | disputed 배지의 노출 표면 | 통과 | `disputed` 는 `wiki_pages` 컬럼이고 홈 쿼리는 `.eq("workspace_id", workspaceId)` + RLS `wiki_pages_select_member` 안에서 돈다. 조인·RPC·새 테이블 접근 없음. 라이브러리(`wiki/page.tsx:31`)가 이미 같은 컬럼을 같은 조건으로 읽고 있어 노출 표면이 넓어지지 않는다 |
| 요청 3 | 신규 컬럼 조회 시 워크스페이스 필터 | 통과 | `app/w/[workspaceId]/page.tsx:53` 유지. 이번 diff 에서 삭제·완화된 `.eq()` 0건 |
| 요청 4 | 공개 라우트 `/p/` 회귀 | 통과 | 아래 「요청 4 상세」 |
| 요청 5 | 알 수 없는 상태값·null 처리 | **부분 위반** | 미지 enum·undefined 는 "검증 필요"로 안전하게 떨어진다(`verification-label.ts:49`, 테스트 `:105~110`). 그러나 라이브러리 통계가 disputed 를 검증으로 세고(조치 1), 만료된 검증이 "검증됨"으로 보인다(조치 2) — 둘 다 신뢰를 실제보다 높게 보이게 하는 방향이다 |

### 요청 4 상세 — 공개 페이지(`anon`)

`app/p/[slug]/[page]/page.tsx` 의 r2 시점 변경은 여전히 `:94~99` 한 줄
(`className="eyebrow"` → `"breadcrumb-path"`)과 주석뿐이다. r1 에서 확인한 것이
그대로 유지된다.

- 클라이언트는 `createPublicClient()`(`:38`) — `authenticated` 로 승격되지 않았다.
- 읽는 테이블은 사이드카 2개(`:45`, `:57`)뿐. `wiki_pages` 조인이 추가되지 않았고,
  따라서 이번에 홈에 추가된 `disputed` 도 공개 표면에는 닿지 않는다.
- `:61` `.eq("workspace_id", settingsData.workspace_id)` 유지.
- `allow_public_sharing` 을 앱이 다시 적지 않는다는 `:39~42` 주석의 전제(anon 실행)도
  그대로다.
- CSS 변경은 전부 **키우는** 방향이다(`.public-badge` 9px→12px `:2665~2668`,
  `.public-stamp` 10px→12px `:2672`). `display:none` · `visibility` · 잘라내기
  변경 0건 — 표시되던 정보가 숨겨지는 방향의 변경은 없다.

## 조치가 필요한 항목

1. **위키 라이브러리 통계가 충돌 문서를 "검증 완료"로 센다 — 같은 화면에서 숫자와 행이 모순** (심각도: 높음, r1-2 미조치 이월)
   - 위치: `apps/dashboard/components/WikiLibrary.tsx:101~106` (vs 같은 파일 `:160`)
   - 깨지는 것: 통계 술어가 `p.verification_status === "verified"` 라
     `disputed = true` 인 문서까지 카운트에 넣는다. 그런데 바로 아래 목록의
     같은 행은 `stateLabel`(=`verificationLabel`)을 통해 **"충돌 감지"** 로
     그려진다. 즉 "검증 완료 3"이라고 적힌 화면에서 행 하나가 "충돌 감지"다 —
     사용자는 숫자와 목록 중 무엇을 믿어야 할지 알 수 없고, 예외도 나지 않는다.
     r1 이 홈에서 잡아낸 "충돌 문서가 검증으로 보인다"와 **정확히 같은 오표시**가
     라이브러리 통계 쪽에 그대로 남아 있다. 부가로 어휘도 갈린다: 통계는
     "검증 완료", 목록은 "검증됨"으로 같은 값을 두 이름으로 부른다 — 이번 change
     가 목적지 간에서 없앤 이중 어휘가 한 화면 안에 남았다.
   - 조치: 카운트 술어를 `pages.filter(isVerified).length` 로 바꾸고(이미 export
     돼 있다), 통계 라벨을 목록과 같은 "검증됨"으로 맞춘다.

2. **만료된 검증이 홈·라이브러리에서 "검증됨"으로 표시된다 — r1 이 잡은 것과 같은 종류의 컬럼 누락** (심각도: 높음)
   - 위치: `apps/dashboard/lib/verification-label.ts:45~58` /
     `apps/dashboard/app/w/[workspaceId]/page.tsx:50~52`(select) /
     `apps/dashboard/app/w/[workspaceId]/wiki/page.tsx:31`(`pageColumns`) /
     대조군 `apps/dashboard/components/WikiPageContent.tsx:360~370`
   - 깨지는 것: `wiki_pages.expires_at` 은 실재하는 컬럼이고
     (`supabase/migrations/0007_search_and_queue_extensions.sql:255`), 그 주석이
     **"만료된 검증을 검증으로 세면 오래된 위키가 영원히 verified 로 남습니다"**
     (`0007:240~241`), **"지나면 verification_status 를 그대로 신뢰하지 않는다"**
     (`0007:259`)라고 못박았다. 위키 리더는 이 계약을 지킨다 —
     `WikiPageContent.tsx:120~121` 이 `isExpired` 를 계산하고 `:360~370` 이
     danger 톤 "검증 만료됨 · 재검증 필요"를 띄운다. 그러나
     - 홈 select(`page.tsx:50~52`)와 라이브러리 select(`wiki/page.tsx:31`) 어디에도
       `expires_at` 이 없고,
     - 새로 만든 단일 출처 `verificationLabel`/`isVerified` 는 만료 개념 자체를
       모르며 입력 타입(`verification-label.ts:24~36`)에도 필드가 없다.

     결과: 검증이 만료된 문서가 홈·라이브러리에서는 초록 톤
     `<b class="badge verified">검증됨</b>` 인데, 그 문서를 열면 붉은 톤
     "검증 만료됨 · 재검증 필요"다. **r1-1 과 완전히 같은 구조의 결함이다** —
     상태를 결정하는 컬럼을 select 하지 않아 목적지마다 같은 문서가 다른 신뢰
     상태로 보이고, 옵셔널 필드 + 구조적 타이핑 때문에 타입 검사도 238건의
     테스트도 아무 소리를 내지 않는다. 방향도 나쁜 쪽이다(실제보다 더 검증된 것처럼).
     - 도달 가능성: 대시보드의 검증 버튼(`WikiPageContent.tsx:102~105`)은
       `expires_at` 을 보내지 않으므로 **현재 UI 만으로는 만료 행을 만들 수 없다.**
       그러나 `PATCH /workspaces/{ws}/wiki/{id}/verify` 는 `expires_at` 을 정식
       요청 필드로 받고(`apps/api/src/api/routers/wiki.py:31`, `:54~55`) 응답으로도
       돌려준다. 즉 이미 열려 있는 계약이고, 리더는 그 분기를 이미 그리고 있다.
   - 조치: 둘 중 하나를 택하되 **묵시적으로 두지 않는다.**
     (a) `VerificationLabelInput` 에 `expires_at?: string | null` 을 추가해
         `verificationLabel`/`isVerified` 가 만료를 리더와 같은 규칙으로 판정하게
         하고, 두 select 에 `expires_at` 을 넣는다(리더의 "검증 만료됨" 문구도
         이 모듈에서 파생시킨다). 또는
     (b) 이번 change 의 범위 밖으로 미룬다면 `verification-label.ts` 의 docblock 에
         "이 모듈은 `expires_at` 을 판정하지 않는다 — 목록 화면은 만료된 검증을
         검증으로 표시한다"를 ⚠️ 로 명시하고 후속 이슈를 건다. 계약만 선언하고
         한 축이 비어 있는 지금 상태가 r1 이 지적한 것과 같은 이유로 가장 나쁘다.

3. **select 컬럼 목록 자체는 여전히 어떤 테스트도 지키지 않는다** (심각도: 보통)
   - 위치: `apps/dashboard/tests/workspace-home.test.tsx:26~29`
   - 깨지는 것: 이 테스트의 Supabase 모의는 `select: () => query` 로 **컬럼 인자를
     통째로 버린다.** 새로 추가된 `tests/verification-label.test.tsx` 는 컴포넌트에
     props 를 직접 넘겨 렌더하므로 컬럼 목록을 전혀 통과하지 않는다. 따라서 r1 이
     지목한 실제 발화 지점 — `page.tsx:50~52` 의 select 문자열에서 `disputed` 가
     빠지는 것 — 은 지금 되돌려도 238건 전부 green 이다. 회귀 방지가 근본 원인이
     아니라 그 아래 한 겹(컴포넌트 배선)에만 걸려 있다.
   - 조치: 홈 테스트의 모의를 `select: (cols: string) => { captured = cols; return query }`
     처럼 인자를 붙잡게 바꾸고, `wiki_pages` select 가 `disputed` 를 포함하는지
     (2번을 (a)로 처리하면 `expires_at` 도) 단언한다. 같은 자리에서
     `.eq("workspace_id", …)` 호출 여부도 함께 붙잡아 두면 워크스페이스 필터
     제거도 테스트가 막는다.

4. **⚠️ 주석의 화면 개수가 실제와 하나 어긋난다** (심각도: 낮음)
   - 위치: `apps/dashboard/components/WikiPageContent.tsx:136`
   - 깨지는 것: "다른 다섯 화면의 eyebrow 는 제거됐다"라고 적혀 있으나 실제
     제거는 여섯이다 — 홈(`app/w/[workspaceId]/page.tsx:104`), 설정
     (`settings/page.tsx:60`), 위키 라이브러리(`WikiLibrary.tsx:89`), 백로그
     (`BacklogList.tsx:82`), 질문(`AskConversation.tsx:289`), 소스
     (`SourcesList.tsx:143`). 같은 사실을 적은 다른 두 주석은 여섯/일곱으로
     맞다(`PreviewWorkspace.tsx:675` "앱의 여섯 화면",
     `nexuswiki-design-system.css:476~483` "앱의 일곱 화면"=6+리더). 이 저장소에서
     `⚠️` 주석은 판단 근거로 쓰이므로 숫자가 어긋나면 다음 편집자가 남은 사용처를
     찾으러 간다. (r1-3 의 나머지 — "프리뷰에만 남는다"는 서술 — 는 이번에
     사실이 됐다: `apps/dashboard` 전체에 살아 있는 `.eyebrow` 사용처 0건 확인.)
   - 조치: `다섯` → `여섯`.

5. **리더의 충돌 문구만 모듈 밖에 남았는데 그 예외가 기록돼 있지 않다** (심각도: 낮음)
   - 위치: `apps/dashboard/components/WikiPageContent.tsx:16~17`, `:165~168`
   - 깨지는 것: `DISPUTED_CALLOUT` 은 "충돌 감지**됨** — …"이고 목록의 라벨은
     "충돌 감지"다. 바로 아래 `partial` 분기는 같은 종류의 차이("부분 검증됨" vs
     "부분 검증")를 이번에 모듈 파생으로 해소하면서 `:375~377` 에 이유를 적었는데,
     `disputed` 는 UI-SPEC 카피 계약(`:13` "문구를 한 글자도 바꾸지 않는다")이라
     바꿀 수 없으면서도 그 예외가 어디에도 적혀 있지 않다. 다음 사람이 둘 중
     하나를 "빠뜨린 것"으로 오인하고 카피 계약 쪽을 건드릴 여지가 남는다.
   - 조치: `DISPUTED_CALLOUT` 선언부에 "라벨(`verificationLabel`)과 달리 이 문구는
     카피 계약이라 모듈에서 파생하지 않는다"를 한 줄 남긴다.

## 판정 근거

테넌트 경계는 이번 라운드에도 뚫리지 않았다. `service_role`/service client 는
대시보드 전역에 0건이고, 새로 읽기 시작한 `disputed` 는 이미 위키 라이브러리가
같은 조건으로 읽던 `wiki_pages` 컬럼이라 노출 표면이 넓어지지 않았으며,
`.eq("workspace_id", workspaceId)` 도 그대로다. `anon` 에 새 GRANT·정책·테이블
접근이 붙지 않았고 `/p/` 는 여전히 `createPublicClient()` 로 사이드카 2개만 읽는다.
SQL·API·워커 변경이 0건이라 A·B·C·E 는 대부분 해당 없음이고 마이그레이션 번호
충돌도 없다. 따라서 `blocked` 이 아니다.

`pass` 도 아니다. r1-1 은 네 겹 모두 닫혔고 렌더 기반 회귀 테스트까지 붙었지만,
**같은 부류의 조용한 오표시가 두 건 남아 있다.** 하나는 r1-2 를 손대지 않아
남은 것으로, 라이브러리 통계가 "충돌 감지"로 그려진 행을 "검증 완료"에 세어 한
화면 안에서 숫자와 목록이 모순된다. 다른 하나는 이번 라운드에 새로 확인한
`expires_at` 누락으로, 만료된 검증이 홈·라이브러리에서는 "검증됨"인데 리더에서는
"검증 만료됨"이다 — 상태를 결정하는 컬럼을 select 하지 않아 목적지마다 신뢰
상태가 갈리는, r1-1 과 구조가 완전히 같은 결함이고 방향도 실제보다 더 검증된
것처럼 보이는 쪽이다. 둘 다 예외를 던지지 않고 238건의 테스트를 통과하며,
`Core Value` 인 추적 가능한 신뢰 표시를 실제보다 높게 보이게 한다. 게다가 r1 이
지목한 발화 지점(select 컬럼 목록)은 지금도 어떤 테스트의 보호도 받지 않아 같은
실수가 다시 들어올 수 있다. 전부 코드 수정으로 해결되고 테넌트 경계를 넘지는
않으므로 `needs_fix` 로 판정한다.
