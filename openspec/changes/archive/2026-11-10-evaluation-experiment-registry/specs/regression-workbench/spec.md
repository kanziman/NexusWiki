## Purpose

로그인 없는 공개 회귀 분석 화면이 커밋된 실험 스냅샷을 읽어, 실험 종류별 판정과 측정값, 판정 기준의 출처, 결정 기록을 읽기 전용으로 보여 주는 동작을 정의한다.

## ADDED Requirements

### Requirement: Static experiment snapshot only
`/showcase/regression`은 저장소에 커밋된 실험 스냅샷과 기존 공개 평가 기록만 빌드 시점에 읽어야 MUST 하며, 렌더링 중 DB·API·모델을 호출하면 안 된다. 스냅샷의 문자열은 실행 가능한 마크업으로 처리하면 안 된다.

#### Scenario: Offline rendering
- **WHEN** 공개 빌드로 페이지를 렌더링한다
- **THEN** DB 접근이나 모델 비용 없이 스냅샷만으로 실험 목록과 판정이 표시된다

#### Scenario: Untrusted snapshot text
- **WHEN** 스냅샷의 실험 제목이나 결정 근거에 HTML이 들어 있다
- **THEN** 실행되지 않고 글자 그대로 보인다

### Requirement: Experiments and local tools are separated
사이드바는 공개 실험 목록과 로컬 개발 도구를 다른 구역으로 보여 줘야 MUST 한다. 로컬 개발 도구 구역은 개발 모드에서만 보여야 MUST 하며, 내 검증의 실행과 이력은 그 구역의 한 항목이어야 MUST 한다. 새 검증 실행 서랍은 내 검증 화면 맨 위에만 있어야 MUST 하며, 다른 실험 화면에는 실행 서랍과 로컬 기록 안내가 보이면 안 된다.

#### Scenario: Public visitor
- **WHEN** 공개 배포에서 방문자가 페이지를 연다
- **THEN** 사이드바에는 재검색 실험과 Ask 반복 측정만 있고 로컬 개발 도구 구역은 없다

#### Scenario: Local run drawer placement
- **WHEN** 개발 모드에서 재검색 실험 화면을 본다
- **THEN** 실행 서랍과 "이 컴퓨터에 저장된 검사 기록" 안내가 보이지 않고, 내 검증 화면에서만 실행 서랍이 맨 위에 보인다

### Requirement: Compared run identity and roles
판정 영역은 후보와 기준선 각각의 역할 이름, 실행 이름, 실행 id, 코드 리비전, 실행 시각을 보여 줘야 MUST 한다. 질문별 변화의 이름은 기준선과 후보의 비교라는 뜻으로 설명돼야 MUST 하며, 시간 순서를 뜻하는 표현을 쓰면 안 된다.

#### Scenario: Research experiment roles
- **WHEN** 방문자가 재검색 실험을 연다
- **THEN** 후보는 도입 검토안 · `on`, 기준선은 현재 방식 · `off`로 각각의 리비전과 실행 시각과 함께 보인다

### Requirement: Adoption experiment verdict from its criteria
도입 실험 화면은 실험이 참조하는 기준 세트의 조건별 결과와 최종 판정을 보여 줘야 MUST 한다. 각 조건은 충족·미충족과 실제 값, 허용값을 보여야 MUST 하며, 화면 위쪽에 판정에 쓴 기준 세트의 이름·출처·기록 시각과 사전 등록 여부를 보여야 MUST 한다. 참고 판정이 있으면 공식 판정과 구분해 참고로 표시해야 MUST 한다. 결정 기록(상태·근거·날짜)을 읽기 전용으로 보여야 MUST 한다.

#### Scenario: Research verdict by original criteria
- **WHEN** 방문자가 재검색 실험을 연다
- **THEN** 원래 기준 6개 중 답변 복구 · 통과 증가 · 비용(+66.4%)이 미충족으로, 나머지 3개가 충족으로 보이고, 결정 상태는 미채택이다

#### Scenario: Provenance shown honestly
- **WHEN** 기준 세트의 출처 커밋 시각이 실행보다 늦다
- **THEN** 화면은 사전 등록이라고 표시하지 않고 "실행보다 먼저 기록됐음을 증명하지 못함"과 두 시각을 보여 준다

#### Scenario: Policy v1 reference
- **WHEN** 재검색 실험에 정책 v1 참고 판정이 있다
- **THEN** "정책 v1로 판정했다면 새로 실패 1개도 막는 조건"이 공식 판정과 구분된 참고 문구로 보인다

### Requirement: Measurement experiments show measurements, not adoption
안정성 측정과 채점 검증 화면은 채택 배지, 채택 조건 목록, 결정 기록을 보이면 안 된다. 대신 측정값 하나를 판정 영역 첫머리에 보여야 MUST 한다. 질문별 변화는 안정성 측정에서 흔들림, 채점 검증에서 판정 변화로 불러야 MUST 하며 회귀라고 부르면 안 된다.

#### Scenario: Stability measurement
- **WHEN** 방문자가 Ask 반복 측정 실험을 연다
- **THEN** 채택 배지와 비용·p95 허용 조건이 보이지 않고, 질문별 판정 일치 수와 흔들린 질문이 보인다

#### Scenario: Grader check in development
- **WHEN** 개발 모드에서 내 검증(채점 검증)을 연다
- **THEN** 채택 배지 없이 판정이 바뀐 질문 수가 보이고, 판정 변화가 없으면 채점 규칙을 바꾸지 않았을 때 정상이라는 설명이 함께 보인다

### Requirement: Read-only policy view
화면은 채택 정책 v1과 각 기준 세트의 조건 전문을 읽기 전용으로 펼쳐 볼 수 있게 해야 MUST 한다. 방문자가 허용 기준값을 바꾸는 입력은 없어야 MUST 하며, 판정은 방문자 입력이나 브라우저 저장값에 따라 바뀌면 안 된다.

#### Scenario: No threshold input
- **WHEN** 방문자가 도입 실험 화면의 모든 영역을 펼친다
- **THEN** 허용 비용·p95를 바꾸는 입력칸이 없고, 정책 버전과 조건 전문만 보인다

#### Scenario: Stale browser values ignored
- **WHEN** 이전 버전이 남긴 기준값과 검토 메모가 브라우저 저장소에 있다
- **THEN** 화면 판정과 표시는 스냅샷만 따르고 저장값을 읽거나 쓰지 않는다

### Requirement: Snapshot download matches the page
방문자는 화면이 읽은 실험 스냅샷을 그대로 JSON으로 내려받을 수 있어야 MUST 한다.

#### Scenario: Download
- **WHEN** 방문자가 실험 스냅샷 JSON 링크를 연다
- **THEN** 화면 렌더링에 쓴 것과 같은 스냅샷이 내려온다
