# Tenant Isolation 리뷰 — landing-evaluation-intro r1

- 판정: pass
- 대상: 커밋 전 작업 트리 (`git diff` + 미추적 파일, 기준 HEAD `8b0fde4961a1614de604754c703a91e462a151d0`). `git diff main...HEAD`는 비어 있다 — 변경이 아직 커밋되지 않았다.
- 일시: 2026-11-11T13:25:04Z

검사 범위:

- 수정: `apps/dashboard/app/p/[slug]/[page]/page.tsx`, `apps/dashboard/components/PublicLandingPage.tsx`, `apps/dashboard/lib/experiments.ts`, `apps/dashboard/tests/experiments.test.ts`, `apps/dashboard/tests/public-wiki-page-route.test.tsx`
- 신규: `apps/dashboard/components/public-landing/PublicLandingEvaluation.tsx`, `apps/dashboard/tests/PublicLandingEvaluation.test.tsx`, `openspec/changes/landing-evaluation-intro/`
- `supabase/migrations/`, `apps/api/`, 워커, `lib/supabase/*`, `middleware.ts`에는 변경이 없다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 변경 파일 어디에도 `service_role`·service client가 없다. 공개 위키 경로는 기존 `createPublicClient()`(anon)를 그대로 쓰고(`app/p/[slug]/[page]/page.tsx:59`), 바뀐 것은 헤더 마크업뿐이다(`:123-132`). 랜딩 평가 섹션은 Supabase 클라이언트를 하나도 쓰지 않고 커밋된 정적 JSON만 import한다(`lib/experiments.ts:1`, `components/public-landing/PublicLandingEvaluation.tsx:3-11`). 홈 링크를 실제로 눌러 `/`로 가면 기존 `app/page.tsx`가 요청자 세션 클라이언트(`createClient`, RLS 적용)로 `workspaces`를 읽는다. 사용자가 이동한 경우에만 그렇고, 이번 변경 전과 같은 동작이다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 해당 없음 | 마이그레이션 변경 없음. 공개 위키 경로가 조회하는 테이블은 여전히 사이드카 두 개(`workspace_public_settings`, `wiki_page_publications`)뿐이다(`page.tsx:65-83`). `workspaces`·`wiki_pages`·`source_chunks` 조인이 새로 생기지 않아 불변식 §4가 유지된다 |
| A-4 | service_role 코드의 `workspace_id` 필터 | 해당 없음 | 워커·service_role 코드 변경 없음 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | UPDATE/DELETE 경로 없음. 공개 경로의 읽기 0행은 기존대로 `notFound()`이며 킬스위치 OFF·미발행·없는 슬러그를 구분하지 않는다(`page.tsx:73-94`, 변경 없음) |
| B-7 | `42501` → 403 매핑 | 해당 없음 | 쓰기 경로 없음 |
| C-8 | 핸들러 멱등성·upsert 키 | 해당 없음 | 작업 핸들러 변경 없음 |
| C-9 | `jobs` 직접 UPDATE 금지 | 해당 없음 | `jobs` 접근 없음 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 벡터 검색 변경 없음 |
| D-11 | 토크나이저 일치·`tsv_tokenizer_version` | 해당 없음 | 색인·질의 경로 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 스키마 변경 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 프롬프트 변경 없음 |
| D-14 | LLM 컨텍스트 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립 변경 없음 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음(최대 번호는 그대로 `0037_eval_experiments.sql`) |

### 호출자 요청 추가 확인

| 항목 | 결과 | 근거 |
| --- | --- | --- |
| 공개 표면의 사용자 세션 클라이언트 | 통과 | `/p/` 경로는 anon 공개 클라이언트를 유지한다. 세션 클라이언트를 쓰면 0016의 `*_select_member` 정책이 멤버에게 킬스위치를 무력화하는데, 이 회귀는 없다(`page.tsx:55-59` 주석과 코드 변경 없음). 랜딩 컴포넌트는 `"use client"`인 `PublicLandingPage` 아래에서 정적 데이터만 렌더링한다 |
| prefetch로 생기는 원치 않은 인증·DB 요청 | 통과 | 새 `Link`에는 모두 `prefetch={false}`가 붙어 있다. 공개 위키 홈 링크(`page.tsx:125-130`), 대표 실험 상세 링크(`PublicLandingEvaluation.tsx:112-119`), 카드 3개(`:184-188`)가 해당한다. Next `15.5.22` App Router에서 `prefetch={false}`는 화면 진입 시 프리페치와 hover 프리페치를 둘 다 끈다. 그래서 세션 쿠키를 가진 방문자가 `/p/`를 열기만 해서는 `/`의 서버 렌더링(`createClient` → `auth.getUser` → `workspaces` 조회)이 돌지 않는다. 두 소스 검사 테스트가 이를 고정한다(`tests/public-wiki-page-route.test.tsx`의 "홈 링크는 / 를 프리페치하지 않는다", `tests/PublicLandingEvaluation.test.tsx`의 "링크가 대상 라우트를 프리페치하지 않는다"). 참고로 `/p/` 요청 자체에서 미들웨어가 `getUser`를 부르는 것은 원래 동작이고 이번 변경과 관계없다 |
| `/w/` 링크 유출 | 통과 | 추가된 링크 대상은 `/`, `/showcase/evidence-research`, `/showcase/evaluation`, `/showcase/controlled-ai`, `/showcase/regression`뿐이다. 워크스페이스 ID가 들어간 경로는 없다 |
| 판정이 없을 때 지어낸 값을 보이는 조용한 실패 | 통과 | `featuredAdoption`(`lib/experiments.ts:129-143`)은 결정 기록이 있는 첫 도입 실험만 고른다. `experimentFor`가 돌려준 실험이 같은 id가 아니거나(`:139`) 기준·정책·결정 중 하나라도 없으면(`:141`) `undefined`를 돌려준다. 이때 컴포넌트는 블록을 아예 그리지 않는다(`PublicLandingEvaluation.tsx:170-175`). 결정이 가리키는 기준 세트와 실험의 기준 세트가 서로 다를 가능성은 원천 DB의 복합 FK `(experiment_id, criteria_set_id) → eval_experiments(id, criteria_set_id)`가 막는다(`supabase/migrations/0037_eval_experiments.sql:98-99`). 합성 표기는 `snapshot.synthetic === true`일 때만 붙는다. 이 값이 빠지면 표기도 빠지는 구조지만, 내보내기 스크립트가 루트 키 집합에 `synthetic`을 강제하고 항상 `True`를 쓰므로(`scripts/eval_experiments.py:82`, `:490`) 현재 경로로는 누락될 수 없다. 대체 표시·비합성 표시·결정 누락은 테스트가 덮는다 |
| 테넌트 데이터 노출 | 통과 | `content/experiments.json`에는 실험 id, 실행 별칭(`off`/`on`, `run-1`/`run-2`), 저장소 상대 경로, 집계 문자열만 있고 `workspace_id`·사용자·원문 내용이 없다. `synthetic: true`인 합성 평가 기록이다. 공개 위키 헤더에 새로 보이는 값도 없다(`workspaceDisplayName`은 원래 렌더링되던 사이드카 값이다) |

확인 실행: `npx vitest run tests/PublicLandingEvaluation.test.tsx tests/experiments.test.ts tests/public-wiki-page-route.test.tsx tests/PublicLandingPage.test.tsx` → 24개 통과, 0개 실패.

## 조치가 필요한 항목

없음.

## 판정 근거

이번 변경은 정적 스냅샷 렌더링과 링크 마크업에 그친다. DB 접근 경로, 클라이언트 선택, RLS 정책, 마이그레이션, 워커는 하나도 건드리지 않았다. 공개 위키 경로는 anon 공개 클라이언트와 사이드카 두 테이블만 보는 불변식을 유지한다. 새 링크는 모두 프리페치를 꺼서 세션 방문자에게서 의도치 않은 인증·DB 요청이 생기지 않는다. 대표 실험은 참조가 하나라도 끊기면 판정과 수치 없이 사라지도록 순수 함수에서 한 번만 결정되므로, 지어낸 값이 조용히 노출될 경로가 없다. 그래서 `pass`로 판정한다.
