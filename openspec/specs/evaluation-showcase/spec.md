# evaluation-showcase Specification

## Purpose

포트폴리오 방문자가 NexusWiki의 Ask 품질을 무엇으로 어디까지 쟀는지, 어떤 측정이 아직 비어 있는지를 한 화면에서 확인하게 한다. 모든 숫자는 분모 · 회차 · 실행 경로 · 한계와 함께 보여, 합성 샘플 한 번의 결과가 운영 성과나 안정성 보장으로 읽히지 않게 한다.

## Requirements

### Requirement: Public evaluation overview page
시스템은 로그인 없는 `/showcase/evaluation` 페이지에서 평가 지도 · 반복 측정 · 거절 성능 · 적용 원장 · 재현 조건과 한계의 다섯 구역을 보여줘야 MUST 한다. 페이지 첫머리에 결론 한 줄과 합성 샘플(문서 수 · 질문 수)이라는 사실을 함께 표시해야 MUST 한다. 세션이 있는 방문자도 같은 내용을 봐야 MUST 하며, 페이지는 기존 `controlled-ai` · `evidence-research` 쇼케이스로 연결되고 두 쇼케이스도 이 페이지로 연결돼야 MUST 한다.

#### Scenario: Anonymous visitor opens the page
- **WHEN** 로그인하지 않은 방문자가 `/showcase/evaluation`을 연다
- **THEN** 다섯 구역과 결론 한 줄, 합성 샘플 경고가 보이고 로그인 화면으로 이동하지 않는다

#### Scenario: Navigating between showcases
- **WHEN** 방문자가 `controlled-ai` 또는 `evidence-research` 쇼케이스를 연다
- **THEN** 이 페이지로 가는 링크가 있고, 이 페이지에서도 두 쇼케이스로 가는 링크가 있다

### Requirement: Evaluation map shows every measurement surface
평가 지도는 공개 기록에 있는 모든 측정면을 상태(잰 것 · 일부만 · 비어 있음)와 함께 보여줘야 MUST 한다. 수치가 있는 측정면은 수치 · 분모 · 측정일 · 출처를 함께 보여줘야 MUST 하며, 분모나 측정일 없이 비율만 보여주면 안 된다. 비어 있는 측정면은 숨기지 않고 왜 비어 있는지를 보여줘야 MUST 한다.

#### Scenario: Measured surface
- **WHEN** 공개 기록의 한 측정면에 수치가 있다
- **THEN** 그 칸은 상태 · 수치 · 분모 · 측정일 · 출처를 함께 보인다

#### Scenario: Empty surface
- **WHEN** 공개 기록의 한 측정면이 비어 있음 상태다
- **THEN** 그 칸은 비어 있음 상태와 이유를 보이고 수치를 보이지 않는다

### Requirement: Repetition grid distinguishes runs, paths, and non-runs
반복 측정 구역은 문항 × 회차마다 통과 · 실패 · 미실행을 구분해 보여줘야 MUST 하고, 회차마다 실행 경로(HTTP 또는 하네스)를 표시해야 MUST 한다. 문항마다 안정성(안정 통과 · 안정 실패 · 흔들림 · 미실행)을 보여줘야 MUST 한다. 회차별 답할 수 있는 문항 통과 수와 95% 구간, 회차 사이 최소 · 최대를 보여줘야 MUST 하며, 경로가 섞인 묶음은 HTTP 회차만의 값을 함께 보여줘야 MUST 한다. 회차를 합친 신뢰 구간을 보여주면 안 된다. 알려진 실패는 사람이 정한 보고 단계와 자동 판정 단계를 함께 보여줘야 MUST 한다. 미실행 칸을 실패로 표시하면 안 된다.

#### Scenario: Known failure across all runs
- **WHEN** q06이 세 회차 모두 실패하고 라벨이 질문 모호성 · 자동 단계가 검색 미적중이다
- **THEN** q06 행은 세 칸 모두 실패, 안정 실패로 표시되고 보고 단계 질문 모호성과 자동 단계 검색 미적중을 함께 보인다

#### Scenario: Mixed execution paths
- **WHEN** 묶음이 HTTP 2회와 하네스 1회로 이뤄져 있다
- **THEN** 회차마다 경로가 보이고 전체 값과 HTTP 회차만의 값이 둘 다 보인다

#### Scenario: Partially executed run
- **WHEN** 한 회차가 일부 문항에서 멈췄다
- **THEN** 실행하지 않은 문항 칸은 미실행으로 보이고 실패 수에 들어가지 않는다

### Requirement: Refusal figures shown apart from pass rate
거절 성능 구역은 회차마다 답할 수 있는 문항 통과 · 정확한 거절 · 잘못된 거절을 각각 분모와 함께 보여줘야 MUST 한다. 거절 문항이 없는 회차의 정확한 거절은 0이 아니라 없음으로 보여줘야 MUST 한다. 거절 표본 수를 정확한 거절 옆에 보여줘야 MUST 한다.

#### Scenario: One unanswerable question
- **WHEN** 회차가 답할 수 있는 29문항 중 28개를 통과하고 거절 1문항을 정확히 거절했다
- **THEN** 그 회차는 28/29 · 정확한 거절 1/1 · 잘못된 거절 0/29를 보이고 거절 표본이 1개임을 보인다

### Requirement: Application ledger in date order
적용 원장 구역은 공개 기록의 항목을 날짜순으로 보여줘야 MUST 하고, 항목마다 적용한 평가 기법 · NexusWiki에서 한 일 · 측정이 바꾼 것 · 증거 위치를 보여줘야 MUST 한다. 측정이 바꾼 것이 없는 항목은 공개 기록에 넣으면 안 된다.

#### Scenario: Ledger entry rendered
- **WHEN** 공개 기록에 날짜 · 기법 · 적용 · 증거 · 측정이 바꾼 것을 가진 항목이 있다
- **THEN** 그 항목이 날짜순 위치에 다섯 정보와 함께 보인다

### Requirement: Reproduction conditions and limits stay attached
재현 조건과 한계 구역은 고정 입력 지문(수집 스냅샷 · 질문 fixture · 답변 프롬프트) · 모델 · 검색 정책 · 근거 수 · 측정 비용을 보여줘야 MUST 한다. 합성 샘플이라 운영 성과가 아니라는 점, 회차 수와 회차가 독립 표본이 아니라는 점, 흔들림 0이 안정성 보장이 아니라는 점, 거절 표본 수를 한계로 보여줘야 MUST 한다.

#### Scenario: Limits visible with results
- **WHEN** 방문자가 반복 측정 결과를 본다
- **THEN** 같은 페이지에서 회차 수 · 독립 표본 아님 · 흔들림 0의 의미 · 거절 표본 수 · 합성 샘플 한계를 확인할 수 있다

### Requirement: Static allowlisted public evaluation record
페이지는 저장소에 커밋된 버전 있는 공개 평가 기록만 빌드 시점에 읽어야 MUST 하며, 운영 DB · API · 모델을 호출하거나 운영 데이터 클라이언트를 사용하면 안 된다. 공개 기록에는 허용한 필드만 들어가야 MUST 하며 자격증명 · workspace 식별자 · 사용자 식별자 · 공급자 generation id · 답변 본문 · 운영 본문을 넣으면 안 된다. 기록 문자열은 실행 가능한 마크업으로 처리하면 안 된다. 방문자는 페이지가 읽은 공개 기록을 그대로 JSON으로 내려받을 수 있어야 MUST 한다.

#### Scenario: Offline rendering
- **WHEN** 페이지를 빌드하고 렌더링한다
- **THEN** 모델 비용이나 운영 데이터 접근 없이 공개 기록만으로 표시된다

#### Scenario: Untrusted record text
- **WHEN** 공개 기록의 질문 문구나 원장 설명에 HTML이 들어 있다
- **THEN** 실행되지 않고 글자 그대로 보인다

#### Scenario: Forbidden field in record
- **WHEN** 공개 기록에 허용 목록 밖의 필드나 workspace 식별자 · 답변 본문이 들어 있다
- **THEN** 검사가 실패하고 그 기록은 공개되지 않는다

#### Scenario: Download matches the page
- **WHEN** 방문자가 공개 JSON 링크를 연다
- **THEN** 페이지가 렌더링에 쓴 것과 같은 공개 기록이 내려온다

### Requirement: Invalid or missing measurements are not presented as results
공개 기록의 반복 측정 묶음이 유효하지 않거나(묶음 키 불일치 등) 측정값이 없으면, 페이지는 해당 구역을 미측정 또는 무효로 표시해야 MUST 하며 수치 요약을 보여주면 안 된다.

#### Scenario: Series marked invalid
- **WHEN** 공개 기록의 반복 측정 묶음이 무효로 표시돼 있다
- **THEN** 반복 측정 구역은 무효와 그 이유를 보이고 통과 수 · 구간 · 안정성 요약을 보이지 않는다

#### Scenario: Map and conclusion follow an invalid series
- **WHEN** 공개 기록의 반복 측정 묶음이 무효로 표시돼 있다
- **THEN** 결론 한 줄과 평가 지도의 최종 답 정답성 · 거절 칸도 무효를 보이고 반복 측정 수치를 보이지 않는다
