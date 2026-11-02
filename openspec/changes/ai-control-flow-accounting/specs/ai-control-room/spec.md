## Purpose

워크스페이스 멤버가 요청과 잡의 처리 경로, 지연, 비용을 화면에서 확인하되 Ask 작성자 경계와 테넌트 격리를 약화시키지 않게 한다.

## ADDED Requirements

### Requirement: Control Room 추적 탭
시스템은 인증된 워크스페이스 라우트 `/w/[workspaceId]/control`에 추적 탭을 SHALL 제공하고, 운영 환경에서도 MUST 동작한다. trace 상세는 단계별 소요 시간, 호출 종류, 모델, 토큰, 비용, Router 결정, 시도 횟수, 최종 상태를 SHALL 보여준다. 이후 단계의 탭은 아직 수집된 데이터가 없음을 표시할 뿐 지어낸 수치를 MUST NOT 보여준다.

#### Scenario: 완료된 trace 상세
- **WHEN** 볼 권한이 있는 멤버가 trace를 연다
- **THEN** 시작부터 끝까지의 단계와 단계별 소요 시간, 토큰, 비용이 표시되고 합계가 해당 trace의 사용량 행과 일치한다

#### Scenario: 진행 중인 수집 trace
- **WHEN** 잡 체인이 아직 끝나지 않았다
- **THEN** 완료, 진행, 대기 단계가 구분되어 표시된다

#### Scenario: 데이터가 없는 워크스페이스
- **WHEN** 멤버가 trace가 하나도 없는 워크스페이스에서 탭을 연다
- **THEN** 빈 상태와 첫 trace가 생기는 방법을 표시한다

### Requirement: 작성자와 역할을 함께 강제하는 trace 접근
Ask trace 상세는 해당 Ask 턴의 작성자이면서 현재 멤버인 사용자만 MUST 볼 수 있다. 수집 trace 상세와 Ask 집계는 editor 이상만 SHALL 볼 수 있다. 모든 조회는 요청자 JWT로 실행되고 RLS의 평가를 MUST 받으며, `service_role`을 MUST NOT 사용한다.

#### Scenario: 작성자가 자신의 Ask trace를 본다
- **WHEN** 현재 멤버가 자신의 Ask trace를 연다
- **THEN** 상세가 표시된다

#### Scenario: editor가 다른 멤버의 Ask trace를 요청한다
- **WHEN** editor 또는 owner가 다른 멤버의 Ask trace 식별자로 상세를 요청한다
- **THEN** 시스템은 HTTP 403으로 거부하고 해당 trace의 존재 여부를 드러내지 않는다

#### Scenario: viewer가 탭을 연다
- **WHEN** viewer가 추적 탭을 연다
- **THEN** 자신의 Ask trace만 표시되고 수집 trace와 집계는 표시되지 않는다

#### Scenario: 다른 워크스페이스의 trace
- **WHEN** 멤버가 소속되지 않은 워크스페이스의 trace 식별자로 요청한다
- **THEN** 시스템은 HTTP 403으로 거부하고 어떤 값도 반환하지 않는다

#### Scenario: 멤버십을 잃은 작성자
- **WHEN** 워크스페이스에서 제거된 작성자가 이전 Ask trace를 요청한다
- **THEN** 시스템은 접근을 거부한다

### Requirement: 개인을 드러내지 않는 Ask 집계
Ask 집계는 기간별 건수, 비용, 지연, 결정 분포만 SHALL 제공하고, 사용자별 분해와 개별 trace 식별자를 MUST NOT 포함한다.

#### Scenario: editor가 집계를 본다
- **WHEN** editor가 Ask 집계를 조회한다
- **THEN** 응답에 사용자 식별자, 스레드 식별자, 개별 Ask trace 식별자가 없다

### Requirement: 허용 목록으로 조립한 응답
추적 API 응답은 정해진 허용 필드로만 MUST 조립하고, 질문, 프롬프트, 답변, 잡 payload, 원시 오류, 공급자 자격 증명을 MUST NOT 포함한다.

#### Scenario: 실패한 호출을 포함한 trace
- **WHEN** 공급자 오류로 실패한 단계가 있는 trace를 조회한다
- **THEN** 정제된 오류 분류만 표시되고 원시 오류 문자열은 반환되지 않는다
