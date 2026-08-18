# Commit Message Guide

## 언어 규칙
모든 커밋 메시지는 한국어로 작성한다.

허용:
fix(payment): 정산 금액 중복 계산 수정
feat(auth): 구글 로그인 추가
test(payment-domain): JUnit Platform 활성화

금지:
fix(payment): fix duplicate settlement bug
feat(auth): add google oauth login

---

## 형식
Conventional Commits v1.0.0 형식을 사용한다.

### 기본 구조
```text
<type>(<scope>): <description>

<blank line>

- 변경 사항 1
- 변경 사항 2
- 변경 사항 3

<blank line>

AC:
Given: [전제 조건 / 상황]
When: [동작 / 이벤트]
Then: [기대 결과 / 검증 기준]

<blank line>

Refs: #123
(또는 Closes: #123)
```

---

## 타입
- `feat` : 새로운 기능 추가
- `fix` : 버그 수정
- `test` : 테스트 코드 추가 및 수정
- `refactor` : 기능 변경 없는 코드 리팩토링
- `build` : 빌드 시스템 및 외부 의존성 변경
- `ci` : CI/CD 설정 파일 및 스크립트 변경
- `docs` : 문서 추가 및 수정
- `chore` : 기타 유지보수 및 설정 변경

---

## 제목 규칙
- 현재 변경 사항만을 명확히 축약한 제목이어야 한다.
- 50자 이내를 권장한다.

예시:
```text
fix(payment): 정산 금액 중복 계산 수정
```

---

## 본문 규칙
본문은 변경 사항을 요약하는 용도로 작성한다.

- 반드시 목록(Bullet List, `-`) 형태로 작성한다.
- 변경한 기능, 로직, 테스트 등을 중심으로 작성한다.
- 구현 세부 코드나 분석 내용은 작성하지 않는다.
- Why가 필요한 경우에만 간단히 추가한다.

예시:
```text
- 정산 금액 계산 중복 로직 제거
- Redis 캐시 갱신 순서 수정
- 관련 단위 테스트 추가
```

---

## AC (Acceptance Criteria) 규칙
기능 구현(`feat`) 또는 버그 수정(`fix`) 시 검증 기준이 명확히 드러나도록 `Given:`, `When:`, `Then:` 형식을 본문 하단에 포함한다.

- `Given:` 사전 조건이나 시스템의 초기 상태
- `When:` 사용자의 행동이나 트리거된 이벤트
- `Then:` 기대되는 결과 및 검증 가능한 상태 변화

예시:
```text
AC:
Given: 정산 대상 주문 데이터가 2건 이상 존재할 때
When: 배치 정산 로직이 실행되면
Then: 중복 계산 없이 정확한 총합 금액으로 1회만 결제 테이블에 반영된다
```

---

## 이슈 링크 규칙
관련 GitHub Issue가 존재하면 커밋 마지막에 반드시 추가한다.

### 단일 이슈
```text
Refs: #123
```
또는 (이슈 해결 시)
```text
Closes: #123
```

### 여러 이슈인 경우
```text
Refs: #123, #456
```

이슈가 없다면 생략한다.

---

## 전체 작성 예시

```text
feat(auth): 구글 OAuth 로그인 및 세션 연동

- Google OAuth2 로그인 콜백 라우트 구현
- 세션 토큰 발급 및 쿠키 보안 헤더 적용
- 인증 예외 처리를 위한 미들웨어 가드 추가

AC:
Given: 미인증 사용자가 구글 로그인 버튼을 클릭했을 때
When: Google OAuth 인증이 성공적으로 완료되면
Then: 사용자 세션이 발급되고 워크스페이스 대시보드로 이동한다

Closes: #20
```

---

## 금지
다음 내용은 커밋 메시지에 포함하지 않는다:
- Confidence
- Scope-risk
- Rejected
- Tested
- Not-tested
- Analysis
- AI 생성 설명
- 장문의 변경 보고서
- `Co-Authored-By:` 트레일러 (에이전트 공동 저자 표기 일체 — `Co-Authored-By: Claude ...` 포함)
- `Generated with` 류의 도구 서명
