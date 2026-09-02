# Tenant Isolation 리뷰 — workspace-home-redesign + wiki-library-redesign r1

- 판정: needs_fix
- 대상: 작업 트리 변경분(base `2f64376c95a0fb50ceeb0182cc41f0ea42b5ae1b`, `main`). `git diff main...HEAD`는 브랜치가 `main`에 있어 비어 있으므로 `git diff`(추적 파일 미커밋 변경분)를 대상으로 삼았다.
- 범위: 두 OpenSpec change를 모두 다룬다 — `openspec/changes/archive/2026-09-02-workspace-home-redesign/`, `openspec/changes/archive/2026-09-02-wiki-library-redesign/`. 두 change의 구현이 같은 파일 집합에 섞여 있어 한 보고서로 판정한다.
- 일시: 2026-09-02T00:00:00+09:00

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 홈·위키 인덱스 서버 페이지 모두 `lib/supabase/server`의 `createClient()`(요청자 쿠키 세션)만 쓴다. `apps/dashboard/app/w/[workspaceId]/page.tsx:120`, `apps/dashboard/app/w/[workspaceId]/wiki/page.tsx:28`. `apps/dashboard/{app,lib,components}` 전체에 `service_role`·`SERVICE_ROLE`·`SECRET_KEY` 참조가 주석 2곳(`wiki/page.tsx:34`, `lib/supabase/server.ts:13`) 외에 없다. 새로 추가된 `source_chunks` 카운트와 `wiki_pages.sources` 컬럼 추가 모두 같은 요청자 클라이언트를 탄다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 이 PR에 마이그레이션이 없다 |
| A-3 | anon 신규 GRANT·정책 | 해당 없음 | SQL 변경 없음. 공개 공유(`0016`) 경로도 건드리지 않았다 |
| A-4 | service_role 코드의 workspace_id 명시 필터 | 해당 없음 | 워커 변경 없음 |
| A-5 | 신규 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | API 라우터·`lib/wiki-publication.ts` 모두 이 PR에서 변경되지 않았다. 일괄 검증·발행·삭제 계약은 그대로다 |
| B-7 | SQLSTATE 42501 → 403 | 해당 없음 | 동일 |
| C-8 | 핸들러 멱등성 | 해당 없음 | 워커·잡 핸들러 변경 없음 |
| C-9 | jobs 직접 UPDATE 금지 | 해당 없음 | `jobs` 접근 코드 변경 없음 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 벡터 검색 경로 변경 없음 |
| D-11 | 색인/질의 토크나이저 일치 | 해당 없음 | FTS 경로 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 시도 | 통과 | 시도 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 프롬프트 변경 없음 |
| D-14 | 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립 경로 변경 없음. `wiki_pages.sources` 길이를 "인용 N개"로 표시할 뿐 컨텍스트를 만들지 않는다 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음(범위 밖 주의 1건) | 이 PR에 마이그레이션 없음. 다만 작업 트리에 미추적 `supabase/migrations/0020_workspace_byok_api_key.sql`이 남아 있고 `0021_source_deletion_integrity.sql`은 이미 `main`에 있다 — 아래 「범위 밖 주의」 참조 |
| 요청 1 | 요청자 세션 사용(신규 `source_chunks`·`sources`) | 통과 | 위 A-1 |
| 요청 2 | 신규 쿼리의 workspace_id 명시 범위 | 통과 | `page.tsx:150-156`이 `.eq("workspace_id", workspaceId)`를 명시하고, `tests/workspace-home.test.tsx`가 `state.chunkWorkspaceId === "ws-1"`로 회귀를 고정한다. `wiki/page.tsx:67,76`의 두 분기도 각각 `.eq("workspace_id", ...)` 유지 |
| 요청 3 | 권한 게이트 회귀(인라인 → 플로팅 바) | 통과 | `WikiLibrary.tsx:374` `showFloatingBulk = canVerify && selectedIds.size > 0`, 렌더 `:721`. 행 체크박스 `:604` `canVerify`, 전체 선택 바 `:558` `canVerify`. 삭제 버튼 `:664` `isOwner` + 핸들러 `:181` 재확인 |
| 요청 4 | 검증 판정 단일 진실 공급원 | 통과 | 홈 `page.tsx:271` `isVerified` 사용, 라이브러리 `WikiLibrary.tsx:240` `isVerified`, 톤 `:249-255` `isVerified`/`isExpiredVerification`, 라벨 `:74` `verificationLabel` 위임. 새 `=== "verified"` 비교가 추가된 곳 없음 |
| 요청 5 | 조용한 실패 | **위반** | `apps/dashboard/app/w/[workspaceId]/page.tsx:150-156`, `:269` — 아래 1번 |

## 조치가 필요한 항목

1. **`source_chunks` 카운트가 PostgREST 행 상한에서 조용히 잘린다** (심각도: 높음)
   - 위치: `apps/dashboard/app/w/[workspaceId]/page.tsx:150-156` (쿼리), `:269` (`const chunkCount = (chunksResult.data ?? []).length;`), 표시 `:326`
   - 깨지는 것: 이 쿼리는 청크 **행 전체를 가져와 JS에서 `.length`를 센다.** PostgREST는 `supabase/config.toml:18`의 `max_rows = 1000`(Supabase 클라우드 기본값도 1000)로 응답 행을 잘라내며, **잘렸다는 사실을 오류로 알리지 않는다.** 청크는 원문 1건당 수십~수백 개가 생기므로 원문 10~30건이면 1000행을 넘긴다. 그 순간부터 홈 벤토 2번 카드는 워크스페이스 청크가 3,000개든 50,000개든 영구히 `인덱싱된 청크 1000개`로 고정된다. 예외도 경고도 없고 테스트는 통과한다(테스트 모의는 상한을 재현하지 않는다) — CLAUDE.md "정합성"이 금지하는 조용한 실패의 전형이다.
   - 부가: `chunksResult.error`를 검사하지 않는다. RLS 거부·네트워크 오류·타임아웃 어느 쪽이든 `data`가 `null`이 되어 `인덱싱된 청크 0개`로 렌더된다. 사용자는 "색인이 안 됐다"로 읽지만 실제로는 조회가 실패한 것이다. 같은 화면의 `sourcesResult`/`pagesResult`/`linksResult`도 동일 패턴이나 그것들은 기존 코드이고, 이번에 새로 들어온 네 번째 쿼리는 **집계 전용**이라 상한 절단이 결과값을 직접 왜곡한다는 점에서 성격이 다르다.
   - 조치: 행을 내려받지 말고 카운트만 받는다. 이 저장소에 이미 같은 관용구가 있다 — `apps/dashboard/components/WorkspaceGeneralSettings.tsx:83`의 `.select("*", { count: "exact", head: true })`. 홈에서도 아래로 바꾼다.
     ```ts
     supabase
       .from("source_chunks")
       .select("id", { count: "exact", head: true })
       .eq("workspace_id", workspaceId),
     ```
     그리고 `chunkCount`는 `chunksResult.count ?? 0`으로 읽되, `chunksResult.error`가 있으면 `0`이 아니라 "집계 불가"를 나타내는 값(예: `null` → 카드에서 `—` 표기)으로 구분한다. `head: true`는 상한 절단을 없애고 최대 1000행 전송도 함께 없애므로 design.md의 [Risk] "`source_chunks` 카운트가 큰 워크스페이스에서 홈 조회를 늘린다"도 같이 해소된다.
   - 회귀 고정: `tests/workspace-home.test.tsx`의 모의에 `select`의 두 번째 인자와 `count`를 반영해, 다시 행 배열 `.length`로 돌아가면 테스트가 깨지게 한다(현재 모의는 `select` 인자를 버리므로 이 회귀를 잡지 못한다).

## 범위 밖 주의

- **미추적 마이그레이션 `supabase/migrations/0020_workspace_byok_api_key.sql`** — 이 PR의 두 change에 속하지 않는 작업 트리 잔여물이다. `0021_source_deletion_integrity.sql`은 이미 `main`에 커밋·적용됐으므로, 0020을 나중에 그대로 커밋하면 **이미 push된 0021보다 앞선 번호가 뒤늦게 들어와** 로컬과 클라우드의 적용 순서가 어긋난다(CLAUDE.md 「정합성」 마지막 항목). 이 PR에 포함시키지 말고, 해당 기능 브랜치에서 번호를 `0022` 이상으로 올린 뒤 진행할 것.
- `apps/dashboard/app/w/[workspaceId]/wiki/page.tsx`의 테스트 모의(`tests/wiki-index-route.test.tsx:31`)는 `eq: () => query`로 컬럼·값을 버린다. 현재 코드에는 `workspace_id` 필터가 있지만, 홈 테스트가 새로 도입한 `chunkWorkspaceId` 방식처럼 필터 인자를 캡처하지 않으면 이 라우트에서 필터가 빠져도 테스트는 통과한다. 이번 변경이 만든 문제는 아니나 같은 형태의 안전망을 여기에도 두는 것이 좋다.

## 판정 근거

테넌트 경계 자체는 이 PR에서 뚫리지 않는다. 새로 추가된 두 조회(`source_chunks` 카운트, `wiki_pages.sources` 컬럼)는 모두 요청자 쿠키 세션 클라이언트를 타고 `workspace_id`를 명시적으로 걸며, `source_chunks_select_member`(`0004_rls_policies.sql:266`)가 뒤에서 한 번 더 막는다. 일괄 검증·발행이 인라인 바에서 하단 플로팅 바로 옮겨졌지만 `canVerify` 게이트가 `showFloatingBulk`에 그대로 실려 있고, 삭제는 `isOwner` 게이트와 핸들러 내부 재확인을 둘 다 유지한다 — 요청받은 "식별자만 옮겨 붙고 게이트가 빠지는" 회귀는 없으며, 오히려 `WikiBulkActions.test.tsx`가 `bulk-verify-btn`/`bulk-publish-btn`이 `canVerify=false`에서 문서에 아예 없음을 새로 단언해 안전망이 강해졌다. 검증률·검증 라벨도 홈·라이브러리·`KnowledgeGrid` 세 화면 모두 `lib/verification-label.ts`에만 의존한다.

그럼에도 `pass`를 줄 수 없는 이유는 하나다. 새로 들어온 `source_chunks` 카운트가 PostgREST `max_rows` 상한에 걸려 **예외 없이 1000에서 멈추고**, 조회 실패 시에는 **0으로 뭉개져** 사용자에게 "청크가 없다"로 보인다. 둘 다 이 저장소가 명시적으로 금지한 "조용히 깨지는" 부류이고, 홈 대시보드는 워크스페이스 색인 상태를 확인하는 유일한 요약 화면이라 잘못된 숫자가 그대로 신뢰된다. 테넌트 경계를 넘지는 않으므로 `blocked`이 아니라 `needs_fix`이며, `count: "exact", head: true`로 바꾸는 국소 수정으로 해결된다.
