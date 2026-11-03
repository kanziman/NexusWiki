# ai-control-room Specification

## Purpose

워크스페이스 멤버가 요청과 잡의 처리 경로, 지연, 비용을 화면에서 확인하되 Ask 작성자 경계와 테넌트 격리를 약화시키지 않게 한다.

## Requirements

### Requirement: Control Room 추적 탭
시스템은 인증된 워크스페이스 라우트 `/w/[workspaceId]/control`에 추적 탭과 예산 탭을 SHALL 제공하고, 운영 환경에서도 MUST 동작한다. trace 상세는 단계별 소요 시간, 호출 종류, 모델, 토큰, 비용, Router 결정, 시도 횟수, 최종 상태를 SHALL 보여준다. 아직 구현되지 않은 이후 단계(Step 3 품질, Step 4 리스크)의 탭은 아직 수집된 데이터가 없음을 표시할 뿐 지어낸 수치를 MUST NOT 보여준다. 원 관측 비용과 사후 정산을 반영한 공급자 보고 비용은 구분하고, 공급자 보고 비용 합계는 호출별 정산 반영 비용과 MUST 일치한다.

#### Scenario: 완료된 trace 상세
- **WHEN** 볼 권한이 있는 멤버가 trace를 연다
- **THEN** 시작부터 끝까지의 단계와 단계별 소요 시간, 토큰, 비용이 표시되고 합계가 해당 trace의 호출별 유효 비용과 일치한다. 정산되지 않은 기존 호출은 원 사용량 행 비용을 그대로 쓴다

#### Scenario: 진행 중인 수집 trace
- **WHEN** 잡 체인이 아직 끝나지 않았다
- **THEN** 완료, 진행, 대기 단계가 구분되어 표시된다

#### Scenario: 데이터가 없는 워크스페이스
- **WHEN** 멤버가 trace가 하나도 없는 워크스페이스에서 탭을 연다
- **THEN** 빈 상태와 첫 trace가 생기는 방법을 표시한다

#### Scenario: 관측액과 정산액이 다르다
- **WHEN** 원 관측 비용보다 작거나 큰 금액으로 사후 정산된다
- **THEN** 호출별 원 관측액을 보존해 구분하고, 정산 반영액과 상세 합계가 일치하며 정산을 새 공급자 호출로 세지 않는다

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

#### Scenario: 작성자가 보고서에 범위 밖의 값을 넣는다
- **WHEN** 작성자가 자신의 턴 보고서에 문자열이나 범위를 벗어난 숫자를 넣는다
- **THEN** 그 값은 지연 집계에서 제외되고 다른 멤버의 집계 조회는 실패하지 않는다

#### Scenario: 집계 경계를 조금씩 옮긴다
- **WHEN** 요청자가 집계 시작 시각을 초 단위로 바꿔 가며 호출한다
- **THEN** 시작 시각은 UTC 일 단위로 내려져, 같은 날 안의 호출은 같은 값을 돌려받는다

### Requirement: 작성자가 바꿀 수 없는 trace 식별자
작성자는 자신의 턴 종결에 필요한 컬럼만 직접 수정할 수 있어야 한다. 턴의 `trace_id`는 생성 뒤에 MUST NOT 바뀐다. 이 보호는 Ask 턴이 남아 있는 trace에 적용되며, 스레드 삭제나 계정 삭제로 턴이 사라진 trace는 Ask trace로 보호되지 않는다.

#### Scenario: 멤버가 이미 쓰인 trace로 새 턴을 만들려 한다
- **WHEN** 멤버가 같은 워크스페이스의 사용량이나 잡에 이미 있는 `trace_id`를 넣어, 함수를 거치거나 테이블에 직접 새 턴을 만든다
- **THEN** 데이터베이스가 권한 오류로 거부하고, 그 trace의 상세 조회 권한은 변하지 않는다

#### Scenario: editor가 다른 멤버의 Ask trace로 잡을 만들려 한다
- **WHEN** editor가 같은 워크스페이스의 Ask 턴에 쓰인 `trace_id`를 넣어 수집 잡을 인큐한다
- **THEN** 데이터베이스가 권한 오류로 거부하고 잡을 만들지 않는다. 한 요청의 여러 잡이 같은 `trace_id`를 쓰는 것은 허용한다

#### Scenario: 작성자가 턴의 trace를 바꾸려 한다
- **WHEN** 작성자가 요청자 JWT로 자신의 턴의 `trace_id`를 수정한다
- **THEN** 데이터베이스가 권한 오류로 거부하고 값은 그대로다

### Requirement: 허용 목록으로 조립한 응답
추적 API 응답은 정해진 허용 필드로만 MUST 조립하고, 질문, 프롬프트, 답변, 잡 payload, 원시 오류, 공급자 자격 증명을 MUST NOT 포함한다.

#### Scenario: 실패한 호출을 포함한 trace
- **WHEN** 공급자 오류로 실패한 단계가 있는 trace를 조회한다
- **THEN** 정제된 오류 분류만 표시되고 원시 오류 문자열은 반환되지 않는다

### Requirement: 확정 비용과 미확정 예산 점유 구분
Control Room은 권한이 있는 조회에서 공급자 보고 비용, 미확정 임시 확보액, 예산 판정에 반영되는 금액을 SHALL 구분한다. 임시 확보액을 실제 청구액으로 MUST NOT 표시한다. 기존 Ask 작성자와 수집 trace·집계의 역할별 접근 경계 및 본문 금지 계약을 MUST 유지한다.

#### Scenario: 미확정 호출이 있다
- **WHEN** 권한이 있는 멤버가 미확정 Ask를 포함한 비용을 조회한다
- **THEN** 미확정 상태와 임시 점유액이 확정 비용과 구분되어 표시되고 예산 제한의 원인을 알 수 있다

#### Scenario: 비용 정산이 완료됐다
- **WHEN** 미확정 호출이 확정 비용으로 정산된 뒤 조회한다
- **THEN** 임시 점유액과 확정 비용이 중복 표시되지 않고 예산 판정액이 실제 회계 상태와 일치한다

#### Scenario: 다른 작성자의 Ask 상세를 요청한다
- **WHEN** 같은 워크스페이스의 다른 멤버가 본인이 작성하지 않은 Ask trace 상세를 요청한다
- **THEN** HTTP 403으로 거부하고 사후 대조를 이유로 새로운 상세 접근 권한을 부여하지 않는다

### Requirement: Control Room 예산 탭
시스템은 Control Room의 예산 탭에서 워크스페이스의 이번 달 예산 현황(월간 한도, 공급자 보고 비용, 미확정 임시 점유액, 예산 판정액, 남은 크레딧), 적용 중인 프롬프트·출력 토큰 상한 정책, 그리고 예산 통제 작동 집계를 SHALL 표시해야 한다. `editor` 이상에게는 호출 경로별(`ask`, `compile`, `conflict_check`, `embed`, `query_embedding`) 호출 수·토큰·비용 분해와 컴파일 입력 잘림·`SKIP_UNCHANGED` 생략 건수를 추가로 SHALL 제공하며, `viewer`에게는 워크스페이스 공통 월간 예산 요약과 본인의 Ask 예산 통제 집계만 제공하고 워크스페이스 전체 호출 분해나 수집 통제 집계는 MUST NOT 노출한다. 모든 조회는 요청자 JWT로 실행되고 개인 식별자·스레드·개별 Ask trace·프롬프트 및 답변 본문을 MUST NOT 포함한다.

#### Scenario: editor가 예산 탭을 연다
- **WHEN** 워크스페이스 `editor` 또는 `owner`가 Control Room 예산 탭을 연다
- **THEN** 이번 달 예산 현황, 호출 경로별 비용·토큰 분해, 적용 중인 토큰 상한 정책, Ask 및 컴파일의 잘림·단락 집계가 표시되고 사용자 식별자나 본문은 포함되지 않는다

#### Scenario: viewer가 예산 탭을 연다
- **WHEN** 워크스페이스 `viewer`가 Control Room 예산 탭을 연다
- **THEN** 이번 달 워크스페이스 예산 요약, 토큰 상한 정책, 본인의 Ask 잘림·단락 집계만 표시되고 호출 경로별 워크스페이스 분해와 수집 단락 집계는 반환되지 않는다

#### Scenario: 비멤버가 예산 스냅샷을 요청한다
- **WHEN** 워크스페이스에 속하지 않은 사용자가 예산 탭 API를 호출한다
- **THEN** 시스템은 HTTP 403으로 거부하고 어떤 예산 수치도 반환하지 않는다

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

### Requirement: Control Room 리스크 탭
시스템은 Control Room 리스크 탭에서 적용 중인 정책 버전, 쓰기 모드, 위험 등급별 개정 건수, 승인 후 반영 중인 건수, 승인 대기 목록을 SHALL 제공한다. `editor` 이상은 대기 제안의 이전·제안 본문을 보고 승인하거나 거부할 수 있다. `viewer`는 집계만 보며 제안 본문을 MUST NOT 받는다. 비멤버는 HTTP 403이다.

#### Scenario: editor가 대기 제안을 처리한다
- **WHEN** `editor`가 리스크 탭에서 대기 제안을 승인한다
- **THEN** 제안이 목록에서 사라지고 집계가 갱신된다

#### Scenario: viewer가 리스크 탭을 연다
- **WHEN** `viewer`가 리스크 탭을 연다
- **THEN** 집계만 표시되고 승인 버튼과 본문이 없다

#### Scenario: 비멤버의 요청
- **WHEN** 비멤버가 리스크 API를 호출한다
- **THEN** HTTP 403으로 거부된다
