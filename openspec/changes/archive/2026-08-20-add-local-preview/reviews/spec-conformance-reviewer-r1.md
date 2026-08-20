# OpenSpec 명세 적합성 리뷰 r1

## 판정

**needs_fix**

## 검토 범위

`origin/main...feat/local-preview-review`의 `/preview` 구현을
`openspec/specs/local-product-preview/spec.md`의 Given/When/Then 계약과 대조했다.

## 근거

- `apps/dashboard/app/preview/layout.tsx`는 `NODE_ENV !== "development"`에서
  `notFound()`를 호출한다. 기존 middleware matcher는 `/preview`를 포함하지 않아
  실서비스 `/w/*` 인증 경로를 변경하지 않는다.
- `apps/dashboard/lib/preview-data.ts`와 `PreviewWorkspace.tsx`는 결정적인 사용자,
  워크스페이스, 소스, 위키, 백로그, 멤버, Ask 답변을 제공하고, 모든 링크를
  `/preview/*`로 유지한다.
- Ask의 위키/원문 인용 버튼은 외부 호출 없이 같은 Ask 화면의 해당 목업 근거를
  전환한다. 업로드·초대·저장·워크스페이스 생성·로그아웃 제어는 한국어
  비저장 안내만 표시한다.

## 발견 사항

1. **[필수] 대표 그래프 데이터가 없다.**
   `local-product-preview`의 “Representative mock workspace exploration”은
   단일 목업 워크스페이스에 source, wiki, **graph**, backlog, member,
   conversation 데이터를 모두 요구한다. 그러나
   `apps/dashboard/lib/preview-data.ts`에는 그래프 노드·엣지 또는 이에 준하는
   그래프 fixture가 없고, `PreviewWorkspace.tsx`도 이를 표시하거나 사용하는
   경로가 없다. 따라서 현 구현은 해당 SHALL을 충족하지 못한다.

   수정 방향: 결정적인 그래프 노드/엣지 fixture를 추가하고, 최소한 미리보기
   홈 또는 명시적인 미리보기 화면에서 검토 가능하게 연결한 뒤 테스트로 보장한다.

## 검증

- `pnpm --dir apps/dashboard test -- PreviewWorkspace.test.tsx preview-layout.test.tsx`
  → 통과: 50 files, 217 tests. (Vitest/Vite 경고와 jsdom navigation 로그만 존재)
- `pnpm --dir apps/dashboard typecheck` → 통과
- `pnpm --dir apps/dashboard lint` → 통과
- `pnpm --dir apps/dashboard build` → 통과
- 단위 테스트 `preview-layout.test.tsx`가 production의 `notFound()` 경계와
  development 렌더링을 확인한다.

그래프 fixture 및 검토 경로가 추가되면 위 필수 항목을 재검토해야 한다.
