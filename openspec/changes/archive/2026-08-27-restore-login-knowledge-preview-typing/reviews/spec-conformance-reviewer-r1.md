# Spec Conformance 리뷰 — restore-login-knowledge-preview-typing r1

- 판정: **needs_fix**
- 대상: 아카이브된 delta spec과 현재 로그인 구현·테스트
- 일시: 2026-08-27T19:17:00+09:00

## 시나리오 판정

| Scenario | 결과 | 근거 |
| --- | --- | --- |
| 지식 미리보기의 생성 순서 | 충족 | `LoginKnowledgePreview.tsx:119-141`가 질문을 문자 단위로 표시한 후 답변을 표시하고, 그 뒤에 근거 chip을 노출한 다음 다음 시나리오 인덱스로 전환한다. 미리보기 본문은 `aria-hidden`으로 유지된다(`:160`). |
| 헤드라인 강조 | 충족 | `LoginHeroTitle.tsx:21-27`가 “답으로 연결하다.”를 의미 있는 span으로 감싸며, `globals.css:280-295`의 pseudo-element가 accent 밑줄을 그린다. |
| 감소 모션 또는 비가시 탭 | **미충족** | 미리보기는 감소 모션·비가시 탭에서 완료 상태로 전환하고 타이머를 정리한다(`LoginKnowledgePreview.tsx:75-81, 146-149`). 하지만 헤드라인은 비가시 탭만 `is-complete`으로 처리하고, 감소 모션은 여전히 `is-animating`을 부여한다(`LoginHeroTitle.tsx:6-24`). reduced-motion CSS는 `animation-duration`만 `0.01ms`로 축소하며 (`globals.css:771-779`), 밑줄 애니메이션의 `280ms` 지연(`:293-295`)을 제거하지 않는다. `both` fill mode 때문에 지연 동안 밑줄은 시작 상태(`scaleX(0)`)라서, 요구한 “즉시 완성된 정적 상태”가 아니다. |

## 실행 검증

- `pnpm --dir apps/dashboard test -- LoginKnowledgePreview.test.tsx login-page-route.test.tsx`: **65개 테스트 파일, 305개 테스트 통과**
- 단, 현재 테스트는 미리보기의 감소 모션만 확인하며(`LoginKnowledgePreview.test.tsx:43-53`), 헤드라인의 감소 모션 즉시 완료 상태 및 비가시 탭 전환을 검증하지 않는다.

## 조치가 필요한 항목

1. **감소 모션에서 헤드라인 밑줄을 즉시 정적 완료 상태로 제공하지 못함**
   - 관련 계약: `google-authentication`의 “감소 모션 또는 비가시 탭” Scenario
   - 재현: `prefers-reduced-motion: reduce` 환경에서 `/login`을 연다.
   - 현재 결과: `is-animating` class와 `280ms` animation delay가 유지되어 밑줄이 지연 후에야 나타난다.
   - 기대 결과: 감소 모션에서는 밑줄 애니메이션과 지연을 모두 제거하거나 컴포넌트가 `is-complete` 상태를 렌더링해 최초 표시부터 전폭 밑줄을 제공해야 한다.
   - 회귀 방지: 헤드라인의 reduced-motion 및 visibility 상태를 직접 검증하는 단위 테스트를 추가한다.

## 판정 근거

delta spec의 핵심 생성 순서와 일반 환경의 밑줄 강조는 구현돼 있다. 또한 미리보기는 모션 민감 사용자와 비가시 탭에서 정지 상태를 제공한다. 그러나 같은 정적 완료 보장이 헤드라인 감소 모션에는 적용되지 않아, 명시적 MUST Scenario 하나가 충족되지 않는다. 사람의 추가 결정 없이 코드와 테스트로 해결 가능한 결함이므로 **needs_fix**로 판정한다.
