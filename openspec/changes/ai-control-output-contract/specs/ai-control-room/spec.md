## ADDED Requirements

### Requirement: Control Room 품질 탭
시스템은 Control Room 품질 탭에서 Ask 인용 위반, 수리, Fallback 집계와 구조화 출력의 시도 위반, 펜스 제거, 소진, 페이지 근거 집계를 SHALL 제공한다. 요청은 요청자 JWT로 수행하며 본문과 사용자 식별자를 MUST NOT 반환한다. `editor` 이상은 워크스페이스 전체를, `viewer`는 본인 Ask 집계만 본다.

#### Scenario: editor가 품질 탭을 연다
- **WHEN** `editor` 또는 `owner`가 품질 탭을 연다
- **THEN** Ask와 수집 경로의 품질 집계가 표시되고 답변 본문이나 사용자 식별자는 없다

#### Scenario: viewer가 품질 탭을 연다
- **WHEN** `viewer`가 품질 탭을 연다
- **THEN** 본인 Ask 집계만 표시되고 수집 경로 집계는 반환되지 않는다

#### Scenario: 비멤버의 요청
- **WHEN** 비멤버가 품질 API를 호출한다
- **THEN** HTTP 403으로 거부되고 수치가 반환되지 않는다

#### Scenario: 집계할 데이터가 없다
- **WHEN** 기간 안에 턴과 호출이 없다
- **THEN** 0을 정상 수치처럼 꾸미지 않고 빈 상태를 표시한다
