## Why

`openspec/specs/library-selection-layout/spec.md`는 소스/위키 항목이 "같은 방식으로" 선택→상세 전환되어야 하고 목록으로 돌아가는 경로가 일관돼야 한다고 규정하며, 관련 change(`archive/2026-08-13-unify-source-wiki-selection-layout`)도 완료 표시로 archive되어 있다. 하지만 실제 코드는 `apps/dashboard/components/SourcesList.tsx`(같은 페이지 내 아코디언 펼치기, 상세가 별도 라우트로 이동하지 않음)와 `apps/dashboard/components/WikiLibrary.tsx`(완전히 다른 라우트 `/wiki/[slug]`로 이동)가 서로 다른 상호작용 모델을 쓴다 — 스타일이 아니라 전환 방식 자체가 다르다. Linear HHH-18이 이 증상을 가리킨다.

## What Changes

- `WikiLibrary.tsx`는 이미 스펙을 만족한다 — 행이 실제 라우트(`/wiki/[slug]`)로 이동하고, 그 라우트의 `WikiPageContent`가 `DetailHeader`로 `/wiki` 목록을 가리키는 실제 return 링크를 갖고 있다(`libraryHref`). 문제는 `SourcesList.tsx` 한쪽뿐이다.
- `SourcesList.tsx`의 "상세 보기" 버튼(같은 페이지 내 아코디언 펼치기, `libraryHref="#sources-library"` in-page anchor)을 제거하고, `WikiLibrary`와 동일한 패턴 — 행이 실제 상세 라우트로 이동 — 으로 바꾼다: 신규 라우트 `apps/dashboard/app/w/[workspaceId]/sources/[id]/page.tsx`를 추가하고, 지금 아코디언 안에 있던 `DetailHeader` + `유형/등록일 <dl>`을 그 라우트로 옮긴다. `libraryHref`는 실제 `/sources` 목록 경로를 가리킨다.
- Dropzone·JobStepper는 지금처럼 목록 페이지에 그대로 둔다 (ingestion은 목록 수준의 관심사이지 상세 수준이 아니다).
- 새 의존성은 추가하지 않는다 — 이미 확립된 패턴(WikiLibrary 쪽)을 재사용하는 것으로 충분하다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

없음 — `library-selection-layout` 요구사항 문구는 이미 정확하며 바뀌지 않는다. 이번 change는 그 요구사항을 실제로 충족시키는 구현 갭만 닫는다 (`.openspec.yaml`에 `skip_specs: true` 선언).

## Impact

- `apps/dashboard/components/SourcesList.tsx` (아코디언 제거, 행을 Link로 전환), 신규 `apps/dashboard/app/w/[workspaceId]/sources/[id]/page.tsx`.
- `WikiLibrary.tsx`/`WikiPageContent.tsx`는 변경 없음 — 이미 스펙을 만족.
- 소스 목록(`/sources`) 라우트의 상세 보기 상호작용만 변경 — ingestion, job 처리 로직은 그대로.
- Linear HHH-18 (id `1fe15225-3bd2-4fd3-8020-eb56d40d84a7`).
