# evaluation-experiment-registry Specification

## Purpose
평가 실행을 목적·종류·판정 기준·결정 기록을 가진 실험 단위로 묶어 정본 하나에 보존하고, 공개 화면이 읽을 허용 필드 스냅샷으로 내보내는 계약을 정의한다.

## Requirements

### Requirement: Experiment record
시스템은 평가 실험을 하나의 기록으로 보존해야 MUST 한다. 실험 기록은 고유 id, 제목, 확인하려는 질문, 종류, 기준선과 후보 각각의 역할 이름과 실행 id, 판정 기준 참조, 공개 여부를 가져야 MUST 한다. 연결된 실행 id는 실제로 존재하는 저장 실행을 가리켜야 MUST 하며, 존재하지 않는 실행을 가리키는 실험은 등록되면 안 된다.

#### Scenario: Existing results registered without new runs
- **WHEN** 등록 스크립트가 기존 저장 결과(재검색 OFF/ON, Ask 반복 측정, 로컬 재채점 이력)로 실험을 등록한다
- **THEN** 모델 호출이나 재채점 없이 세 실험이 등록되고, 각 실험은 저장된 실행 id만 참조한다

#### Scenario: Unknown run reference
- **WHEN** 실험이 저장 결과에 없는 실행 id를 기준선이나 후보로 지정한다
- **THEN** 등록이 실패하고 해당 실험은 기록되지 않는다

#### Scenario: Re-registration is idempotent
- **WHEN** 같은 실험을 같은 id로 다시 등록한다
- **THEN** 중복 실험이 생기지 않고 기록 하나만 남는다

### Requirement: Experiment kinds
실험 종류는 도입 실험, 안정성 측정, 채점 검증 세 가지 중 하나여야 MUST 한다. 채택 판정과 결정 상태는 도입 실험에만 있어야 MUST 한다. 안정성 측정과 채점 검증은 채택 판정 없이 측정값만 가져야 MUST 하며, 기준선 통과 → 후보 실패 질문을 회귀로 기록하면 안 된다. 안정성 측정에서는 이를 흔들림으로, 채점 검증에서는 판정 변화로 기록해야 MUST 한다.

#### Scenario: Adoption experiment
- **WHEN** 재검색 OFF/ON 실험을 도입 실험으로 등록한다
- **THEN** 실험은 판정 기준과 결정 상태를 가진다

#### Scenario: Stability measurement has no adoption verdict
- **WHEN** Ask 반복 측정을 안정성 측정으로 등록한다
- **THEN** 실험에 채택 판정과 결정 상태가 없고, 질문별 판정 일치 수와 흔들린 질문은 저장하지 않고 화면이 측정값으로 계산해 보인다

#### Scenario: Grader check has no adoption verdict
- **WHEN** 로컬 재채점 이력을 채점 검증으로 등록한다
- **THEN** 실험에 채택 판정이 없고, 판정이 바뀐 질문 수는 화면이 측정값으로 계산해 보이며, 실험 기록은 PR 관문 계약 `offline-eval-regression-gate`를 출처로 참조한다

### Requirement: Adoption policy v1
시스템은 채택 정책 v1을 버전이 있는 정본 하나로 보존해야 MUST 한다. 정책 v1은 다음 조건을 모두 만족할 때만 채택 가능으로 판정해야 MUST 한다: 기준선에서 통과하고 후보에서 실패한 질문 0개(질문 단위 회귀), 검사 중단 질문 0개, 후보 통과 수가 기준선 통과 수보다 많음, 총비용 증가 50% 이하, p95 응답 시간 증가 15초 이하. 비교할 질문 집합이나 고정 조건이 다르면 판정하지 않고 비교 불가로 기록해야 MUST 한다. 정책이 반복 측정 없이 판정한다는 한계를 정책 기록에 포함해야 MUST 한다.

#### Scenario: No improvement means not adoptable
- **WHEN** 후보가 회귀 0개, 비용·p95 허용 범위 안이지만 통과 수가 기준선과 같다
- **THEN** 정책 v1 판정은 채택 가능이 아니다

#### Scenario: Single question regression blocks
- **WHEN** 전체 통과 수는 같지만 기준선에서 통과한 질문 하나가 후보에서 실패한다
- **THEN** 정책 v1 판정은 회귀 1개로 채택 가능이 아니다

#### Scenario: Mismatched conditions
- **WHEN** 기준선과 후보의 질문 집합이나 고정 조건 지문이 다르다
- **THEN** 정책 v1은 판정하지 않고 비교 불가와 그 이유를 기록한다

### Requirement: Criteria provenance and original criteria
각 도입 실험은 판정에 쓴 기준 세트를 참조해야 MUST 한다. 기준 세트는 조건 목록, 출처 문서 경로, 출처가 git에 처음 커밋된 시각, 그리고 그 시각이 실험의 가장 이른 실행 시각보다 앞서는지 여부를 가져야 MUST 한다. 출처 시각이 실행보다 늦거나 확인할 수 없으면 사전 등록이라고 표시하면 안 되며, 그 사실을 기록해야 MUST 한다. 재검색 실험은 `openspec/changes/archive/2026-11-09-ask-evidence-research/design.md` D4의 원래 기준과 실행 당시 저장된 조건별 판정(`checks`)과 최종 판정(`adopted`)으로 판정돼야 MUST 하며, 결과 이후 정의한 정책 v1로 판정을 바꾸면 안 된다. 정책 v1로 판정했을 때의 결과는 참고 판정으로만 기록할 수 있다.

#### Scenario: Original criteria judged from stored checks
- **WHEN** 재검색 실험을 등록한다
- **THEN** 원래 기준 6개의 조건별 결과가 저장된 판정과 같게 기록되고(답변 복구·통과 증가·비용 미충족, 기존 30문항 감소 없음·위조 인용 증가 없음·p95 충족), 최종 판정은 미채택이다

#### Scenario: Criteria recorded after the runs
- **WHEN** 기준 출처의 첫 커밋 시각이 실험의 가장 이른 실행 시각보다 늦다
- **THEN** 기준 세트는 사전 등록으로 표시되지 않고 "실행보다 먼저 기록됐음을 증명하지 못함"이 기록된다

#### Scenario: Reference verdict under policy v1
- **WHEN** 재검색 실험에 정책 v1을 참고로 적용한다
- **THEN** 참고 판정은 회귀 1개를 추가로 막는 조건으로 기록되고, 공식 판정과 결정 상태는 바뀌지 않는다

### Requirement: Decision record
도입 실험의 결정 기록은 결정 상태(채택, 미채택, 판단 보류 중 하나), 결정 근거, 결정 날짜, 근거가 된 판정의 기준 세트 참조를 가져야 MUST 한다. 결정 기록은 등록 스크립트로만 생성되며 화면에서 만들거나 바꿀 수 없어야 MUST 한다. 측정 실험은 결정 기록을 가지면 안 된다.

#### Scenario: Research experiment decision
- **WHEN** 재검색 실험의 결정 기록을 등록한다
- **THEN** 결정 상태는 미채택, 근거는 원래 기준 미충족 조건과 기본 OFF 유지이며, 원래 기준 세트를 참조한다

#### Scenario: Measurement experiment decision rejected
- **WHEN** 안정성 측정이나 채점 검증 실험에 결정 기록을 등록하려 한다
- **THEN** 등록이 실패한다

### Requirement: Project-level storage boundary
실험, 기준 세트, 정책, 결정 기록의 정본은 워크스페이스에 속하지 않는 프로젝트 전역 DB 기록이어야 MUST 한다. 이 기록은 `service_role`만 쓰고 읽어야 MUST 하며, `anon`과 `authenticated`는 어떤 행도 읽거나 쓸 수 없어야 MUST 한다. 기록에는 workspace 식별자, 사용자 식별자, 자격증명, 답변 본문을 넣으면 안 된다.

#### Scenario: Anonymous access
- **WHEN** `anon` 역할로 실험 기록을 조회하거나 삽입한다
- **THEN** 행이 반환되지 않거나 거부되고 기록은 바뀌지 않는다

#### Scenario: Authenticated member access
- **WHEN** 어떤 워크스페이스 멤버의 JWT로 실험 기록을 조회하거나 수정한다
- **THEN** 권한 오류(SQLSTATE `42501`)로 거부되어 행이 반환되지 않고 기록은 바뀌지 않는다

### Requirement: Public snapshot export
내보내기 스크립트는 공개로 표시된 실험만 허용 필드 스냅샷으로 저장소에 내보내야 MUST 한다. 로컬 전용 실험은 스냅샷에 들어가면 안 된다. 스냅샷은 실험 기록, 기준 세트와 출처, 정책 버전, 결정 기록, 각 실행의 id·코드 리비전·실행 시각을 담아야 MUST 한다. 허용 목록 밖 필드나 금지 필드가 있으면 내보내기가 실패해야 MUST 한다. 같은 DB 상태를 두 번 내보내면 같은 스냅샷이 나와야 MUST 한다.

#### Scenario: Local-only experiment excluded
- **WHEN** 로컬 재채점 이력 실험이 있는 상태에서 스냅샷을 내보낸다
- **THEN** 스냅샷에는 재검색 실험과 Ask 반복 측정만 들어간다

#### Scenario: Forbidden field
- **WHEN** 내보낼 기록에 workspace 식별자나 답변 본문 필드가 있다
- **THEN** 내보내기가 실패하고 스냅샷 파일은 바뀌지 않는다

#### Scenario: Deterministic export
- **WHEN** DB가 바뀌지 않은 상태에서 내보내기를 두 번 실행한다
- **THEN** 두 스냅샷의 내용이 바이트 단위로 같다

### Requirement: Single source for adoption thresholds
도입 실험 판정에 쓰는 수치 기준(비용 증가 허용률, p95 증가 허용 시간)은 정책 정본 한 곳에서만 정의돼야 MUST 한다. 평가 스크립트와 화면은 각자 기준값을 하드코딩하면 안 되며, 정본과 다른 기준값을 쓰면 검사가 실패해야 MUST 한다.

#### Scenario: Threshold drift detected
- **WHEN** 평가 스크립트나 화면 코드의 기준값이 정책 정본과 다르다
- **THEN** 검사가 실패하고 어긋난 위치를 보고한다
