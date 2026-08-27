# Spec Conformance 리뷰 — restore-login-knowledge-preview-typing r2

- 판정: **pass**
- 대상: 아카이브된 delta spec과 현재 로그인 구현·테스트
- 일시: 2026-08-27T19:20:00+09:00
- 재검토 사유: r1에서 지적한 감소 모션 시 헤드라인 밑줄의 280ms 지연을 수정한 뒤의 2차 검토

## r1 지적 사항 재검토

`LoginHeroTitle`은 `matchMedia("(prefers-reduced-motion: reduce)")`의 현재 값과 변경을 감지한다. 감소 모션이거나 문서가 비가시 상태이면 밑줄 span에 `is-complete`를, 그 외에는 `is-animating`을 렌더링한다. CSS의 기본 pseudo-element는 `scaleX(1)`이고 애니메이션은 `is-animating`에만 적용되므로, 완료 상태에는 r1에서 문제였던 280ms 지연 및 `scaleX(0)` 시작 프레임이 없다.

`LoginHeroTitle.test.tsx`는 감소 모션 환경에서 `is-complete` 렌더링을 직접 확인한다. 따라서 r1의 필수 수정 항목은 해결됐다.

## 시나리오 판정

| Scenario | 결과 | 근거 |
| --- | --- | --- |
| 지식 미리보기의 생성 순서 | 충족 | `LoginKnowledgePreview`가 질문을 문자 단위로 표시한 후 답변을 생성하고 근거 chip을 노출한 다음 다음 시나리오로 넘긴다. |
| 헤드라인 강조 | 충족 | `LoginHeroTitle`이 “답으로 연결하다.”를 의미 있는 span으로 감싸고, `login-visual-underlined::after`가 accent 밑줄을 표시한다. 모션 허용 상태에서는 `is-animating`으로 그리기 애니메이션을 적용한다. |
| 감소 모션 또는 비가시 탭 | 충족 | 미리보기는 두 상태에서 완료된 질문·답변·근거를 즉시 유지하고 타이머 순환을 시작하지 않는다. 헤드라인도 두 상태에서 `is-complete`를 렌더링해 정적 완료 밑줄을 제공한다. |
| OAuth 요청 진행 중 | 충족 | `LoginForm`이 제출 중 CTA를 비활성화하고 진행 문구를 제공해 중복 시작을 막는다. |
| 가입 화면 연결 | 충족 | `/login`의 가입 안내 링크가 `/signup`을 가리킨다. |
| 로그인 시작 및 인증 실패 | 충족 | Google OAuth는 내부 `/auth/callback?next=%2F`를 redirect 대상으로 시작하고, 콜백 실패는 `/login?error=auth` 및 단일 오류 문구로 처리한다. |

## 실행 검증

- `pnpm --dir apps/dashboard test -- LoginHeroTitle.test.tsx LoginKnowledgePreview.test.tsx login-page-route.test.tsx`: **66개 테스트 파일, 306개 테스트 통과**

## 판정 근거

delta spec의 모든 Given/When/Then 표시 계약을 구현이 충족한다. 특히 r1의 미충족 조건이었던 감소 모션 헤드라인은 더 이상 애니메이션 class나 지연을 사용하지 않고 `is-complete`의 전폭 밑줄로 렌더링된다. 스펙 이탈 또는 추가 조치가 필요한 항목이 없어 **pass**로 판정한다.
