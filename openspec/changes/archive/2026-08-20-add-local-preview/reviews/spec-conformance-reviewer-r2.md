# OpenSpec 명세 적합성 리뷰 r2

## 판정

**pass**

## 검토 범위

r1의 필수 수정 사항을 포함해 `origin/main...feat/local-preview-review`의
`/preview` 구현을 `openspec/specs/local-product-preview/spec.md`와 재대조했다.

## 근거

- `app/preview/layout.tsx`는 development 외 환경에서 `notFound()`를 호출하며,
  기존 `/w/*` 인증 middleware 경로를 변경하지 않는다.
- `preview-data.ts`는 결정적인 사용자, 워크스페이스, 소스, 위키, 백로그,
  멤버, Ask 대화와 함께 `previewGraph`의 4개 노드·4개 연결을 제공한다.
  홈 화면은 이 그래프 요약과 노드 라벨을 렌더링한다.
- preview 내비게이션과 문서 링크는 `/preview/*`를 유지하고, Ask 인용은 외부
  요청 없이 같은 Ask 화면에서 일치하는 위키 또는 원문 근거를 전환한다.
- 업로드·초대·저장·워크스페이스 생성·로그아웃 제어는 외부 요청 대신 한국어
  비저장 안내를 표시한다.

## 발견 사항

없음. r1의 그래프 fixture 부재는 `previewGraph` fixture와 홈 화면 요약 및
회귀 테스트로 해소되었다.

## 검증

- `pnpm --dir apps/dashboard test -- PreviewWorkspace.test.tsx preview-layout.test.tsx`
  → 통과: 50 files, 217 tests
- `pnpm --dir apps/dashboard typecheck` → 통과
- `pnpm --dir apps/dashboard lint` → 통과
- r1에서 실행한 `pnpm --dir apps/dashboard build` → 통과
- `PreviewWorkspace.test.tsx`는 그래프 요약(`4개 노드 · 4개 연결`) 렌더링을
  확인하고, `preview-layout.test.tsx`는 development 렌더링과 production
  not-found 경계를 확인한다.
