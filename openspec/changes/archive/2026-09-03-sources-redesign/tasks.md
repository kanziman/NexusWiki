## 1. 벤토 메트릭 스트립

- [x] 1.1 `SourcesList`에서 총 등록 원문(포맷별 분해)·총 청크 수·위키 인용 연결률·청킹 완료율 네 지표를 이미 내려오는 `initialSources`·`chunkStats`·`citingPages`에서 산출한다. 새 조회·새 props·새 RPC를 만들지 않고 기존 `isPdf`/`isTextMd` 판정을 재사용한다.
  - Given: 워크스페이스에 포맷이 섞인 소스가 등록되어 있고 일부만 위키에 인용되어 있다
  - When: 멤버가 원문 소스 관리를 연다
  - Then: 네 지표가 로드된 소스 목록·청크 통계·인용 관계와 일치하고, 인용 0건 소스가 있으면 연결률이 100% 미만으로 표시된다
- [x] 1.2 3칸 평면 통계 바(`section.stats`)를 4열 벤토로 교체한다. 색만으로 상태를 전달하지 않도록 각 칸에 수치와 라벨을 텍스트로 함께 둔다. 소스가 0건이면 벤토를 렌더하지 않고 기존 빈 상태 Dropzone 캔버스를 유지한다.
  - Given: 워크스페이스에 소스가 하나도 없다
  - When: 멤버가 화면을 연다
  - Then: 벤토가 나타나지 않고 `data-testid="empty-sources-dropzone-container"`와 승인된 빈 상태 문구가 그대로 보인다

## 2. 세그먼트 툴바 정렬

- [x] 2.1 MIME 필터 탭의 시각을 세그먼트 칩으로 바꾸되 `role="tablist"`·`role="tab"`·`aria-selected`와 탭 이름에 실린 개수(`전체 N`·`PDF N`·`텍스트/마크다운 N`)를 유지하고, 탭과 검색 인풋의 높이를 `.field.search`가 이미 고정한 36px로 맞춰 툴바 위아래 모서리를 일치시킨다. 공용 `.field.search` 규칙은 고치지 않는다.
  - Given: 포맷이 섞인 소스가 등록되어 있다
  - When: 멤버가 필터 탭과 검색창이 놓인 툴바를 본다
  - Then: 두 컨트롤의 위아래 모서리가 일치하고, 탭 클릭 시 해당 포맷만 남으며, 보조기술에는 탭과 선택 상태로 노출된다

## 3. 일체형 카드-로우 컨테이너

- [x] 3.1 6열 `<table>`을 단일 래퍼 컨테이너 안의 5열 CSS Grid 구조(`소스 파일`·`연결된 위키 문서`·`청크 및 좌표`·`파이프라인`·`작업`)로 교체한다. 컬럼 정의를 컨테이너에 한 번만 선언하고 헤더 행과 데이터 행이 그 값을 공유하게 한다. `data-od-id="source-table-section"`을 유지한다.
  - Given: 여러 소스가 렌더링되어 있다
  - When: 멤버가 헤더 라벨과 각 행의 값을 비교한다
  - Then: 모든 행의 값이 자기 헤더 라벨과 같은 컬럼 축에 놓이고, 좁은 뷰포트에서 페이지 가로 스크롤이 발생하지 않는다
- [x] 3.2 소스 파일 열에 포맷 배지(`.format`)·상세 라우트로 가는 제목 링크·메타 라인(크기·수집 유형·상대 시각·절대 일자)을 배치한다. 제목의 `title`/`aria-label` 계약을 유지하고, `byte_size`가 없으면 크기를 자리표시자 없이 생략한다.
  - Given: 크기가 기록된 소스와 기록되지 않은 소스가 함께 있다
  - When: 멤버가 두 행을 본다
  - Then: 전자는 크기를 포함한 메타 라인을, 후자는 크기를 뺀 메타 라인을 보이며 두 행 모두 상대 시각과 절대 일자를 함께 노출한다
- [x] 3.3 인용 위키 열을 한 줄로 고정해 최대 2개 칩(`.doc-chip`)과 `+N개 더` 잔여 표시를 렌더한다. 인용 0건이면 `인용한 위키 없음`을 유지한다.
  - Given: 위키 5편이 인용하는 소스와 1편이 인용하는 소스가 같은 목록에 있다
  - When: 멤버가 목록을 본다
  - Then: 두 행의 높이가 같고, 인용이 많은 행은 칩 2개와 남은 개수 표시를 보여준다
- [x] 3.4 청크·파이프라인·작업 열을 옮긴다. `JobStepper` 폴링, `상세 보기` 링크 이름, `isOwner` 게이트와 `data-testid="delete-source-btn-<id>"`·`data-testid="confirm-delete-source-btn"`, 페이지당 8개 `Pagination`을 그대로 보존한다.
  - Given: 오너와 비오너가 각각 목록을 연다
  - When: 각자 행의 작업 영역을 본다
  - Then: 오너에게만 삭제 버튼이 기존 testid로 노출되고, 상세 보기 링크와 8개 페이지네이션 동작이 이전과 같다
- [x] 3.5 `app/w/[workspaceId]/sources/loading.tsx` 스켈레톤을 새 골격(4열 벤토 + 5열 그리드 카드-로우)으로 맞춘다. 홈·위키 라이브러리 스켈레톤이 세운 형태를 따르고, `LoadingSkeletons.test.tsx`에 같은 종류의 골격 단언을 더한다. `data-testid="sources-loading-skeleton"`과 `aria-busy`는 유지한다.
  - Given: 목록이 벤토와 5열 그리드로 바뀌었다
  - When: 소스 라우트가 로딩 상태에서 렌더 상태로 전환된다
  - Then: 스켈레톤이 옛 3칸 `.stats` 바나 6열 테이블을 그리지 않아 전환에서 레이아웃이 튀지 않는다
- [x] 3.6 집계 조회 실패를 빈 결과와 구분한다. `sources/page.tsx`가 `chunkResult`·`wikiResult`의 `error`를 검사해 실패 사실을 `SourcesList`에 내려보내고, 실패한 집계에 의존하는 벤토 칸과 행 값이 단정 대신 집계 불가를 표시하게 한다. 조회 경로 자체(클라이언트·select 컬럼·`workspace_id` 필터)는 손대지 않는다. 소스 상세 라우트의 기존 분기를 선례로 따른다.
  - Given: 소스 목록은 로드됐지만 위키 인용 집계 조회가 운영 오류를 반환했다
  - When: 멤버가 화면을 본다
  - Then: 인용 지표와 각 행의 인용 값이 "0% · 고아 소스 N개" 같은 단정 대신 집계 불가를 말하고, 실패한 집계에 의존하지 않는 총 등록 원문·포맷 분해는 그대로 보인다

## 4. 검증 및 스펙 아카이브

- [x] 4.1 `apps/dashboard/tests/SourcesList.test.tsx`·`SourceDeletion.test.tsx`·`source-detail-route.test.tsx`를 새 마크업에 맞춰 확인하고, 깨진 단언만 최소 범위로 고친다. table/row/cell role 의존이 없음을 확인한 상태이므로 시맨틱 변경을 이유로 단언을 넓히지 않는다.
  - Given: 목록이 CSS Grid 카드-로우로 바뀌었다
  - When: 세 테스트 파일을 실행한다
  - Then: 빈 상태 문구, 제목 접근성, 상세 보기 링크, MIME 탭 필터, 8개 페이지네이션, 삭제 흐름 단언이 통과한다
- [x] 4.2 `pnpm test`·`pnpm typecheck`·`pnpm lint`와 `openspec validate sources-redesign --strict`를 새로 실행한다. 이전 실행 결과를 재사용하지 않는다.
  - Given: 구현 task가 완료되었다
  - When: 필수 검증을 실행한다
  - Then: skip이나 실패를 성공으로 오인하지 않고 전건 통과를 확인한다
- [x] 4.3 v2 CSS의 `.content.sources` 블록에 어떤 규칙이 아직 살아 있고 어떤 규칙이 이 화면에서 떨어져 나갔는지 실제 사용처를 확인해 주석으로 남긴다. 규칙 자체는 삭제하지 않는다 — 백로그 리디자인 change가 같은 블록을 건드릴 예정이라 두 change가 같은 파일에서 충돌한다.
  - Given: `.stats`·`.table`·`.table-wrap`은 `BacklogList`·`PreviewWorkspace`에 사용처가 남아 있고, `.content.sources .stats`·`.tabs`·`.tab`만 이 change 이후 미사용이 된다
  - When: 다음 사람이 v2 CSS를 읽는다
  - Then: 어느 규칙이 어디서 아직 쓰이는지와, 미사용이 된 규칙을 왜 지금 지우지 않는지가 주석으로 남아 있다
- [x] 4.4 delta spec을 정본에 동기화하고 strict specs validation 후 change를 아카이브한다.
  - Given: 구현과 검증이 완료되었다
  - When: OpenSpec 동기화·아카이브 절차를 실행한다
  - Then: `source-management-wiki` 정본이 이 change의 툴바 정렬·파이프라인 요약·균일 행·행 출처 표시 계약을 보존한다
