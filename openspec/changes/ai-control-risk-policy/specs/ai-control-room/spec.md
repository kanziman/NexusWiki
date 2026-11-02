## ADDED Requirements

### Requirement: Control Room 리스크 탭
시스템은 Control Room 리스크 탭에서 적용 중인 정책 버전, 쓰기 모드, 위험 등급별 쓰기 건수, 승인 대기 목록을 SHALL 제공한다. `editor` 이상은 대기 제안의 이전·제안 본문을 보고 승인하거나 거부할 수 있다. `viewer`는 집계만 보며 제안 본문을 MUST NOT 받는다. 비멤버는 HTTP 403이다.

#### Scenario: editor가 대기 제안을 처리한다
- **WHEN** `editor`가 리스크 탭에서 대기 제안을 승인한다
- **THEN** 제안이 목록에서 사라지고 집계가 갱신된다

#### Scenario: viewer가 리스크 탭을 연다
- **WHEN** `viewer`가 리스크 탭을 연다
- **THEN** 집계만 표시되고 승인 버튼과 본문이 없다

#### Scenario: 비멤버의 요청
- **WHEN** 비멤버가 리스크 API를 호출한다
- **THEN** HTTP 403으로 거부된다
