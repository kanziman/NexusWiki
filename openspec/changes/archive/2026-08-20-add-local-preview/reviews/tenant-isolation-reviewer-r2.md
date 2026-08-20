# 테넌트 격리 리뷰 r2

## 판정: pass

## 범위

r1 이후 추가된 지식 그래프 fixture·홈 렌더링 변경을 포함해 `origin/main...feat/local-preview-review`와 현재 작업 트리를 재검토했다. 확인 대상은 테넌트 데이터 경계, production 차단, 외부 읽기·쓰기 부작용이다.

## 근거

- 그래프 추가분은 `apps/dashboard/lib/preview-data.ts:117-130`의 정적 `nodes`·`links` fixture와 `PreviewWorkspace.tsx:232-247`의 개수·라벨 렌더링으로만 구성된다. 이벤트 핸들러, 라우터 이동, 네트워크·Supabase 접근이 없다.
- preview 모듈 import(`PreviewWorkspace.tsx:18-27`)는 fixture와 UI 라이브러리뿐이다. preview 경로·컴포넌트·fixture에서 `fetch`, Supabase client, API client, RPC, Storage, `signOut` 호출을 재검색했으며 결과는 없다.
- 기존 쓰기성 제어는 여전히 `setNotice`/`onAction`만 실행하고 비저장 안내(`PreviewWorkspace.tsx:72-80`)를 표시한다. 그래프 변경은 이 동작 경로를 건드리지 않는다.
- `app/preview/layout.tsx:8-16`는 development 외 환경에서 `notFound()`를 호출한다. `/w/**` 인증 middleware·워크스페이스 RLS 경로에는 이번 변경이 없다.

## 지적 사항

없음. 그래프 식별자는 정적 목업 slug이며 실제 workspace ID, 사용자 JWT, API URL 또는 접근 토큰을 포함하지 않는다.

## 검증

- `pnpm test -- PreviewWorkspace.test.tsx preview-layout.test.tsx` (작업 디렉터리: `apps/dashboard`): 50 파일, 217 테스트 통과. 그래프 요약 렌더링, Ask·업로드의 `fetch` 미호출, production `notFound` 경계를 포함한다.
- `pnpm typecheck` 및 `pnpm lint` (작업 디렉터리: `apps/dashboard`): 통과.
- `git diff --check origin/main...HEAD` 및 현재 작업 트리 `git diff --check`: 공백 오류 없음.
