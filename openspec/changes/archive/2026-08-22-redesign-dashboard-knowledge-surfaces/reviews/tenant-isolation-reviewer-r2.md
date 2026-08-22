# Tenant Isolation 리뷰 — redesign-dashboard-knowledge-surfaces r2

- 판정: pass
- 대상: r1 수정이 반영된 현재 워킹 트리와 아카이브 계약 (HEAD `c956490`, merge-base `9091823c4780`)
- 일시: 2026-08-22T19:27:28+09:00

## r1 조치 확인

| r1 지적 | 결과 | 근거 |
| --- | --- | --- |
| 청크·인용 위키 조회 오류를 빈 배열로 오표시 | 해결 | `chunksResult.error || wikiResult.error`를 먼저 검사해 서버에 오류를 남기고, 데이터 내용을 포함하지 않는 공통 로드 실패 UI를 반환한다. `error: null`인 성공 결과에서만 `data ?? []`를 정상 empty로 취급한다 |
| source의 operational error를 not-found로 오표시 | 해결 | `.single()`을 `.maybeSingle()`로 바꾸어 정상 0행은 `{ data: null, error: null }`로 일반화된 not-found에 보내고, 실제 `sourceResult.error`는 별도의 generic load-failure 경로로 보낸다 |
| workspace scope·교차 workspace·오류 분기 테스트 부재 | 해결 | 라우트 테스트가 세 테이블의 `workspace_id` 조건, 청크의 `raw_source_id` 조건, unknown/cross-workspace의 동일 not-found, source/chunks/wiki 각 오류의 load failure와 `console.error` 호출을 직접 단언한다 |
| 오류와 정상 empty의 계약 구분 부재 | 해결 | archived delta와 main `source-management-wiki` spec 모두 operational error는 empty collection이 아니라 generic load-failure로 표시하는 시나리오를 포함한다 |

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 `service_role` | 통과 | 소스 상세은 `@/lib/supabase/server`의 요청자 쿠키 세션 `createClient()`만 쓴다. service client/service key 추가가 없다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 마이그레이션·테이블이 없다 |
| A-3 | `anon` 신규 GRANT/정책 | 해당 없음 | SQL·공개 라우트 변경이 없다 |
| A-4 | `service_role`의 `workspace_id` 필터 | 해당 없음 | 워커/service-role 경로 변경이 없다 |
| A-5 | 자식 테이블 복합 FK | 통과 | 기존 `source_chunks(raw_source_id, workspace_id)` 복합 FK가 원문과 청크의 워크스페이스 일치를 DB에서 강제한다 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 신규 UPDATE/DELETE가 없는 SELECT 전용 변경이다. SELECT의 접근 불가/미존재 0행은 정보 누설 없이 같은 not-found로 닫힌다 |
| B-7 | SQLSTATE `42501` → 403 매핑 | 해당 없음 | 신규 쓰기·`WITH CHECK` 경로가 없다 |
| C-8 | 멱등 upsert 키 | 해당 없음 | 신규 저장·잡 핸들러가 없다 |
| C-9 | `jobs` 직접 UPDATE 금지 | 통과 | 상세 화면은 기존 workspace-scoped jobs API를 호출하는 `JobStepper`만 재사용한다 |
| D-10 | 벡터 검색 `strict_order` | 해당 없음 | 검색 경로 변경이 없다 |
| D-11 | 토크나이저 버전 일치 | 해당 없음 | 검색·색인 변경이 없다 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 스키마 변경이 없다 |
| D-13 | 프롬프트 `str.format` | 해당 없음 | 프롬프트 경로 변경이 없다 |
| D-14 | 인용 추적 앵커 | 통과 | Ask citation segment의 위치와 raw/wiki 종류를 유지하고, 소스 상세의 위키 역참조도 현재 source id를 기준으로 제한한다 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션이 없다 |
| F-16 | 조회 실패의 조용한 오표시 | 통과 | source/chunks/wiki 세 오류가 모두 관측 가능한 서버 로그와 generic load-failure UI로 fail-closed하며, 정상 0행만 empty/not-found로 처리된다 |

## 테넌트 경계와 실패 처리 확인

세 SELECT는 모두 같은 요청자 JWT client를 사용하면서 앱 레벨에서도 다음 범위를 명시한다.

- `raw_sources`: `workspace_id = workspaceId`와 `id = id`
- `source_chunks`: `workspace_id = workspaceId`와 `raw_source_id = id`
- `wiki_pages`: `workspace_id = workspaceId`

기존 RLS의 `raw_sources_select_member`, `source_chunks_select_member`, `wiki_pages_select_member`도 각 행의 `workspace_id`에 대한 요청자 멤버십을 다시 검사한다. 따라서 URL의 workspace/source 식별자를 바꾸어도 다른 테넌트 행이 반환되지 않는다. source가 보이지 않으면 `SourceDetailContent`가 생성되지 않으며, unknown source와 같은 not-found 문구만 노출된다.

오류 분기도 정보 누설 없이 닫힌다. 사용자에게는 어느 테이블·SQL·식별자에서 실패했는지 드러내지 않는 동일한 load-failure 문구만 보인다. 상세 오류, workspace id와 source id는 서버의 `console.error`에만 남아 운영상 관측 가능성을 제공한다. 관련 조회 중 하나라도 실패하면 부분 데이터가 클라이언트 props로 전달되지 않는다. 반대로 RLS가 정상적으로 0행을 반환하거나 관계 데이터가 실제로 비어 있을 때는 `error: null`이므로 계약대로 source 본체와 명시적 empty state를 표시한다.

이번 변경에는 UPDATE/DELETE/INSERT/upsert가 없으므로 0행→403, `42501`→403, 멱등 upsert 키 문제를 새로 만들지 않는다. `JobStepper` 재사용도 기존 requester JWT 기반 API 경로를 그대로 사용한다.

## 새 검증

`apps/dashboard`에서 `pnpm test -- tests/source-detail-route.test.tsx`를 실행했다. 현재 Vitest 설정상 전체 suite가 실행되었고 **56 files, 262 tests가 모두 통과**했다. Vite 설정 및 jsdom navigation 경고는 있었지만 테스트 실패는 없었다.

## 조치가 필요한 항목

없음.

## 판정 근거

r1의 `needs_fix` 원인이었던 조용한 조회 실패는 구현·테스트·OpenSpec 계약 세 층에서 모두 닫혔다. requester JWT와 명시적 `workspace_id` scope 및 기존 RLS의 이중 경계가 유지되고, 교차 workspace source는 unknown id와 같은 not-found로 처리된다. operational error는 empty state로 위장되지 않으며 부분 데이터도 노출하지 않고 generic load-failure로 fail-closed한다. 신규 쓰기·마이그레이션·worker 변경이 없어 403 매핑과 멱등성 위험도 추가되지 않았다. 남은 차단 또는 수정 요구가 없어 r2를 `pass`로 판정한다.
