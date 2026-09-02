# Tenant Isolation 리뷰 — workspace-home-redesign + wiki-library-redesign r2

- 판정: pass
- 대상: 작업 트리 변경분(base `2f64376c95a0fb50ceeb0182cc41f0ea42b5ae1b`, `main`). `git diff main...HEAD`는 브랜치가 `main`에 있어 비어 있으므로 r1과 동일하게 `git diff`(추적 파일 미커밋 변경분)를 대상으로 삼았다.
- 범위: 두 OpenSpec change를 함께 판정한다 — `openspec/changes/archive/2026-09-02-workspace-home-redesign/`, `openspec/changes/archive/2026-09-02-wiki-library-redesign/`
- 일시: 2026-09-02T17:56:38+09:00

## r1 지적 해소 여부

| r1 항목 | 상태 | 근거 |
| --- | --- | --- |
| 1. `source_chunks` 카운트가 PostgREST `max_rows`(1000)에서 조용히 절단 | **해소** | `apps/dashboard/app/w/[workspaceId]/page.tsx:150-158` — `.select("id", { count: "exact", head: true }).eq("workspace_id", workspaceId)`. `head: true`라 응답에 행이 없고 총수는 `Content-Range` 카운트에서 온다. `supabase/config.toml:18`의 `max_rows = 1000`은 행 페이로드에만 걸리므로 절단 경로 자체가 사라졌다. `WorkspaceGeneralSettings.tsx:83`의 기존 관용구와 같은 형태다 |
| 1-부가. `chunksResult.error` 미검사 → 실패가 `0개`로 위장 | **해소** | 같은 파일 `:275-284` — `chunksResult.error`면 `console.error("홈 청크 수 집계 실패", { workspaceId, error })`로 서버 로그를 남기고, `chunkCount`는 `error \|\| typeof count !== "number"`일 때 `null`이 된다. 렌더는 `:341-346`에서 `chunkCount == null ? "인덱싱된 청크 —" : "인덱싱된 청크 N개"` + `tagTone`을 `warning`으로 바꾼다. **`?? 0` 폴백이 코드 어디에도 없다** — 표시 문자열만 갈아 끼우고 실패를 성공처럼 다루는 형태가 아니다 |
| 범위 밖 주의 1. 미추적 `supabase/migrations/0020_workspace_byok_api_key.sql` | **해소(이 PR 기준)** | 여전히 `??`(untracked)이며 커밋 대상에서 제외됐다. 이 PR에는 마이그레이션이 0건이므로 E-15 위반이 성립하지 않는다. 아래 「이월 주의」에 잔여 조건을 남긴다 |
| 범위 밖 주의 2. `tests/wiki-index-route.test.tsx`의 `eq`가 인자를 버림 | **미해소(권고 사항, 위반 아님)** | `apps/dashboard/tests/wiki-index-route.test.tsx:32`는 여전히 `eq: () => query`다. 다만 이번 라운드에서 `select` 컬럼 캡처(`state.wikiPageColumns`)가 추가돼 `sources`·`expires_at` 누락은 잡힌다. 코드 자체의 `workspace_id` 필터는 `wiki/page.tsx:58,67,76,91` 네 곳 모두 살아 있다 |

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `apps/dashboard/{app,lib,components}` 전체에서 `service_role`·`SERVICE_ROLE`·`SECRET_KEY`·`service_client` 참조가 주석 3곳(`app/bookmark-actions.ts:8`, `app/w/[workspaceId]/wiki/page.tsx:34`, `lib/supabase/server.ts:13`)뿐이다. 수정된 청크 카운트도 같은 `createClient()`(요청자 쿠키 세션) 배열 안에 있다 — 별도 클라이언트를 새로 만들지 않았다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 이 PR에 마이그레이션이 없다(`git status supabase/migrations`는 미추적 0020 하나뿐이며 커밋 제외) |
| A-3 | anon 신규 GRANT·정책 | 해당 없음 | SQL 변경 0건. 공개 공유(`0016`) 경로 무변경 |
| A-4 | service_role 코드의 workspace_id 명시 필터 | 해당 없음 | 워커(`apps/worker`) 변경 0건 |
| A-5 | 신규 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | `apps/dashboard/lib/wiki-publication.ts`와 API 라우터는 이 PR에서 변경되지 않았다(`git status`에 없음). `WikiLibrary.tsx:302,340`의 일괄 핸들러는 기존 서버 액션을 그대로 호출한다 |
| B-7 | SQLSTATE 42501 → 403 | 해당 없음 | 동일 |
| C-8 | 핸들러 멱등성 | 해당 없음 | 잡 핸들러 변경 없음 |
| C-9 | jobs 직접 UPDATE 금지 | 해당 없음 | `jobs` 접근 코드 변경 없음 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 벡터 검색 경로 변경 없음 |
| D-11 | 색인/질의 토크나이저 일치 | 해당 없음 | FTS 경로 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 시도 | 통과 | 시도 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 프롬프트 변경 없음 |
| D-14 | 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립 경로 변경 없음. `wiki_pages.sources`는 길이만 배지·칩 정렬에 쓴다 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 커밋 대상 마이그레이션 0건 |
| 요청 1 | r1 지적 실제 해소 | 통과 | 위 표 1·1-부가 |
| 요청 2 | 수정이 새 문제를 만들지 않음 | 통과 | `page.tsx:158`이 `.eq("workspace_id", workspaceId)`를 그대로 유지하고, 요청자 세션 클라이언트(`page.tsx:120 createClient()`)의 `Promise.all` 배열 안에 그대로 있다. 새 RPC·새 클라이언트·새 fetch가 추가되지 않았다(diff의 추가 라인 중 `.from(`은 기존 4개 조회의 재들여쓰기 + `source_chunks` 하나뿐) |
| 요청 3 | 추가 테스트가 실제 회귀를 고정 | 통과 | 아래 「회귀 고정 검증」 |
| 요청 4 | r1 pass 항목 재확인 | 통과 | 아래 「r1 pass 항목 재확인」 |

## 회귀 고정 검증

새 테스트가 통과만 시키는 형태인지 확인하기 위해 **의도적 회귀를 주입해 실패를 확인했다**(검사 후 원본 복원, `diff` 바이트 동일 확인).

- 주입: `page.tsx`의 `.select("id", { count: "exact", head: true })` → `.select("id")`, `chunkCount` 계산 → `(chunksResult.data ?? []).length`
- 결과: `tests/workspace-home.test.tsx` **8건 중 4건 실패**(`인덱싱된 청크 2500개` 미표시, `chunkSelectOptions` 불일치, 오류 시 `1개` 표시, count 부재 시 `1개` 표시)
- 복원 후 재실행: 8건 전부 통과. 관련 4개 파일(`workspace-home`, `wiki-index-route`, `WikiBulkActions`, `WikiLibrary`) 24건 전부 통과

모의 설계도 확인했다. `tests/workspace-home.test.tsx:60-76`은 `head: true`일 때만 `data`를 비우고 그렇지 않으면 행 배열을 그대로 돌려주므로, 행 기반 집계로 되돌아가면 카운트 헤더(2500)와 행 수(1000)가 어긋나 반드시 깨진다. 실패 케이스는 `error`와 `count: null` 두 갈래를 따로 덮고, 각각 `0개`·`1개` 표기가 **없음**을 단언해 "0으로 뭉개기"와 "행 수로 대체하기" 양쪽을 막는다.

r1이 확인했던 기존 단언은 약화되지 않았다. `state.chunkWorkspaceId === "ws-1"` 단언은 오히려 5개 테스트로 늘었고(`:139,181,378,394` 등), `wikiSelect` 컬럼 캡처 회귀 테스트(`disputed`·`expires_at`)도 그대로 남아 있다.

## r1 pass 항목 재확인

- 플로팅 바 `canVerify` 게이트: `WikiLibrary.tsx:374` `const showFloatingBulk = canVerify && selectedIds.size > 0;`, 렌더 `:722`. 행 체크박스 `:604`, 전체 선택 바 `:558`, 핸들러 내부 재확인 `:303`·`:342` 모두 `canVerify` 유지
- `isOwner` 삭제 게이트: 버튼 `:664`, 핸들러 `:181` `if (!deleteTarget || deleting || !isOwner) return;` 유지
- `verification-label.ts` 단일 진실 공급원: `WikiLibrary.tsx:26-27,75,121,237-240`과 홈 `page.tsx:289` 모두 `isVerified`/`verificationLabel` 경유. 이번 수정으로 홈에 새로 들어온 `verificationRate`도 `isVerified(page)`로 센다 — `=== "verified"` 직접 비교는 두 파일 어디에도 없다

## 이월 주의(이번 PR 위반 아님)

- **`supabase/migrations/0020_workspace_byok_api_key.sql`** — 커밋 제외로 이 PR의 E-15 우려는 해소됐다. 다만 `0021_source_deletion_integrity.sql`이 이미 `main`(`2f64376`)에 있으므로, BYOK 브랜치에서 이 파일을 커밋할 때 번호를 `0022` 이상으로 올려야 한다. 0020 그대로 나가면 로컬과 클라우드의 적용 순서가 어긋난다
- **미추적 프리뷰 HTML 3종**(`apps/dashboard/public/redesign-preview.html`, `apps/dashboard/public/wiki-library-preview.html`, `docs/design-systems/dashboard-redesign-preview.html`) — 커밋 제외 결정으로 `public/`에 인증 없이 노출되는 표면은 생기지 않는다. `docs/design-systems/dashboard-redesign-plan.md`에서도 `file:///Users/zorba/...` 참조가 전부 사라졌음을 확인했다(저장소 전체 grep 결과 커밋 대상 파일에 `file:///` 잔여 없음). 다만 세 파일이 작업 트리에 남아 있으므로 `git add -A`로 우발 커밋되지 않게 주의한다
- **`apps/dashboard/app/w/[workspaceId]/sources/page.tsx:53-59`** — 이 PR에서 변경되지 않은 기존 코드지만, `source_chunks` 행을 그대로 받아 JS에서 매핑한다. 원문당 청크가 쌓이면 `max_rows = 1000`에 걸려 소스별 청크 수가 조용히 줄어든다. `design.md` D-3이 "이 패턴을 재사용한다"고 적었으나 실제 구현은 더 안전한 `count/head` 방식을 택했다 — 반대 방향의 동기화(소스 목록을 고치는 일)는 별도 change로 다룰 것
- `tests/wiki-index-route.test.tsx:32`의 `eq: () => query`는 여전히 컬럼·값을 버린다. 위키 인덱스 라우트에서 `workspace_id` 필터가 빠져도 이 테스트는 통과한다. 홈 테스트가 쓰는 인자 캡처 방식을 같이 두는 것을 권한다

## 판정 근거

r1에서 유일한 `needs_fix` 사유였던 조용한 실패 2종이 모두 실제로 닫혔다. 절단 경로는 `count: "exact", head: true`로 사라졌고(행을 아예 받지 않으므로 `max_rows`가 결과값에 개입할 수 없다), 실패는 `null` → `—` + `warning` 톤 + 서버 로그로 **0과 구분되어** 표면화된다. 표시 문자열만 바꾸고 실패를 성공으로 다루는 형태가 아님을 코드(`?? 0` 폴백 부재)와 주입 회귀 실험(4건 실패) 양쪽으로 확인했다.

수정은 테넌트 경계에 새 표면을 만들지 않았다. 청크 조회는 여전히 요청자 쿠키 세션 클라이언트를 타고 `.eq("workspace_id", workspaceId)`를 명시하며, `source_chunks_select_member`(`0004_rls_policies.sql:266`)가 뒤에서 한 번 더 막는다. `head: true`는 RLS 판정 이후의 카운트를 돌려주므로 타 워크스페이스 행이 총계에 섞이지 않는다. 마이그레이션·워커·API·검색·프롬프트 경로는 이 PR에서 전혀 건드리지 않아 A-2~A-5, B, C, D-10~D-14는 해당 없음이다. r1이 통과로 본 권한 게이트 3종도 이번 수정으로 흔들리지 않았고, 커밋 범위 우려(미추적 마이그레이션·프리뷰 HTML·절대경로 링크)는 제외 결정과 문서 정리로 이 PR 안에서는 성립하지 않는다. 따라서 `pass`다.
