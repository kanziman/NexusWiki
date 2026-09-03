# Tenant Isolation 리뷰 — sources-redesign r2

- 판정: pass
- 대상: working tree diff (HEAD `0b26b55`, 브랜치 `feat/knowledge-grid-design-polish`, 미커밋 상태)
- 일시: 2026-09-03T01:35:36Z

검사 범위(6개 파일, +670/-260):

- `apps/dashboard/app/w/[workspaceId]/sources/page.tsx` (+20/-0) — **r1 이후 신규**
- `apps/dashboard/components/SourcesList.tsx` (+523/-0 기준 재작성)
- `apps/dashboard/tests/SourcesList.test.tsx` (+171/-1) — **r1 이후 신규**
- `apps/dashboard/app/w/[workspaceId]/sources/loading.tsx`
- `apps/dashboard/tests/LoadingSkeletons.test.tsx`
- `docs/design-systems/v2/nexuswiki-design-system.css` (주석만)

델타 스펙 `openspec/changes/sources-redesign/specs/source-management-wiki/spec.md`도 갱신됐다(`Source pipeline summary metrics`에 집계 실패 계약 문단 + `Scenario: A summary aggregate query fails`).

## r1 지적 해소 여부

**해소됨.** r1이 제시한 조치 (a) — 상위 라우트가 error를 boolean으로 내려보내고 해당 칸이 단정 대신 집계 불가를 말한다 — 가 그대로 구현됐다.

- `sources/page.tsx:82-93` — `chunkResult.error` · `wikiResult.error`를 각각 `chunkStatsUnavailable` · `citingPagesUnavailable`로 승격하고, 참일 때 `console.error("소스 목록 집계 조회 실패", { workspaceId, chunkError, wikiError })`로 서버 로그에 남긴다. 소스 상세 라우트의 선례(`sources/[id]/page.tsx:88-103`)와 같은 형태다.
- `SourcesList.tsx:318-334`(생성된 청크) · `:343-363`(위키 인용 연결률) · `:382-410`(파이프라인 상태) — 세 칸 모두 실패 시 `AGGREGATE_UNAVAILABLE`("집계를 불러오지 못했습니다") 단일 문구로 대체된다. r1이 지목한 `"고아 소스 없음"`(`:359`) · `"전 소스 청킹 완료"`(`:400`) · `"청킹 대기 중인 소스 없음"`(`:406`) 세 단정은 전부 `!Unavailable` 분기 안으로 들어갔다. 상태 아이콘 색까지 `!chunkStatsUnavailable && pendingChunkCount === 0`으로 게이트했다(`:375`) — 색만 초록으로 남아 성공을 암시하는 누락이 없다.
- 행 단위도 함께 고쳐졌다. `:614-617` 인용 열이 `"인용한 위키 없음"` 대신 `"인용 정보를 불러오지 못했습니다"`, `:645-648` 청크 열이 `"청크 없음"` 대신 `"집계 불가"`를 낸다. r1은 벤토만 지적했으므로 이는 초과 이행이다 — 행 값도 같은 집계에서 파생되므로 옳은 방향이다.
- 실패한 집계에 의존하지 않는 값(`총 등록 원문` 카드, 포맷 분해 칩 `:302-309`)은 계속 표시된다. 델타 스펙 `spec.md:23`·`:33-35`의 문구와 일치한다.
- 회귀 테스트 `tests/SourcesList.test.tsx` "집계 조회가 실패하면 단정 대신 집계 불가를 표시한다" — `queryByText(/고아 소스/)` · `queryByText(/인용됨 \(/)` 부재를 단언하고, 행 문구 2건과 포맷 분해 잔존까지 확인한다.

**조회 경로·`user_client` 사용 무변경 확인.** `page.tsx`의 신규 20줄은 전부 이미 `await`된 결과 객체를 읽는 순수 로직이다. `createClient()`(`lib/supabase/server.ts` — `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` + 요청자 쿠키) 호출부, 네 조회의 `select`/`.eq("workspace_id", workspaceId)`, `Promise.all` 구성, `PAGE_SIZE` 어느 것도 바뀌지 않았다(diff는 순수 `+20 -0`). 조기 반환도 넣지 않아 실패 시에도 목록 자체는 계속 그려진다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 추가된 라인 전체에 `service_role`·`SERVICE_ROLE`·`service_client`·`createServiceClient` 문자열 없음(diff의 `+` 라인 grep 결과 0건). 서버 조회는 `page.tsx:28`의 요청자 세션 클라이언트, 클라이언트 조회는 `SourcesList.tsx:149`의 브라우저 클라이언트뿐 — 둘 다 RLS 지배 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 마이그레이션·SQL 변경 없음 |
| A-3 | `anon` 신규 GRANT·정책 | 해당 없음 | SQL 변경 없음. `anon`은 여전히 정책 없음(`0004_rls_policies.sql`) |
| A-4 | 워커의 명시적 `workspace_id` 필터 | 해당 없음 | 워커·`apps/api` 코드 변경 없음(working tree에 해당 경로 수정 없음) |
| A-5 | 자식 테이블 복합 FK `(id, workspace_id)` | 해당 없음 | 스키마 변경 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음(회귀 없음) | 삭제 호출부 `SourcesList.tsx:162-200`는 HEAD와 동일. `supabase`·`apiFetch`·`isOwner`·`ApiError`·`data-testid` 라인 diff는 삭제 버튼 블록의 **들여쓰기 4건뿐**(`-551/-560` → `+593/+602`). 0행 판정은 API 책임이고 이 change는 API를 건드리지 않았다 |
| B-7 | SQLSTATE 42501 → 403 | 해당 없음 | API·DB 변경 없음 |
| C-8 | 핸들러 멱등성 / upsert 키 | 해당 없음 | 잡 핸들러 변경 없음. `handleIngested`(`:148-160`)는 단건 재조회 후 로컬 prepend로 무변경 |
| C-9 | `jobs` 직접 UPDATE 금지 | 해당 없음 | `jobs` 접근 코드 없음. 행 진행 표시는 기존 `JobStepper` 재사용(`:669-672`) |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 벡터 검색 경로 변경 없음 |
| D-11 | 색인/질의 토크나이저 일치 | 해당 없음 | 목록 검색은 로컬 `title.toLowerCase().includes()`(`:202-206`)로 DB tsvector와 무관 |
| D-12 | `search_tsv` 생성 컬럼화 시도 | 해당 없음 | 해당 DDL 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 프롬프트 코드 없음 |
| D-14 | 인용 앵커 보존 | 통과 | 위키 칩은 `slug` 라우팅(`:627`), 청크 열은 `char_start–char_end` 구간(`:654-657`)을 유지. 집계 실패 시 좌표가 빠지지만 그때는 값을 지어내지 않고 "집계 불가"를 표시하며, 전량 인용·좌표는 소스 상세 라우트가 계속 렌더한다 |
| D-추가 | r1 지적(집계 실패의 단정 승격) | **해소** | 위 「r1 지적 해소 여부」 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음. 최대 번호는 여전히 `0021_source_deletion_integrity.sql` |
| 추가-1 | 벤토 지표의 워크스페이스 밖 데이터 노출 | 통과 | 다섯 값 모두 이미 내려온 props의 순수 파생. `totalChunks`가 `Object.values(chunkStats)` 전량 합산에서 `sources` 기반 파생으로 바뀌면서(`:225-228`) 오히려 노출면이 좁아졌다 — 목록에 없는 소스(삭제됨·다른 창)의 청크 수가 합계로 새어 나올 경로가 사라졌다 |
| 추가-2 | `data-testid` 삭제 계약 보존 | 통과 | `delete-source-btn-${source.id}`(`:692`) · `confirm-delete-source-btn`(`:816`) · `empty-sources-dropzone-container`(`:496`) · `pipeline-stats`(`:288`) · `source-table-section`(`:438`) · `source-management-header`(`:261`) · `upload-open`(`:273`) 전부 유지 |

### `totalChunks` 파생 변경 검토 (spec-conformance 지적 반영분)

`Object.values(chunkStats).reduce(...)` → `sources.reduce((sum, s) => sum + (chunkStats[s.id]?.count ?? 0), 0)`(`SourcesList.tsx:225-228`).

격리 관점에서 **개선**이다. `chunkStats`는 서버 props라 클라이언트에서 소스를 삭제해도 항목이 남는다. 전량 합산은 화면에 없는 소스의 청크 수를 계속 더해 "행은 사라졌는데 합계는 그대로"인 모순을 만들었고, 이는 삭제된 원문의 존재를 합계 차이로 추론할 수 있는 잔여 신호이기도 했다. 새 파생은 현재 렌더되는 `sources`만 참조하므로 그 신호가 사라진다. 회귀 테스트 "청크 합계는 목록에 남은 소스에서만 파생된다"가 `deleted-source` 항목이 합계에 섞이지 않음을 단언한다.

`indexedCount`(`:229-231`) · `citedCount`(`:238-240`)는 원래부터 `sources` 기반이라 무변경이다.

### 검증 실행 (이번 라운드에서 새로 실행)

- `apps/dashboard`에서 `npx vitest run tests/SourcesList.test.tsx tests/SourceDeletion.test.tsx tests/LoadingSkeletons.test.tsx` → **25 passed / 0 failed**
- `apps/dashboard`에서 `npx tsc --noEmit` → 오류 없음

## 권고 (비차단 — 이번 판정에 반영하지 않음)

1. **50행 창 밖을 향한 단정은 그대로 남아 있다** (심각도: 낮음, 이 change 범위 밖 경계)
   - 위치: `SourcesList.tsx:399-408`("전 소스 청킹 완료" · "청킹 대기 중인 소스 없음"), `:358-360`("고아 소스 없음") · 분모 출처는 `page.tsx:9,35`의 `PAGE_SIZE = 50`
   - 상황: 소스가 51개 이상인 워크스페이스에서 51번째 이후가 미청킹·미인용이어도 요약은 완료를 단정한다. 조회 실패가 아니라 창(window) 때문이다.
   - r1이 조치 (a)/(b) 중 "둘 중 하나면 충분하다, (a)를 권한다"고 명시했고 (a)가 구현됐다. 델타 스펙 `spec.md:21`도 요약을 "derived from the same workspace data the list itself renders"로 정의해 창을 허용한다. 목록·탭 라벨(`전체 50`)도 같은 창을 쓰므로 화면 안에서는 자기모순이 없다. 따라서 이번 판정을 막지 않는다.
   - 후속으로 다룬다면: 문구를 `"불러온 소스 청킹 완료"` 류로 창을 밝히거나, 워크스페이스 단위 `count` 조회를 별도로 하나 둔다.

2. **`raw_sources` 조회 오류는 여전히 검사되지 않는다** (심각도: 낮음, 선재 결함 — 이 diff가 만든 것이 아님)
   - 위치: `page.tsx:30-37` — `const { data } = await supabase.from("raw_sources")...`; `error`를 받지 않는다.
   - 깨지는 것: 이 조회가 실패하면 `sources = []`가 되어 화면이 "아직 등록된 소스가 없습니다" 빈 상태 + 드롭존을 보여준다. 사용자에게는 오류가 아니라 "이 워크스페이스에 원문이 하나도 없다"로 보인다.
   - `main`의 같은 줄과 바이트 단위로 동일하며(확인함), 이번 change의 델타 스펙도 chunk·wiki 집계만 계약한다. 다만 r1이 지적한 것과 정확히 같은 종류의 실패이므로, 세 조회를 같은 규칙으로 다루려면 다음 change에서 정리하는 편이 좋다.

## 판정 근거

r1의 유일한 지적이 권장안 (a)로 정확히 해소됐고, 해소 과정에서 새로 들어온 코드는 `page.tsx`의 순수 파생 20줄과 `SourcesList.tsx`의 조건부 렌더 분기뿐이다. 조회 자체 — 클라이언트 생성, `select` 컬럼, `.eq("workspace_id", …)` 필터, `Promise.all` 구성 — 는 한 글자도 바뀌지 않았으므로 테넌트 경계에 새 표면이 생기지 않았다. `service_role`은 어디에도 들어오지 않았고(A-1), SQL·워커·API 변경이 없어 A-3·A-4를 포함한 `blocked` 사유는 하나도 성립하지 않는다. `totalChunks` 파생 변경은 삭제된 소스의 청크 수가 합계로 남는 모순을 없애 격리 관점에서도 순개선이다. 삭제 경로의 `isOwner` 게이트·`source_in_use` 문구 매핑·`data-testid` 계약은 들여쓰기를 제외하고 무변경이며, 새로 실행한 25건 테스트와 `tsc --noEmit`이 통과한다. 위 「권고」 두 건은 각각 r1이 명시적으로 대안 중 하나로 충분하다고 판단한 잔여분과 `main`에서 그대로 넘어온 선재 결함이라 이번 change의 위반으로 계상하지 않는다. `pass`.
