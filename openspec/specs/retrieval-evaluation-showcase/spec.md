# retrieval-evaluation-showcase Specification

## Purpose

합성 문서에서 수행한 제한된 도구 재검색의 적용 전후 결과와 재현 조건을 포트폴리오 방문자가 확인하고, 품질 개선 여부와 비용·지연의 대가를 함께 판단할 수 있게 한다.

## Requirements

### Requirement: Public evidence research comparison page
시스템은 로그인 없는 /showcase/evidence-research 페이지에서 실제 OFF/ON 실행의 비교 조건·문항별 결과·복구 및 회귀·품질·비용·지연·채택 판정을 보여줘야 MUST 한다. 합성 평가라는 사실과 표본·반복 횟수·판정 방법·한계를 표시하고 기존 controlled-ai 소개 페이지에서 연결해야 MUST 한다.

#### Scenario: Published matched evaluation
- **WHEN** 방문자가 결과 페이지를 연다
- **THEN** 조건 일치 여부와 OFF/ON 요약, 문항별 전후 결과, 평가 방법 및 공개 JSON 다운로드를 확인할 수 있다

#### Scenario: No valid result
- **WHEN** 측정값이 없거나 실행 조건이 다르다
- **THEN** 미측정 또는 조건 불일치를 표시하고 개선 수치로 오인할 요약을 제공하지 않는다

### Requirement: Static allowlisted synthetic evaluation data
결과 페이지는 명시적으로 허용한 합성 평가 데이터만 읽고 운영 DB·API·모델을 호출하지 않아야 MUST 한다. 공개 export에는 자격증명·workspace 식별자·공급자 generation id·운영 본문을 포함하면 안 된다. 결과 문자열은 실행 가능한 마크업으로 처리하면 안 된다.

#### Scenario: Offline result rendering
- **WHEN** 페이지를 빌드하고 결과를 렌더링한다
- **THEN** 모델 비용이나 운영 데이터 접근 없이 버전 있는 공개 평가 기록으로 표시한다

#### Scenario: Untrusted result text
- **WHEN** 합성 질문 또는 판정 이유에 HTML이 포함된다
- **THEN** 실행하지 않고 텍스트로 표시한다
