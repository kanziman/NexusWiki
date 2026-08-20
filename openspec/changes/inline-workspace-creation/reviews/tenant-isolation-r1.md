# Tenant Isolation 리뷰 — inline-workspace-creation r1

- 판정: pass
- 대상: `git diff main...feat/inline-workspace-creation` (ab6dc63)
- 일시: 2026-08-20T07:16:55Z

## 범위 요약

`git diff --stat main...feat/inline-workspace-creation` 결과, 코드 변경은
`apps/dashboard/components/WorkspaceSwitcher.tsx`와 그 테스트
(`apps/dashboard/tests/WorkspaceSwitcher.test.tsx`) 두 파일뿐이다. 나머지는
`openspec/` 문서(proposal/design/tasks/spec)뿐이며 `supabase/migrations/`,
서버 액션, API 라우트에는 변경이 없다. `apps/dashboard/app/onboarding-actions.ts`는
`git diff main...feat/inline-workspace-creation -- apps/dashboard/app/onboarding-actions.ts`
가 빈 출력을 내 완전히 동일함을 확인했다 — `createPersonalWorkspace` 서버 액션
로직(이름 검증, slug 충돌 재시도, `MAX_PERSONAL_WORKSPACES = 3` 서버 재검증)이
그대로 재사용된다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `WorkspaceSwitcher.tsx`, `onboarding-actions.ts`, `apps/dashboard/lib/supabase/server.ts` 전체에 `service_role`/`SUPABASE_SERVICE`/`bypassrls` 문자열 없음 (`git diff main...feat/inline-workspace-creation \| grep -inE "service_role\|service_key\|bypassrls\|anon\b\|grant "` → 매치 0건). `createClient()`(`apps/dashboard/lib/supabase/server.ts:26-42`)는 `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` + 요청자 쿠키 세션으로 만든 requester JWT 클라이언트다. |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 신규 테이블·마이그레이션 없음 (`supabase/migrations/` diff 없음) |
| A-3 | anon 신규 GRANT/정책 | 해당 없음 | 마이그레이션 변경 없음 |
| A-4 | 워커 workspace_id 필터 | 해당 없음 | 워커 코드 변경 없음. 이 change는 요청 경로(서버 액션)만 다루며, 그마저도 변경되지 않았다 |
| A-5 | 신규 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 이 change에서 UPDATE/DELETE 경로 없음. `createPersonalWorkspace`는 INSERT만 수행(변경 없음) |
| B-7 | 42501 → 403 매핑 | 해당 없음 | 위와 동일. slug UNIQUE 충돌(`23505`)만 처리하며 이 로직도 변경되지 않음 |
| C-8 | 멱등성(upsert 키) | 해당 없음 | 워크스페이스 생성은 사용자 명시 액션(버튼 클릭)이며 at-least-once 잡 큐 경로가 아니다. 기존 slug 충돌 재시도 로직도 변경 없음 |
| C-9 | jobs 직접 UPDATE 금지 | 해당 없음 | `jobs` 테이블 관련 코드 변경 없음 |
| D-10~14 | 벡터 검색/토크나이저/프롬프트/인용 앵커 | 해당 없음 | 검색·인덱싱·LLM 프롬프트 코드 변경 없음. 순수 UI 컴포넌트 |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음 |

## 사용자 지정 확인 항목

**(1) 새 서버 액션/API 경로 추가 여부**
없음. `git diff --name-status main...feat/inline-workspace-creation`에는
`WorkspaceSwitcher.tsx`(수정)와 테스트 파일(수정)만 코드 변경으로 나온다.
`app/onboarding-actions.ts`는 diff에 전혀 등장하지 않아 완전히 동일하다.
컴포넌트는 `import { createPersonalWorkspace } from "@/app/onboarding-actions"`
(`WorkspaceSwitcher.tsx:9`)로 기존 함수를 그대로 호출한다
(`WorkspaceSwitcher.tsx:65`, `handleCreateSubmit` 내부).

레거시 라우트 `apps/dashboard/app/w/new/page.tsx`는 여전히 저장소에 남아 있으며
이번 diff에서 변경되지 않았다(design.md Non-Goals에 "`/w/new` 라우트 변경"이
명시적으로 범위 밖으로 기록됨). 죽은 진입 링크가 됐을 수 있으나 이는 UX 이슈이지
테넌트 격리 위반이 아니다.

**(2) 클라이언트 표시 상태만으로 최종 판정하지 않는지**
`WorkspaceSwitcher.tsx:175`의 `workspaces.length < 3`는 **인라인 폼 진입점을
보여줄지 여부만** 결정하는 UI 게이트다. 실제 생성 여부의 최종 판정은
`handleCreateSubmit`(`WorkspaceSwitcher.tsx:58-76`)이 서버 액션
`createPersonalWorkspace(newName)`을 호출한 결과에 전적으로 달려 있다:

- 서버 액션(`onboarding-actions.ts:33-71`, 변경 없음)은 매 호출마다 자체 Supabase
  클라이언트로 `workspaces` 테이블을 다시 조회해(`existing?.length`) 상한을
  재검증한다 — 클라이언트가 넘긴 값을 신뢰하지 않는다.
- 서버가 `{ error: ... }`를 반환하면 `createError`에 담겨 폼 안에 그대로
  표시되고(`WorkspaceSwitcher.tsx:66-70`) `router.push`는 호출되지 않는다 —
  낙관적 성공 처리가 없다.
- 이 흐름은 테스트로도 커버된다: `apps/dashboard/tests/WorkspaceSwitcher.test.tsx`의
  "인라인 폼 제출이 실패하면(상한 도달 등) 폼 안에 오류를 보여주고 입력값을
  유지한다" 케이스가 서버가 상한 오류를 반환할 때 `push`가 호출되지 않음을
  단언한다.
- design.md(Risks/Trade-offs, 4번째 항목)도 "서버 액션이 최종 판정"이라고
  명시하고 있어, 클라이언트 stale state(다른 탭에서 이미 상한 도달)로 인한
  경쟁 상황을 설계 단계에서 인지하고 서버 재검증에 위임했음이 문서로도
  확인된다.

**(3) service_role/권한 우회 혼입 여부**
없음. A-1 항목 참조. `WorkspaceSwitcher.tsx`는 클라이언트 컴포넌트(`"use client"`,
1행)이며 Supabase 클라이언트를 직접 만들지 않고 서버 액션만 호출한다. 서버
액션은 변경되지 않았고, 여전히 requester JWT 기반 `createClient()`만 사용한다.

## 조치가 필요한 항목

없음.

## 판정 근거

새 서버 코드·마이그레이션·RLS 변경이 전무하고, 기존에 이미 requester JWT로
동작하며 서버 측 3개 상한 재검증을 수행하는 `createPersonalWorkspace` 서버
액션을 그대로 재사용한다. 클라이언트의 `workspaces.length < 3` 조건은 UI
진입점 노출 여부만 제어할 뿐 생성 최종 판정에는 관여하지 않으며, 서버 거부
시 낙관적 네비게이션 없이 오류를 그대로 표시하는 것이 테스트로 검증돼 있다.
검사 항목 A~E 중 해당하는 항목 전부가 "해당 없음" 또는 "통과"이며 위반
사항이 없어 `pass`로 판정한다.
