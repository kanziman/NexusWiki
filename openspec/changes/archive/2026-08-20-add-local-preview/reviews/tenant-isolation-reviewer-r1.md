# 테넌트 격리 리뷰 r1

## 판정: pass

## 범위

`origin/main...feat/local-preview-review`의 개발 전용 `/preview` 목업 경로를 검토했다. 중점은 실제 테넌트 데이터·세션·API 경로와의 분리, production 노출 차단, 쓰기성 조작의 외부 부작용 부재다.

## 근거

- `apps/dashboard/app/preview/layout.tsx:10-14`는 `NODE_ENV !== "development"`이면 `notFound()`를 호출한다. 하위 catch-all 경로도 이 서버 레이아웃 아래에 있으므로 production에서 목업 데이터가 렌더링되지 않는다.
- 변경은 `app/preview/**`, `PreviewWorkspace.tsx`, `preview-data.ts`, 테스트와 OpenSpec 문서로 한정되어 있다. `/w/**` 레이아웃·미들웨어·Supabase 클라이언트·RLS/API 코드는 변경되지 않았다.
- `apps/dashboard/components/PreviewWorkspace.tsx:18-26`의 import는 fixture와 UI 라이브러리뿐이다. 변경된 preview 소스 전체에서 `fetch`, Supabase 클라이언트, `apiFetch`, RPC, Storage, `signOut` 호출을 찾지 못했다.
- `PreviewWorkspace.tsx:113-119`, `144-151`, `295-301`, `587-593`, `637-650`의 쓰기성 제어는 모두 `setNotice`/`onAction`으로만 연결되고, `72-80`의 한국어 비저장 안내를 렌더링한다.
- `apps/dashboard/middleware.ts:59-75`는 변경되지 않았고 보호 대상 `/w/:path*`를 계속 인증 게이트로 둔다. `/preview`를 matcher에서 제외한 것은 로컬 무인증 목업을 위한 것이며, production은 위 레이아웃 경계가 별도로 차단한다.

## 지적 사항

없음. fixture의 `preview-workspace` 식별자와 `.local` 이메일은 정적 목업 값이며 실제 데이터 식별자나 권한 토큰을 포함하지 않는다.

## 검증

- `pnpm test -- PreviewWorkspace.test.tsx preview-layout.test.tsx` (작업 디렉터리: `apps/dashboard`): 50 파일, 217 테스트 통과. preview 테스트는 Ask·업로드에서 `fetch` 미호출을 확인하고, production layout의 `notFound` 결과도 확인한다.
- `pnpm typecheck` (작업 디렉터리: `apps/dashboard`): 통과.
- `pnpm lint` (작업 디렉터리: `apps/dashboard`): 통과.
- `git diff --check origin/main...HEAD`: 공백 오류 없음.
