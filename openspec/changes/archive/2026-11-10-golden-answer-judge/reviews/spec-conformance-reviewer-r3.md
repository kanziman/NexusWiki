# 스펙 부합 리뷰 3차

판정: **pass**

## 검토 범위

이전 2차 리뷰 이후 추가된 실제 답변·생성 당시 근거 가져오기, `/showcase/review` 집중 검토 화면, 대화형 AI의 별도 추가 검토, 심사 응답 포장 및 잘못된 인용 구간 처리 변경을 `golden-answer-evaluation` 스펙과 대조했다. 랜딩페이지 문구는 이번 머지 범위에서 제외했다. 테넌트 격리 리뷰는 기존 사용자 요청에 따라 생략했다.

## 확인 결과

- 실제 답변 가져오기는 등록된 제품 재생 출처, 동일 데이터셋 지문과 문항 지문을 확인한다. 표본 지문에는 답변과 생성 당시 제공 근거 맵이 포함되므로 답변 또는 근거가 바뀌면 과거 사람 판정을 자동 재사용하지 않는다. 누락된 과거 인용 근거를 정답 문서로 복원하지 않는다.
- 별도 AI 검토는 `ai-review-*.json`에서만 읽고 데이터셋·표본·판정 기준 지문을 확인한다. `reviews`나 유료 심사 `results`를 덮어쓰지 않으며, 사람 일치도 집계 인자에도 포함하지 않는다. 화면은 AI 검토임을 명시하고 사람 선택지를 채우지 않는다.
- 단일 JSON 코드블록은 포장만 제거한다. 입력에 없는 답변·근거 인용 구간은 검증된 통과로 남지 않고 해당 지표가 검토 필요가 된다. 자유 설명문에서 JSON을 추측 추출하지 않는다.
- 집중 검토 화면은 기존 로컬 판정 저장 API와 입력 지문·개정 충돌 계약을 공유한다. 조회만으로 모델을 호출하지 않고, 근거 없는 과거 답변은 누락 안내를 표시한다. 작성 중 문항·답변 전환을 막고 저장 실패 시 작성 내용을 보존한다.
- 운영 환경의 실행·저장 차단은 기존 프록시 경계가 계속 담당한다. 추가 화면이 별도 쓰기 우회 경로를 만들지 않는다.

## 새로 실행한 검증

- `.venv/bin/pytest -q apps/worker/tests/test_golden_answer_judge.py apps/worker/tests/test_golden_answer_import.py apps/worker/tests/test_local_evaluation_server.py`: **27 passed**.
- dashboard의 `vitest run tests/GoldenJudgePanel.test.tsx tests/GoldenReviewPage.test.tsx tests/LocalEvaluation.test.tsx`: **20 passed**.

검토한 변경에서 머지를 막을 스펙 불일치를 발견하지 않았다. 이 판정은 AI 채점 결과의 실제 정확도나 사람 검토 완료를 인증하는 판정이 아니다. 개인 로컬 답변·심사·사람 판정 데이터는 Git 커밋 대상이 아니다.
