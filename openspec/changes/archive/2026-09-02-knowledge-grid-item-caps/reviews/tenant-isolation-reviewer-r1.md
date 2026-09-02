# Tenant Isolation 리뷰 — knowledge-grid-item-caps r1

- 판정: needs_fix
- 대상: `git diff origin/main` (working tree, base `b274d46` — HEAD == merge-base라 변경분 전부 미커밋 상태)
- 일시: 2026-09-02T13:15:01Z

검사 범위(4파일):

- `apps/dashboard/components/KnowledgeGrid.tsx` (+106 −60)
- `apps/dashboard/tests/KnowledgeGrid.test.tsx` (+17 −7)
- `openspec/specs/workspace-home-dashboard/spec.md` (+6 −2)
- `docs/design-systems/wiki-library-redesign-plan.md` (+4 −2)

`git diff origin/main --name-only -- supabase apps/api` = 0. 마이그레이션 · RLS · API · 워커 변경 없음을 확인했다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 해당 없음 | 이 diff에 데이터 접근 코드 없음. 이 컴포넌트에 데이터를 공급하는 `apps/dashboard/app/w/[workspaceId]/page.tsx:120`은 `@/lib/supabase/server`의 요청자 세션 `createClient()`를 쓰며 diff에 포함되지 않음. 저장소 전체에 `service_client` 사용 흔적 없음 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블 없음. `supabase/migrations` 최신은 `0021_source_deletion_integrity.sql`이며 이 diff는 건드리지 않음 |
| A-3 | anon 신규 GRANT/정책 | 해당 없음 | SQL 변경 없음. `/preview` 경로는 DB를 읽지 않고 `lib/preview-data.ts` 정적 픽스처를 쓴다 |
| A-4 | service_role 코드의 workspace_id 필터 | 해당 없음 | 워커 변경 없음 |
| A-5 | 신규 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 이 diff에 쓰기 경로 없음. 컴포넌트는 읽기 전용 렌더링 |
| B-7 | SQLSTATE 42501 → 403 | 해당 없음 | 동일 |
| C-8 | 핸들러 멱등성 | 해당 없음 | 잡 핸들러 변경 없음 |
| C-9 | jobs 직접 UPDATE 금지 | 해당 없음 | `jobs` 접근 없음 |
| D-10 | hnsw.iterative_scan | 해당 없음 | 벡터 검색 변경 없음 |
| D-11 | 색인/질의 토크나이저 일치 | 해당 없음 | 검색 경로 변경 없음 |
| D-12 | search_tsv 생성 컬럼화 시도 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 `str.format` | 해당 없음 | 프롬프트 변경 없음 |
| D-14 | 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립 변경 없음 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음 |
| 요청 1 | 검증 판정 단일 진실 공급원 | 통과 | `KnowledgeGrid.tsx:117,124`가 `isVerified` / `isExpiredVerification`만 쓴다. 저장소 전체 `verification_status ===` 검색 결과 신규 직접 비교 0건(`lib/verification-label.ts` 내부 정의 외 전부 ⚠️ 주석뿐) |
| 요청 1' | 검증 **톤** 매핑 단일 진실 공급원 | 위반 | `KnowledgeGrid.tsx:139-147` 인라인 삼항이 `WikiLibrary.tsx:118-125` `verificationToneClass`를 복제 (아래 1번) |
| 요청 2 | 충돌·만료 표면화 | 통과 | 상태 span이 조건 없이 항상 렌더된다(구버전은 `verified \|\| disputed \|\| expired` 게이트). 충돌→`--danger`, 만료→`--warning`, 검증→`--good`, 그 외 muted. `CheckCircle2`는 `isVerified`일 때만 붙어 충돌·만료 문서에 체크 아이콘이 새지 않는다. 네 토큰 전부 `docs/design-systems/v2/nexuswiki-design-system.css:44-60`에 실재하며, Tailwind 4.3.3이라 `/10`·`/25`·`/80` 불투명도 수식어도 color-mix로 컴파일된다 |
| 요청 3 | 상한 축소의 정보 은폐 | 부분 위반 | 헤더 카운트 칩이 잘린 수가 아니라 **전체 수**(`filteredPages.length` / `backlogItems.length`)를 그대로 보여줘 "데이터 없음" 오인은 막힌다. 전용 라우트 `app/w/[workspaceId]/wiki/page.tsx`·`backlog/page.tsx` 둘 다 실재하고 테스트가 href를 단언한다. 다만 백로그 열의 탈출구 라벨이 "전체 보기"→"보완하기"로 바뀌었다 (아래 3번) |
| 요청 4 | 워크스페이스 범위 | 통과 | 상한은 `slice`뿐이고 데이터 경계에 손대지 않았다. 서버는 `raw_sources`·`wiki_pages`·`wiki_links`·`source_chunks` 네 쿼리 전부 `.eq("workspace_id", workspaceId)`를 요청자 세션으로 건다(`page.tsx:129,143,147,157`) |
| 요청 5 | 빈 상태 / 오류 상태 구분 | 미해결(이 diff 밖) | 컴포넌트는 빈 배열만 받으므로 구분할 수단이 없다. 상위 `page.tsx:160,190`이 `?? []`로 오류를 빈 배열에 접는다 (아래 4번) |
| 검증 실행 | 테스트 · 타입 · 스펙 | 통과 | `vitest run tests/KnowledgeGrid.test.tsx tests/verification-label.test.tsx` → 11 pass / 0 fail. `tsc --noEmit` → 오류 없음. `openspec validate workspace-home-dashboard --strict` → valid |

## 조치가 필요한 항목

1. **검증 상태 색상 매핑이 두 컴포넌트에 복제됐다** (심각도: 높음)
   - 위치: `apps/dashboard/components/KnowledgeGrid.tsx:139-147` ↔ `apps/dashboard/components/WikiLibrary.tsx:118-125`
   - 깨지는 것: 이번 리디자인이 `.badge` / `.badge.verified` 클래스를 버리고 인라인 삼항으로 색을 정한다.
     ```tsx
     disputed ? "text-[var(--danger)]"
       : expired ? "text-[var(--warning)]"
         : verified ? "text-[var(--good)]" : "text-[var(--muted)]"
     ```
     이는 `WikiLibrary.tsx`의 `verificationToneClass`와 현재는 결과가 동일하지만(네 술어가 상호 배타라 순서 차이도 무해하다), 매핑이 두 곳에 산다. 한쪽만 고치는 순간 같은 `disputed` 문서가 라이브러리에서는 빨강, 홈에서는 회색이 된다 — 예외도 테스트 실패도 없이 조용히 갈라진다. `lib/verification-label.ts` 헤더가 "컴포넌트가 라벨 문자열을 직접 들고 있으면 안 된다"고 못박은 바로 그 사고가 실제로 한 번 났고(`검증 완료` vs `검증됨`), 이번엔 라벨 대신 **색**이 같은 자리를 차지했다. 색은 신뢰 상태를 읽는 첫 신호라 라벨보다 먼저 눈에 들어온다.
   - 조치: `verificationToneClass`를 `apps/dashboard/lib/verification-label.ts`로 옮기고 `WikiLibrary.tsx`와 `KnowledgeGrid.tsx` 양쪽이 import한다. `CheckCircle2` 게이트(`isVerified`일 때만)도 같은 모듈의 술어를 계속 쓰게 둔다.

2. **`/preview` 홈이 실제 홈과 갈라졌다 — 명시적으로 금지된 드리프트다** (심각도: 보통)
   - 위치: `apps/dashboard/components/PreviewWorkspace.tsx:247-296` (변경 없음) ↔ `KnowledgeGrid.tsx:78-283` (변경됨)
   - 깨지는 것: `PreviewWorkspace.tsx:247-250` 주석은 "클래스를 포크하면 미리보기가 실제 홈과 서서히 갈라져 '대표성 있는 미리보기'가 조용히 무너진다"고 적고 그래서 `.sections`를 공유한다. 이번 diff는 클래스를 포크하지 않은 대신 **홈 쪽 행 마크업 전체**를 `.doc` / `.doc-list` / `.doc-body` / `.doc-meta` / `.section-head` / `.source-line`에서 인라인 카드로 갈아치웠다. 미리보기는 여전히 옛 클래스를 쓰므로, 로그인 전 사용자가 보는 `/preview`는 제품에 더 이상 존재하지 않는 레이아웃이다. 주석이 막으려던 결과가 다른 경로로 그대로 일어났다. 컴파일도 테스트도 통과하므로 아무도 알려주지 않는다.
   - 조치: `PreviewWorkspace`의 지식 그리드 블록을 같은 카드 마크업으로 맞추거나, 최소한 `PreviewWorkspace.tsx:247` 주석을 갱신해 "홈은 인라인 카드로 이전했고 미리보기는 의도적으로 남긴다"는 결정을 근거와 함께 남긴다. 주석이 지키지 못하는 불변식을 계속 주장하게 두면 다음 사람이 그것을 믿는다.

3. **백로그 열의 탈출구 라벨이 "전체 보기"에서 "보완하기"로 바뀌었다 — 상한을 절반으로 줄인 커밋에서** (심각도: 보통)
   - 위치: `apps/dashboard/components/KnowledgeGrid.tsx:195`(섹션 제목), `:206-212`(링크 라벨)
   - 깨지는 것: 백로그 상한이 8→4로 줄어 숨겨지는 항목이 두 배가 됐는데, 남은 항목에 도달하는 **유일한** 링크의 라벨이 "전체"라는 말을 잃었다. 위쪽 위키 열은 여전히 "전체 보기"라, 같은 화면의 나란한 두 열이 같은 성격의 컨트롤을 다르게 부른다 — `openspec/specs/dashboard-design-consistency/spec.md:33,62`의 "Shared state and control language"가 막으려는 형태다. 섹션 제목도 "지식 공백 (작성 대기 백로그)"로 바뀌어, LNB(`WorkspaceSidebar.tsx:343,350`) · 목적지 h1(`BacklogList.tsx:72`) · 브레드크럼(`WorkspaceShell.tsx:31`)이 모두 "미완성 백로그"라 부르는 목적지에 세 번째 이름이 생겼다(직전 이름 "작성 대기 백로그"와의 불일치는 이 diff 이전부터 있었다 — 이번 변경이 악화시킨 것이지 만든 것은 아니다).
     새 테스트(`KnowledgeGrid.test.tsx:172-179`)는 `href`만 단언하므로 라벨이 무엇으로 바뀌어도 통과한다.
   - 조치: 백로그 링크 라벨을 "전체 보기"로 되돌리거나, 두 열 모두 같은 규칙("전체 보기" 또는 "N개 더 보기")으로 통일한다. 섹션 제목은 목적지 이름 "미완성 백로그"에 맞춘다. 통일한 라벨을 테스트에서 함께 단언해 다음 리스타일이 조용히 되돌리지 못하게 한다.

## 관찰 — 이 diff 밖 (판정에 반영하지 않음)

4. **목록 쿼리 실패가 빈 상태로 위장된다** (심각도: 높음, 선재 결함)
   - 위치: `apps/dashboard/app/w/[workspaceId]/page.tsx:160`(`sourcesResult.data ?? []`), `:161`(`pagesResult.data ?? []`), `:189`(`linksResult.data ?? []`)
   - 깨지는 것: `wiki_pages` 조회가 실패하면(RLS 거부, 네트워크, PostgREST 오류) `?? []`가 이를 빈 배열로 접고, 홈은 이번 diff가 점선 테두리로 더 또렷하게 만든 "컴파일된 위키 문서가 아직 없습니다."를 띄운다. 사용자는 워크스페이스가 비었다고 읽는다. 같은 파일 `:262-270`은 `chunksResult`에 대해 정확히 이 위험을 ⚠️ 주석으로 적어 두고 `error`를 검사해 `null`로 구분하는데, 목록 세 개는 같은 처리를 받지 않는다.
   - 이 diff는 `page.tsx`를 건드리지 않았고 빈 상태 문구도 그대로다. 다만 이번 리디자인이 그 빈 상태의 시각적 확신도를 올렸으므로 함께 기록한다. 조치: 세 결과의 `error`를 검사해 빈 상태와 오류 상태를 다른 문구로 분기한다.

## 판정 근거

테넌트 경계는 이 diff에서 어디도 움직이지 않았다. SQL·API·워커 변경이 0이고, 상한은 순수 클라이언트 `slice`이며, 데이터를 공급하는 서버 컴포넌트는 여전히 요청자 세션 + `workspace_id` 명시 필터를 쓴다. `service_role`은 등장하지 않는다. 검증 상태 **판정**도 요청대로 `lib/verification-label.ts`의 세 함수에만 의존하며, 오히려 배지 게이트가 사라져 충돌·만료·미검증이 이전보다 더 넓게 표면화된다 — 요청 1·2·4는 통과다.

그럼에도 `pass`를 주지 않는 이유는 이 리디자인이 **조용히 갈라지는 지점을 세 개 새로 만들었기** 때문이다. 색상 매핑 복제(1번)는 이 저장소가 이미 한 번 겪고 모듈 헤더에 못박아 둔 목적지별 상태 표현 드리프트의 재발 조건이고, 미리보기 마크업 드리프트(2번)는 코드 주석이 명시적으로 금지한 결과가 다른 경로로 실현된 것이며, 백로그 탈출구 라벨 변경(3번)은 하필 그 탈출구의 중요도가 두 배로 커진 커밋에서 일어났다. 셋 다 예외를 던지지 않고 테스트를 통과하며 — 이 리뷰가 보는 종류의 결함이다. 다만 셋 다 국소적 코드 수정으로 해결되고 테넌트 경계를 넘지 않으므로 `blocked`이 아니라 `needs_fix`다.
