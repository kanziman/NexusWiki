# Tenant Isolation 리뷰 — landing-nav-evaluation r1

- 판정: pass
- 대상: 미커밋 작업 트리 `git diff` (기준 HEAD `a79617dba0e7da5a5f61495b5e1db5be37f5a090`). 로컬 `main`이 `origin/main`보다 뒤처져 있어 `git diff main...HEAD`에는 이미 머지된 #279·#280·#286이 섞인다. 그래서 이 change의 실제 변경분인 작업 트리 diff만 검사했다.
- 일시: 2026-11-11T14:11:31Z

## 검사 범위

`git diff --stat` 기준 변경 파일은 2개(+56 / -2)다.

- `apps/dashboard/components/public-landing/PublicLandingHeader.tsx` — 데스크톱·모바일 메뉴에 `/showcase/evaluation`으로 가는 「평가 기록」 `next/link`(`prefetch={false}`)를 추가하고, 데스크톱 `nav` 간격과 `whitespace-nowrap` 클래스를 조정했다
- `apps/dashboard/tests/PublicLandingPage.test.tsx` — 두 메뉴의 링크 순서와 `href`, 모바일 메뉴가 닫히는지 확인하는 테스트 1건을 추가했다

`supabase/`, `apps/api/`, 워커 쪽 변경은 없다. 링크 대상인 `apps/dashboard/app/showcase/evaluation/page.tsx`는 `force-static`이고, 커밋된 JSON(`@/content/evaluation.json` 등)만 읽는다. Supabase 클라이언트를 import하지 않는다. 이 페이지는 이번 diff로 바뀌지 않았다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 해당 없음 | diff에 Supabase 클라이언트 생성·호출이 없다. 링크 대상 페이지도 정적 JSON만 읽는다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음, 마이그레이션 변경 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 해당 없음 | SQL 변경 없음. 새 링크는 정적 공개 페이지로 가는 클라이언트 측 이동일 뿐이고, DB 접근 경로를 새로 열지 않는다 |
| A-4 | 워커의 명시적 `workspace_id` 필터 | 해당 없음 | 워커 코드 변경 없음 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 스키마 변경 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | UPDATE/DELETE 경로 없음 |
| B-7 | `42501` → 403 매핑 | 해당 없음 | 쓰기 경로 없음 |
| C-8 | 핸들러 멱등성 · upsert 키 | 해당 없음 | 작업 핸들러 변경 없음 |
| C-9 | `jobs` 직접 UPDATE 금지 | 해당 없음 | `jobs` 접근 없음 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 벡터 검색 변경 없음 |
| D-11 | 토크나이저 동일성 · `tsv_tokenizer_version` | 해당 없음 | 색인·질의 경로 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 스키마 변경 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 프롬프트 변경 없음 |
| D-14 | LLM 컨텍스트 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립 변경 없음 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 새 마이그레이션 없음. 현재 최대 번호는 `0037_eval_experiments.sql`이다 |

## 조치가 필요한 항목

없음.

## 판정 근거

이번 변경은 공개 랜딩 헤더에 정적 공개 페이지로 가는 링크를 하나 더한 UI 변경이다. DB·API·워커·마이그레이션·프롬프트를 전혀 건드리지 않는다. 링크 대상 `/showcase/evaluation`은 `force-static`이며 커밋된 허용 필드 JSON만 렌더링한다. 따라서 이번 diff로 생기는 새 데이터 접근 경로도, 테넌트 경계를 넘는 경로도 없다. 15개 항목은 전부 해당 없음이다.
