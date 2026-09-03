# Tenant Isolation 리뷰 — sources-redesign r1

- 판정: needs_fix
- 대상: working tree diff (HEAD `0b26b55`, 브랜치 `feat/knowledge-grid-design-polish`, 미커밋 상태)
- 일시: 2026-09-03T01:26:37Z

검사 범위(4개 파일, +429/-257):

- `apps/dashboard/components/SourcesList.tsx` (+297/-174)
- `apps/dashboard/app/w/[workspaceId]/sources/loading.tsx` (+87/-83)
- `apps/dashboard/tests/LoadingSkeletons.test.tsx` (+15/-0)
- `docs/design-systems/v2/nexuswiki-design-system.css` (+30/-0, 주석만)

`apps/dashboard/app/w/[workspaceId]/sources/page.tsx`는 diff에 **없다** — 조회 경로가 손대지지 않았다는 주장은 사실이다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 변경 파일 전체에 `service_role`·`SERVICE_ROLE`·`service_client` 문자열 없음. 조회는 `page.tsx:28`의 `createClient()`(`apps/dashboard/lib/supabase/server.ts:24`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` + 요청자 쿠키)와 `SourcesList.tsx:139`의 브라우저 클라이언트뿐. 둘 다 RLS 지배를 받는다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음. 마이그레이션 파일 자체가 diff에 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 해당 없음 | SQL 변경 없음. `0004` 주석대로 `anon`에는 정책이 없고, 이 change는 그 상태를 건드리지 않는다 |
| A-4 | 워커의 명시적 `workspace_id` 필터 | 해당 없음 | 워커 코드 변경 없음 |
| A-5 | 자식 테이블 복합 FK `(id, workspace_id)` | 해당 없음 | 스키마 변경 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음(회귀 없음) | 삭제 호출부 `SourcesList.tsx:148-183`는 HEAD와 **들여쓰기 한 줄을 제외하고 완전 동일**(`isOwner`·`apiFetch`·`ApiError`·`source_in_use` 라인 diff 결과 차이 0). 0행 판정은 API 쪽 책임이고 이 change는 API를 건드리지 않았다 |
| B-7 | SQLSTATE 42501 → 403 | 해당 없음 | API·DB 변경 없음 |
| C-8 | 핸들러 멱등성 / upsert 키 | 해당 없음 | 잡 핸들러 변경 없음 |
| C-9 | `jobs` 직접 UPDATE 금지 | 해당 없음 | `jobs` 접근 코드 없음. 행 단위 진행 표시는 기존 `JobStepper` 재사용(`SourcesList.tsx:619-624`) |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 벡터 검색 경로 변경 없음 |
| D-11 | 색인/질의 토크나이저 일치 | 해당 없음 | 검색은 로컬 문자열 `includes()` 필터(`SourcesList.tsx:184-188`)로 DB tsvector와 무관. HEAD와 동일 |
| D-12 | `search_tsv` 생성 컬럼화 시도 | 해당 없음 | 해당 DDL 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 프롬프트 코드 없음 |
| D-14 | 인용 앵커 보존 | 통과 | 위키 칩은 `wiki_id`가 아닌 `slug` 라우팅(`SourcesList.tsx:578`)을, 청크 열은 `char_start–char_end` 구간(`SourcesList.tsx:604-607`)을 계속 노출한다. 칩 2개 + `+N개 더` 접기(`SourcesList.tsx:520-521`)로 화면에서 사라지는 인용은 소스 상세 라우트가 전량 렌더한다(`app/w/[workspaceId]/sources/[id]/page.tsx:110-133`) — 되짚기 경로가 실제로 존재함을 확인했다 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음. 최대 번호는 여전히 `0021_source_deletion_integrity.sql` |
| 추가-1 | 벤토 지표의 워크스페이스 밖 데이터 노출 | 통과 | 아래 「보조 확인」 참조 |
| 추가-2 | `data-testid` 삭제 계약 보존 | 통과 | 아래 「보조 확인」 참조 |
| 추가-3 | 오류·빈 결과의 조용한 실패 전환 | **위반** | `SourcesList.tsx:325-331`, `348-364` — 삼켜진 조회 오류가 워크스페이스 단위 **단정 문구**로 승격된다 |

### 보조 확인 (호출자 질의에 대한 답)

**조회 경로 무변경.** `git diff --stat`에 `sources/page.tsx`가 없다. 이 파일은 `raw_sources`·`source_chunks`·`wiki_pages`·`workspace_members` 네 조회 모두에 `.eq("workspace_id", workspaceId)`를 걸고 요청자 세션 클라이언트를 쓴다. RLS 정책 `raw_sources_select_member`(`0004_rls_policies.sql:213`)·`wiki_pages_select_member`(:232)·`source_chunks_select_member`(:266)가 그 위에 이중으로 걸린다.

**벤토 지표는 새 데이터를 만들지 않는다.** 다섯 값 모두 이미 내려온 props의 순수 파생이다.

- `citedCount` (`SourcesList.tsx:224-226`) — `citingPages[source.id]`만 읽는다. `citingPages`의 키는 워크스페이스 위키 페이지의 `sources` 배열에서 나오지만, 조회는 `sources` 배열 안 id가 아니라 **소스 목록에 있는 소스 id로만 인덱싱**하므로 다른 워크스페이스 소스의 존재 여부가 새어나갈 수 없다.
- `orphanCount`·`pendingChunkCount`·`citationRate`·`indexingRate` (`SourcesList.tsx:227-236`) — `sources.length`·`indexedCount`·`citedCount`의 산술일 뿐이다.
- 요청자에게 원래 보이던 정보의 재조합이다. 행별 위키 칩과 청크 수는 이전 테이블에도 그대로 있었으므로, 집계로 새로 추론 가능해지는 사실이 없다.

**삭제 경로 보존.** `data-testid`/`data-od-id` 집합을 HEAD와 정렬 비교했을 때 차이 0(`source-management-header`·`upload-open`·`pipeline-stats`·`source-table-section`·`empty-sources-dropzone-container`·`delete-source-btn-${source.id}`·`confirm-delete-source-btn`). `isOwner` 게이트는 버튼 렌더(`SourcesList.tsx:626`)와 핸들러 선두(`:149`) 두 곳 모두 유지된다. `source_in_use` → 한국어 문구 매핑(`:178-181`)도 무변경.

**검증 실행.** `apps/dashboard`에서 `vitest run tests/SourcesList.test.tsx tests/SourceDeletion.test.tsx tests/LoadingSkeletons.test.tsx` → 3 파일 19건 전부 통과. `tsc --noEmit` → 오류 없음.

## 조치가 필요한 항목

1. **삼켜진 조회 오류가 "고아 소스 없음 / 전 소스 청킹 완료"라는 단정으로 승격된다** (심각도: 보통)
   - 위치: `apps/dashboard/components/SourcesList.tsx:325-331`(위키 인용 연결률 칸의 `orphanCount === 0 ? "고아 소스 없음" : ...`), `:348-364`(파이프라인 상태 칸의 `"전 소스 청킹 완료"` 배지와 `"청킹 대기 중인 소스 없음"`)
   - 깨지는 것: `sources/page.tsx`는 세 조회의 `error`를 검사하지 않고 `chunkResult.data ?? []`·`wikiResult.data ?? []`로 흘려보낸다(`page.tsx:78`, `:96`). `raw_sources` 조회는 성공하고 `wiki_pages` 조회만 실패하는 상황(RLS 거부·타임아웃·PostgREST 5xx)에서 `citingPages`가 빈 객체가 되고, 벤토는 이를 **"인용 연결률 0%, 아직 인용되지 않은 소스 N개"** 라는 확정 사실로 표시한다. 사용자에게는 오류가 아니라 "위키 컴파일이 소스를 전혀 참조하지 않았다"로 보이며, 대응은 불필요한 재컴파일이다. 반대로 `source_chunks` 조회가 실패하면 `"청킹 대기 N개"`가 뜬다. 종전 UI는 `<b>{indexedCount}/{sources.length}</b>` 같은 중립 수치만 보여줬으므로, 단정 문구(`"고아 소스 없음"`·`"전 소스 청킹 완료"`·`"청킹 대기 중인 소스 없음"`)는 이 change가 새로 도입한 것이다. 즉 조용한 실패의 표면적이 이 diff에서 넓어졌다. 같은 저장소의 소스 상세 라우트는 이미 `if (chunksResult.error || wikiResult.error)`로 이 경우를 분기 처리하고 있어(`app/w/[workspaceId]/sources/[id]/page.tsx:88-93`) 처리 선례도 있다.
   - 부수 효과: `page.tsx:9`의 `PAGE_SIZE = 50` 때문에 분모 `sources.length`는 워크스페이스 총량이 아니라 **최대 50행 창**이다. 소스가 51개 이상인 워크스페이스에서 51번째 이후가 미청킹·미인용이어도 벤토는 `"전 소스 청킹 완료"`·`"고아 소스 없음"`을 띄운다. 델타 스펙이 "derived from the same workspace data the list itself renders"로 창을 명시적으로 허용하므로 스펙 위반은 아니지만, 단정 문구는 그 창을 넘어서는 주장을 한다.
   - 조치: 둘 중 하나면 충분하다. (a) `page.tsx`에서 `chunkResult.error`·`wikiResult.error`를 `SourcesList`에 `metricsDegraded` 류 boolean으로 내려보내고, 참일 때 해당 칸의 단정 문구를 `"집계를 불러오지 못했습니다"`로 대체한다(소스 상세 라우트와 동일한 처리). (b) 최소 수정으로 가려면 단정 문구를 창 범위를 밝히는 표현으로 바꾼다 — `"고아 소스 없음"` → `"불러온 소스 중 고아 없음"`, `"전 소스 청킹 완료"` → `"불러온 소스 청킹 완료"`. (a)를 권한다. (b)만으로는 위키 조회 실패가 여전히 "연결률 0%"로 보인다.

## 판정 근거

테넌트 경계는 이 diff 어디에서도 흔들리지 않는다. 사용자 요청 경로에 `service_role`이 들어오지 않았고, 유일한 서버 조회 파일은 아예 손대지 않았으며, 새 벤토 지표는 전부 이미 요청자에게 렌더되던 props의 산술 파생이라 워크스페이스 밖 데이터도 요청자에게 숨겨야 할 사실도 노출하지 않는다. 삭제 경로의 `isOwner` 게이트·`data-testid` 계약·`source_in_use` 409 문구 매핑은 들여쓰기 외 바이트 단위로 동일하다. `blocked` 사유(A-1·A-3·A-4)는 하나도 해당하지 않는다.

`pass`를 주지 않는 이유는 D 계열의 조용한 실패 하나뿐이다. 이 change는 "표시 계층만 바꿨다"고 주장하지만, 표시 계층에서 **중립 수치를 단정 문구로 바꾼 것**은 의미론적 변경이다. 상위 `page.tsx`가 조회 오류를 삼키고 있다는 기존 사실과 결합하면, 조회 실패가 사용자에게 오류가 아니라 정상적인 업무 상태(고아 소스 다수·청킹 미완)로 보이게 된다. 데이터가 손상되지는 않고 코드 수정으로 해결되므로 `needs_fix`다. 수정 범위는 `page.tsx`의 error 전달 한 줄과 `SourcesList.tsx` 두 칸의 문구 분기이며, 재리뷰는 r2에서 해당 두 지점만 확인하면 된다.
