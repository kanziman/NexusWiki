# ask-evidence-research Specification

## Purpose

Ask의 첫 검색 결과에서 누락된 비교 대상과 표현을 모델이 확인한 뒤, 요청자의 권한 안에서 제한된 추가 검색으로 근거를 보완하고 기존 인용·예산·스트리밍 계약을 유지한다.

## Requirements

### Requirement: Bounded model-selected evidence research
시스템은 기능 ON이고 최초 근거가 있을 때 질문과 예산 내 근거를 모델에 제공하고 실제 search_evidence 도구 호출을 선택하게 SHALL 한다. 판단은 1회, 검색은 최대 2회이며 전체 추가 단계는 15초 이내로 제한해야 MUST 한다. OFF 또는 최초 근거 0건은 기존 동작을 유지해야 MUST 한다.

#### Scenario: Missing comparison target
- **WHEN** 모델이 첫 근거에서 비교 대상 누락을 확인하고 유효한 검색어를 호출한다
- **THEN** 시스템은 최대 2개 검색을 수행한 뒤 최종 근거로 답변한다

#### Scenario: Sufficient evidence or disabled mode
- **WHEN** 모델이 도구를 선택하지 않거나 기능이 OFF다
- **THEN** 추가 검색 없이 기존 근거로 답변하며 OFF에서는 판단 호출도 하지 않는다

#### Scenario: No initial evidence
- **WHEN** 최초 검색 근거가 0건이다
- **THEN** 추가 모델 호출 없이 기존 no-evidence 결과를 반환한다

### Requirement: Server-owned research authorization and validation
시스템은 최초 요청의 workspace_id와 요청자 JWT를 재사용하고 모델 인자로 접근 범위를 바꿀 수 없게 MUST 한다. 허용 도구와 query만 검증하고 1~500자 검색어 및 최대 호출 수를 실행 전에 검사해야 MUST 한다.

#### Scenario: Invalid tool batch
- **WHEN** 호출에 알 수 없는 도구·인자, 빈 검색어, 길이 초과 또는 3개 이상 호출이 포함된다
- **THEN** 전체 배치를 실행하지 않고 초기 근거로 진행하며 거부 이유를 기록한다

#### Scenario: Cross-tenant request
- **WHEN** 모델이 다른 workspace_id 또는 JWT 인자를 제공한다
- **THEN** 해당 호출은 거부되고 다른 테넌트의 검색·비용·근거가 발생하지 않는다

### Requirement: Evidence budget and stream continuity
시스템은 초기·추가 근거를 중복 제거해 병합하고 최종 토큰 예산을 적용한 뒤 서버 인용 별칭을 발급해야 MUST 한다. 도구 실행을 답변 스트리밍 전에 끝내고 기존 외부 SSE 순서를 유지해야 MUST 한다.

#### Scenario: Duplicate evidence and oversized context
- **WHEN** 추가 검색에 같은 근거와 예산보다 큰 본문이 반환된다
- **THEN** 최종 문맥에는 중복이 없고 기존 토큰 상한이 적용되며 포함 근거만 서버 별칭을 받는다

### Requirement: Research failure and cost visibility
시스템은 일반 판단·검색 실패와 시간 제한 시 완료된 허용 근거로 답변하고, 인증·권한·예산 오류는 기존 오류 계약을 따라야 MUST 한다. 취소를 전파하고 판단을 포함한 모든 유료 호출의 비용·불완전 사용량을 기존 회계에 반영해야 MUST 한다.

#### Scenario: Timeout or malformed decision
- **WHEN** 판단이 잘못되거나 추가 단계가 시간 제한에 도달한다
- **THEN** 추가 실행을 중단하고 보유 근거로 답변하며 원인과 실제 호출 수를 기록한다

#### Scenario: Authorization or budget denied
- **WHEN** 추가 단계에서 권한 또는 예산이 거부된다
- **THEN** 거부를 일반 검색 실패로 삼키지 않고 기존 오류 계약으로 종료한다

#### Scenario: Decision call consumed tokens without searching
- **WHEN** 판단 모델이 호출됐지만 도구를 선택하지 않거나 중단된다
- **THEN** 판단 호출의 비용과 불완전 여부도 회계와 eval에 포함된다
