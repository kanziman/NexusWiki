# Tenant Isolation 리뷰 — redesign-dashboard-knowledge-surfaces r1

- 판정: needs_fix
- 대상: 현재 워킹 트리의 `redesign-dashboard-knowledge-surfaces` 구현 및 아카이브 계약 (HEAD `c956490`, merge-base `9091823c4780`)
- 일시: 2026-08-22T19:19:24+09:00

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 `service_role` | 통과 | 신규 소스 상세 라우트는 `@/lib/supabase/server`의 `createClient()`만 사용한다. 이 팩토리는 publishable key와 요청 쿠키로 `createServerClient`를 만들며 요청자 JWT 기준 RLS를 적용한다. 구현 diff에 service client/service key 추가가 없다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 마이그레이션과 신규 테이블 변경이 없다 |
| A-3 | `anon` 신규 GRANT/정책 | 해당 없음 | SQL·공개 라우트 변경이 없다 |
| A-4 | `service_role` 경로의 `workspace_id` 필터 | 해당 없음 | 워커·서비스 역할 코드 변경이 없다 |
| A-5 | 자식 테이블 복합 FK | 통과 | 기존 `source_chunks`는 `(raw_source_id, workspace_id)`가 `raw_sources(id, workspace_id)`를 참조해 청크와 원문의 워크스페이스가 구조적으로 일치한다 (`0002_search_schema.sql`) |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 신규 UPDATE/DELETE가 없는 SELECT 전용 변경이다. 보이지 않는 source SELECT 0행은 계약대로 unknown source와 같은 일반화된 not-found 화면으로 닫힌다 |
| B-7 | SQLSTATE `42501` → 403 매핑 | 해당 없음 | `WITH CHECK`가 동작하는 쓰기 경로가 없다 |
| C-8 | 멱등 upsert 키 | 해당 없음 | 신규 저장·잡 핸들러가 없다 |
| C-9 | `jobs` 직접 UPDATE 금지 | 통과 | 상세 화면은 기존 `JobStepper`를 재사용하며 `jobs`를 직접 수정하지 않는다. 재시도·취소는 기존 API 엔드포인트를 호출한다 |
| D-10 | 벡터 검색 `strict_order` | 해당 없음 | 검색 질의 변경이 없다 |
| D-11 | 토크나이저 버전 일치 | 해당 없음 | 색인·검색 변경이 없다 |
| D-12 | `search_tsv` 생성 컬럼화 | 해당 없음 | 스키마 변경이 없다 |
| D-13 | 프롬프트 `str.format` | 해당 없음 | 프롬프트 경로 변경이 없다 |
| D-14 | 인용 추적 앵커 | 통과 | Ask 변경은 기존 서버 해소 citation segment를 `MarkdownAnswer`에 React 노드로 전달해 마커 위치를 보존한다. 소스 상세도 `raw_source_id`로 wiki `sources` 원장을 대조한다 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션이 없다 |
| F-16 | 관련 조회의 조용한 실패 | **위반** | `chunksResult.error`와 `wikiResult.error`를 검사하지 않고 각각 `data ?? []`로 접어 실제 조회 실패를 정상적인 빈 컬렉션처럼 렌더링한다 |

## 격리 경계 상세 확인

### 요청자 JWT와 워크스페이스 범위

`apps/dashboard/app/w/[workspaceId]/sources/[id]/page.tsx`의 세 조회는 모두 같은 요청자 세션 client를 공유한다. 각 조회에는 다음 앱 레벨 범위가 명시되어 있다.

- `raw_sources`: `.eq("workspace_id", workspaceId).eq("id", id)`
- `source_chunks`: `.eq("workspace_id", workspaceId).eq("raw_source_id", id)`
- `wiki_pages`: `.eq("workspace_id", workspaceId)`

DB도 `raw_sources_select_member`, `source_chunks_select_member`, `wiki_pages_select_member` 정책에서 각각 행 자신의 `workspace_id`를 `is_workspace_member(workspace_id)`로 검사한다 (`0004_rls_policies.sql:213-215`, `232-234`, `266-268`). 따라서 URL의 `workspaceId`나 source id를 다른 테넌트 값으로 바꾸어도 해당 source 행은 RLS에 의해 0행이 되고, 라우트는 관련 데이터가 든 `SourceDetailContent`를 만들지 않고 일반화된 not-found만 반환한다.

청크는 복합 FK 때문에 선택한 source와 같은 workspace에만 존재할 수 있다. 인용 위키는 JSONB `sources`에 DB FK가 없지만, 먼저 `wiki_pages.workspace_id = workspaceId`와 해당 행의 RLS를 통과한 페이지만 메모리에서 필터링한다. 현재 source 자체도 같은 workspace에서 보이는 행이어야 하므로 다른 워크스페이스의 wiki metadata가 props로 섞이는 경로는 없다.

### 403/not-found, 쓰기, 멱등성

이번 변경은 SELECT 전용이므로 RLS에 막힌 UPDATE/DELETE 0행이나 `WITH CHECK`의 `42501`을 새로 매핑할 지점은 없다. 접근 불가 source와 존재하지 않는 source는 같은 문구 `자료를 찾을 수 없습니다`로 처리해 식별자 존재 여부를 누설하지 않는다.

새 저장·큐 핸들러도 없다. 상세 화면에 추가된 `JobStepper`는 이미 소스 목록에서 사용하던 컴포넌트이며, requester JWT를 매 호출마다 붙이는 기존 `apiFetch`를 통해 workspace-scoped jobs API만 호출한다. 따라서 이번 diff가 새 멱등성 키를 요구하거나 `jobs` 직접 UPDATE를 도입하지 않는다.

## 조치가 필요한 항목

1. **청크·인용 위키 조회 실패가 정상적인 빈 상태로 조용히 오표시된다** (심각도: 높음)
   - 위치: `apps/dashboard/app/w/[workspaceId]/sources/[id]/page.tsx`의 `chunksResult.data ?? []`, `wikiResult.data ?? []`
   - 재현 조건: 요청자에게 source는 보이지만 PostgREST/네트워크/스키마 오류 등으로 `source_chunks` 또는 `wiki_pages` 조회가 `{ data: null, error: ... }`를 반환한다.
   - 현재 결과: 오류를 검사하지 않아 UI가 각각 `추출된 청크가 없습니다`, `아직 이 소스를 인용한 위키 문서가 없습니다`라고 표시한다. 사용자는 실제 데이터 부재와 조회 장애를 구분할 수 없고, 원문→청크→위키 추적 관계가 끊겼는데도 정상 empty state로 보인다. 이는 `source-management-wiki`의 “query yields no visible rows” 계약을 “query failed”까지 확장한 것이 아니며, 프로젝트 리뷰 게이트가 명시적으로 찾는 조용한 실패다.
   - 조치: 관련 SELECT의 `error`를 명시적으로 분기한다. RLS가 정상적으로 0행을 반환한 경우(`data: []`, `error: null`)만 빈 상태로 취급하고, 실제 오류는 fail-closed 오류 화면/라우트 오류 경계로 전달하거나 컬렉션별 로드 실패 상태를 명확히 표시한다. 두 오류 경우를 라우트 테스트로 고정한다.

2. **source 조회의 모든 오류가 not-found로 합쳐져 운영 장애도 존재하지 않는 자료처럼 보인다** (심각도: 보통)
   - 위치: 같은 라우트의 `if (sourceResult.error || !sourceResult.data)`
   - 보안상 fail-closed이고 다른 테넌트 정보도 누설하지 않지만, 접근 불가/미존재에 해당하는 0행 오류와 DB·네트워크·스키마 오류를 구분하지 않는다. 후자는 일반화된 로드 실패로 다뤄야 장애가 데이터 부재로 조용히 위장되지 않는다.
   - 조치: PostgREST의 0행 결과만 계약상의 generic not-found로 매핑하고, 그 밖의 오류는 상세 정보 없이 사용자용 로드 실패 또는 오류 경계로 보내며 서버 관측 가능성을 유지한다.

3. **라우트 테스트가 워크스페이스 scope와 오류 분기를 회귀 방지하지 못한다** (심각도: 보통)
   - 위치: `apps/dashboard/tests/source-detail-route.test.tsx`
   - 현재 mock은 `raw_sources.id`만 기록한다. 세 테이블 모두에 정확한 `.eq("workspace_id", workspaceId)`가 걸렸는지, 청크에 `.eq("raw_source_id", id)`가 걸렸는지 검증하지 않는다. 테스트 이름/태스크의 “보이지 않는 소스 fixture”도 실제로는 단순 missing id만 사용하므로 교차 워크스페이스 의도를 직접 고정하지 않는다.
   - 조치: 테이블별 `eq` 호출을 캡처해 scope를 단언하고, 다른 workspace의 source가 generic not-found가 되는 경우 및 1·2번의 오류 케이스를 추가한다.

## 판정 근거

테넌트 격리 자체는 통과한다. 사용자 요청 경로에 `service_role`이 없고, 세 조회 모두 `workspace_id`를 명시하며, 기존 RLS가 요청자 멤버십을 다시 강제한다. 접근 불가 source에서는 관련 props를 렌더하지 않아 교차 테넌트 노출도 없고, 신규 쓰기·마이그레이션·잡 핸들러가 없어 403 쓰기 매핑과 멱등성 계약을 새로 깨뜨리지 않는다. 따라서 사람의 정책 결정이 필요한 `blocked` 사안은 아니다.

그러나 관련 데이터 조회의 실제 오류를 빈 배열로 변환해 “청크 없음/인용 없음”이라고 단정하는 경로는 추적 데이터의 조용한 손실이다. source 본체의 비-0행 오류도 not-found로 합쳐져 같은 문제를 만든다. 둘 다 코드와 테스트로 직접 수정할 수 있고, 수정 뒤 새 검증과 다음 라운드 리뷰가 필요하므로 r1 판정은 `needs_fix`다.
