## ADDED Requirements

### Requirement: Paired evidence research evaluation
평가 도구는 같은 문서·위키·청크·임베딩·모델 설정·프롬프트·검색 정책·질문 fixture에서 OFF/ON 1쌍을 실행하고 조건 해시와 양쪽 revision을 기록해야 MUST 한다. 사용자 비용 절감 요청으로 완료된 첫 쌍만 사용하며 반복 안정성은 미측정으로 표시해야 MUST 한다. 문항과 판정 기준은 ON 결과 확인 전에 고정해야 MUST 한다. 조건 불일치는 유효 비교로 표시하면 안 된다. 기존 30문항 회귀 및 비교형 6개·표현 불일치 6개를 포함해야 MUST 한다.

#### Scenario: Matched pair
- **WHEN** 두 실행의 비교 조건 해시가 모두 일치한다
- **THEN** 질문별 결과와 품질·전체 비용·토큰·총 지연 및 첫 답변 토큰 지연 p50/p95를 비교한다

#### Scenario: Corpus or policy changed
- **WHEN** 문서 또는 정책 등 고정 조건 해시가 다르다
- **THEN** 결과를 조건 불일치로 기록하고 개선 근거로 사용하지 않는다

#### Scenario: Decision implementation changed during resume
- **WHEN** 판단 프롬프트·출력 상한을 포함한 실행 코드가 원본 기록 또는 서버 시작 시점과 다르거나 그 지문이 없다
- **THEN** 재개를 거부하고 해당 기록을 동일 조건의 유효 비교로 표시하지 않는다

### Requirement: Recovery scoring uses missing initial evidence
평가 도구는 실제 초기 문맥에서 기대 문서 전체를 확보하지 못한 전용 문항을 복구 대상 분모로 SHALL 사용한다. 최종 문맥의 전체 기대 문서 확보와 필수 사실·이중 인용을 통과한 답변 복구를 별도로 보고해야 MUST 한다. 장애와 측정 누락을 성공으로 세면 안 된다.

#### Scenario: Missing target recovered
- **WHEN** 초기 문맥에 없던 기대 문서가 최종 문맥에 포함되고 답변 판정도 통과한다
- **THEN** 해당 문항은 근거 복구와 답변 복구에 각각 집계된다

#### Scenario: No eligible initial failures
- **WHEN** 초기 문맥이 모든 전용 문항의 기대 문서를 확보했다
- **THEN** 복구 분모는 0이고 복구율은 미측정이며 복구 효과를 주장하지 않는다
