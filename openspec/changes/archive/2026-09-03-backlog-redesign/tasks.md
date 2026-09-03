## 1. 우선순위 요약 벤토

- [x] 1.1 `BacklogList`에서 미해결 주제 수·영향받는 위키 수·최다 인용 주제·가장 오래 대기 중인 주제 네 지표를 이미 내려오는 `initialItems`에서 산출한다. 동률은 최다 인용이면 `impact` 내림차순 후 `target_slug` 오름차순, 최장 대기면 `first_detected_at` 오름차순 후 같은 규칙으로 결정적으로 깬다. 새 조회·새 RPC를 만들지 않는다.
  - Given: 인용 빈도와 최초 감지 시각이 제각각인 미해결 주제가 있고 최다 인용이 동률인 주제가 둘 이상이다
  - When: 멤버가 지식 공백 화면을 연다
  - Then: 네 지표가 목록과 일치하고, 같은 데이터로 다시 렌더해도 동률 주제의 선택이 바뀌지 않는다
- [x] 1.2 2칸 통계 바(`section.stats`)를 4열 벤토로 교체한다. `aria-label="지식 공백 요약"` region 이름을 유지하고, 각 칸의 수치와 라벨을 텍스트로 함께 둔다. 주제가 0건이면 벤토를 렌더하지 않는다.
  - Given: 워크스페이스에 미해결 주제가 하나도 없다
  - When: 멤버가 화면을 연다
  - Then: 벤토가 나타나지 않고 승인된 빈 상태 문구가 그대로 보인다

## 2. 인용 빈도 세그먼트 필터

- [x] 2.1 필터를 `전체 N`·`다중 인용 N`(`impact >= 2`)·`단일 인용 N`(`impact == 1`) 세 갈래로 늘린다. `role="tablist"`·`role="tab"`·`aria-selected`를 쓰고 탭 이름에 개수를 싣는다. 필터와 검색어가 함께 걸리게 하고, 둘 중 어느 쪽이 바뀌어도 페이지를 1로 되돌린다.
  - Given: 2회 이상 인용된 주제와 1회만 인용된 주제가 섞여 있다
  - When: 멤버가 다중 인용 필터를 고르고 이어서 검색어를 입력한다
  - Then: 두 조건을 모두 만족하는 주제만 남고, 각 탭이 자기 조건에 해당하는 개수를 보여준다
- [x] 2.2 필터 탭과 검색 인풋의 높이를 `.field.search`가 이미 고정한 36px로 맞춰 툴바 위아래 모서리를 일치시킨다. 공용 `.field.search` 규칙은 고치지 않고, 검색 인풋의 `aria-label="지식 공백 검색"`을 유지한다.
  - Given: 미해결 주제가 있어 툴바가 렌더링된다
  - When: 멤버가 필터 탭과 검색창을 본다
  - Then: 두 컨트롤의 위아래 모서리가 일치하고 검색 접근 가능한 이름이 그대로다

## 3. 일체형 카드-로우 컨테이너

- [x] 3.1 5열 `<table>`을 단일 래퍼 컨테이너 안의 5열 CSS Grid(`백로그 주제`·`인용 중인 위키`·`인용 빈도`·`최초 감지`·`해결 액션`)로 교체한다. 컬럼 정의를 컨테이너에 한 번만 선언하고 헤더 행과 데이터 행이 공유한다. `data-od-id="backlog-table-section"`을 유지한다.
  - Given: 여러 주제가 렌더링되어 있다
  - When: 멤버가 헤더 라벨과 각 행의 값을 비교한다
  - Then: 모든 행의 값이 자기 헤더 라벨과 같은 컬럼 축에 놓이고, 좁은 뷰포트에서 페이지 가로 스크롤이 발생하지 않는다
- [x] 3.2 그리드에 `role="table"`·`role="row"`·`role="columnheader"`·`role="cell"`을 얹어 표 시맨틱을 보존한다. 인용 빈도 값에 단위를 텍스트로 함께 둬 라벨 없는 숫자만 남지 않게 한다.
  - Given: 목록이 `<table>` 요소 없이 CSS Grid로 렌더링된다
  - When: 보조기술이 목록을 읽거나 테스트가 `getByRole("table")`·`getAllByRole("row")`로 조회한다
  - Then: 행·열 구조가 노출되고 각 주제의 인용 빈도가 해당 열 헤더와 연관되며, 기존 role 단언이 수정 없이 통과한다
- [x] 3.3 인용 위키 열을 한 줄로 고정해 최대 2개 칩(`.doc-chip`)과 `+N개 더` 잔여 표시를 렌더한다. 인용 0건이면 `인용 문서 없음`을 유지한다. 주제 클릭 시 `BacklogDetailModal`이 열리는 동작과 `title` 속성을 보존한다.
  - Given: 위키 5편이 인용하는 주제와 1편이 인용하는 주제가 같은 목록에 있다
  - When: 멤버가 목록을 본다
  - Then: 두 행의 높이가 같고, 인용이 많은 행은 칩 2개와 남은 개수 표시를 보여준다
- [x] 3.4 최초 감지·해결 액션 열을 옮긴다. `+ 소스 추가` 링크의 `prefillTitle`·`tab=text` 쿼리와 접근 가능한 이름, 페이지당 8개 `Pagination`을 그대로 보존한다. 한 행 안에서 주제 버튼·위키 링크·소스 추가 링크가 서로의 동작을 발화시키지 않게 한다.
  - Given: 한 행에 주제 버튼·인용 위키 링크·소스 추가 링크가 함께 있다
  - When: 멤버가 그중 하나를 조작한다
  - Then: 선택한 컨트롤의 목적지나 패널만 열리고 나머지는 발화하지 않으며, 소스 추가 링크의 쿼리 파라미터가 이전과 같다

## 4. 집계 조회 실패 구분

- [x] 4.1 `backlog/page.tsx`가 `wiki_links`·`wiki_pages` 조회의 `error`를 검사해 실패 사실을 `BacklogList`에 내려보내고 실패를 기록한다. 조회 경로 자체(클라이언트·select 컬럼·`workspace_id` 필터·`to_wiki_id is null` 조건)는 손대지 않는다.
  - Given: 미해결 링크 조회가 운영 오류를 반환했다
  - When: 멤버가 화면을 연다
  - Then: 화면이 백로그를 불러오지 못했음을 알리고, `모든 위키 링크가 정상적으로 연결되어 있습니다`라고 단정하지 않는다
- [x] 4.2 조회가 성공하고 결과가 실제로 비어 있을 때는 기존 `EMPTY_HEADING`·`EMPTY_BODY` 문구를 그대로 보여준다. 승인된 카피를 바꾸지 않는다.
  - Given: 조회가 성공했고 미해결 링크가 없다
  - When: 멤버가 화면을 연다
  - Then: `작성 대기 중인 백로그가 없습니다`와 `모든 위키 링크가 정상적으로 연결되어 있습니다`가 그대로 보인다

## 5. 검증 및 스펙 아카이브

- [x] 5.1 `apps/dashboard/tests/BacklogList.test.tsx`·`backlog-page-route.test.tsx`를 새 마크업에 맞춰 확인한다. `getByRole("table")`·`getAllByRole("row")`·`region name:"지식 공백 요약"`·`textbox name:"지식 공백 검색"` 단언은 유지되어야 하므로, 이들이 깨지면 테스트가 아니라 구현을 고친다. 벤토 지표·필터·칩 상한·조회 실패에 대한 테스트를 새로 추가한다.
  - Given: 목록이 ARIA 역할을 얹은 CSS Grid로 바뀌었다
  - When: 두 테스트 파일을 실행한다
  - Then: 기존 role·어휘 단언이 수정 없이 통과하고, 새 동작에 대한 단언이 함께 통과한다
- [x] 5.2 `pnpm --dir apps/dashboard test`·`typecheck`·`lint`와 `openspec validate backlog-redesign --strict`를 새로 실행한다. 이전 실행 결과를 재사용하지 않는다.
  - Given: 구현 task가 완료되었다
  - When: 필수 검증을 실행한다
  - Then: skip이나 실패를 성공으로 오인하지 않고 전건 통과를 확인한다
- [x] 5.3 `sources-redesign`이 v2 CSS에 남긴 `.content.sources` 사용처 현황 주석에서 `BacklogList` 항목을 실제 상태에 맞게 갱신한다. 규칙 자체는 `PreviewWorkspace`가 계속 쓰므로 삭제하지 않는다.
  - Given: `BacklogList`가 `.table`·`.table-wrap`·`.doc-chips`·`.stats`를 더 이상 쓰지 않는다
  - When: 다음 사람이 v2 CSS를 읽는다
  - Then: 주석의 사용처 목록이 실제 코드와 일치한다
- [x] 5.4 delta spec을 정본에 동기화하고 strict specs validation 후 change를 아카이브한다.
  - Given: 구현과 검증이 완료되었다
  - When: OpenSpec 동기화·아카이브 절차를 실행한다
  - Then: `backlog-ask` 정본이 이 change의 필터·툴바 정렬·균일 행·표 시맨틱·우선순위 요약·조회 실패 구분 계약을 보존한다
