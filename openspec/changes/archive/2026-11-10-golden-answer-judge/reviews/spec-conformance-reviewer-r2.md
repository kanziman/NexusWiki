# 스펙 부합 리뷰 2차

판정: **pass**

검토 범위는 1차와 동일하며, 지적한 네 항목과 관련 회귀 테스트를 재검토했다. 테넌트 격리 리뷰는 사용자 요청에 따라 생략했다.

## 1차 지적 해결 확인

- 호출 전 `in_flight`, 시도 수와 미실행 목록을 원자 저장한다. 재시작 시 응답이 없는 호출은 비용 미관측 오류 표본으로 보존하고 실제 미시작 표본만 `not_run`에 남긴다. KeyboardInterrupt 회귀 테스트로 호출 도중 중단을 재현한다.
- 작업 생성 시 표본별 질문·기대 사실·답변·정답 근거·제공 근거 맵 전체를 `inputs`로 보존하고 실제 system prompt와 데이터셋·심사 기준·모델 설정도 기록한다. 실행은 보존한 packet을 사용한다.
- 사람 검토 폼은 편집 개정 번호를 고정한다. 백그라운드 갱신으로 다른 개정이 들어오면 제출을 차단하고, 명시적 재검토 동작에서 작성 상태를 초기화한다. 갱신 callback을 실행하는 UI 테스트로 자동 개정 승격이 없는 것을 확인한다.
- OpenRouter 응답의 빈 choices, 잘못된 message 또는 비문자열 content가 있어도 이미 관측한 비용을 반환한다. HTTP MockTransport 테스트로 비용 17 micros가 유지되는지 검증한다.

## 새로 실행한 검증

- `.venv/bin/pytest -q apps/worker/tests/test_golden_answer_judge.py apps/worker/tests/test_local_evaluation_server.py`: **23 passed**.
- dashboard의 `vitest run tests/GoldenJudgePanel.test.tsx tests/LocalEvaluation.test.tsx`: **13 passed**.

검토한 범위에서 수정이 필요한 스펙 부합 결함을 추가로 발견하지 않았다. 골든셋은 미검토 후보, 실제 사람 판정과 실제 유료 심사 정확도는 미검증 상태라는 제품 표시·보고 원칙을 유지한다. 이 판정은 평가기의 실제 정확도나 운영 배포 완료를 뜻하지 않는다.
