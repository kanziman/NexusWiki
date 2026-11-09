## Purpose

저장된 실제 합성 답변을 현재 채점 규칙으로 다시 평가해 정답·이중 인용·거절 판정의 의도하지 않은 변경을 PR에서 발견한다. 외부 모델을 부르지 않으므로 출력 품질 자체의 회귀를 증명하는 관문과는 구분한다.

## ADDED Requirements

### Requirement: Offline replay verdict gate
관문은 저장된 합성 결과를 현재 채점기로 재채점하고 모든 문항의 기대 통과 여부와 실패 이유를 대조해야 MUST 한다. 차이가 하나라도 있으면 문항 id와 차이를 출력하고 0이 아닌 종료 코드를 반환해야 MUST 한다. 기존에 알려진 실패도 기대 판정에 포함해야 MUST 한다.

#### Scenario: Expected verdicts unchanged
- **WHEN** 모든 문항의 재채점 결과가 고정 기대 판정과 같다
- **THEN** 관문은 문항 수를 보고하고 성공한다

#### Scenario: Citation or refusal verdict regresses
- **WHEN** 인용·거절·정답 판정 또는 실패 이유가 기대값과 다르다
- **THEN** 해당 문항과 차이를 보고하고 실패한다

### Requirement: Complete and safe frozen corpus
fixture는 원본 sha256과 출처 설명, 고정 문항 id 목록, 허용된 채점 입력 필드와 기대 판정만 포함해야 MUST 한다. 자격증명·워크스페이스 id·원문 및 검색 근거는 포함하면 안 된다. 비어 있는 자료, 누락·중복·계획 밖 문항, 알 수 없는 필드, 잘못된 자료형은 실패해야 MUST 한다. 합성 답변 본문은 거절 재채점에 필요한 경우에만 허용한다.

#### Scenario: Missing or duplicate question
- **WHEN** 고정 문항과 실제 행이 일치하지 않거나 중복된다
- **THEN** 빈 성공으로 처리하지 않고 실패한다

#### Scenario: Unexpected private field
- **WHEN** 허용 목록 밖의 필드가 fixture에 있다
- **THEN** 해당 필드 이름을 보고하고 실패한다

### Requirement: Pull request execution without provider access
PR CI는 관문을 필수 실행 단계로 호출하고 실패를 전파해야 MUST 한다. 관문은 네트워크·모델·DB·자격증명 없이 실행해야 MUST 한다. 문서는 저장된 출력의 재채점만 검증하며 새 모델 출력·프롬프트 품질은 검증하지 못한다고 밝혀야 MUST 한다.

#### Scenario: Credentials unavailable
- **WHEN** 자격증명이 없는 환경에서 고정 fixture로 관문을 실행한다
- **THEN** 외부 호출 없이 판정을 완료한다
