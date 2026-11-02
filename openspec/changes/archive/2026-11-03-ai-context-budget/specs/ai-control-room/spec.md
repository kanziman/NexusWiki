## MODIFIED Requirements

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

## ADDED Requirements

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
