# Spec Conformance 리뷰 — offline-eval-regression-gate r2

- 판정: pass
- 대상: `a6191e2` 위 미커밋 작업 트리의 회귀 관문 CLI·fixture·테스트·CI·평가 지도. 같은 작업 트리의 eval-reliability 변경은 제외.
- 일시: 2026-11-09
- 새 검증(이번 라운드에서 직접 재실행):
  - `UV_CACHE_DIR=/private/tmp/nexuswiki-uv-cache uv run --offline pytest -q apps/worker/tests/test_eval_regression_gate.py` — 19개 통과
  - `uv run --offline python scripts/check_eval_regression.py` — `합성 답변 30문항의 고정 판정 일치`, 종료 코드 0
  - `openspec validate offline-eval-regression-gate --strict` — valid
  - 원본 `.worktrees/rrf-evidence-20261108/valid-after/ask-after-valid.json`의 sha256이 fixture `source_sha256`(`f3a8c416…b2ea`)과 일치
  - 행에 `workspace_id: "SECRETVAL"`을 주입한 fixture로 CLI 실행 → `회귀 관문 입력 오류: 행: 알 수 없는 필드 ['workspace_id'], 누락 필드 []`, 종료 코드 2. 값은 출력되지 않음

## r1 지적 대응 확인

| r1 항목 | 결과 | 증거 |
| --- | --- | --- |
| 1. 일반 문항 답변 본문 제거 | 해소 | fixture 집계: `doc != "none"` 29개 행의 answer는 전부 빈 문자열, 거절 문항 q30 한 개만 본문 보존. 검사기 `scripts/check_eval_regression.py:87-88`이 일반 문항의 비어 있지 않은 answer를 `{qid}: 일반 문항의 답변 본문은 저장하지 않는다`로 거부. 테스트 `apps/worker/tests/test_eval_regression_gate.py:94`(주입 시 문항 id 포함 오류), `:101`(fixture 불변식). 일반 문항 판정은 `scripts/ask_replay.py:191-204`에서 answer를 읽지 않으므로 본문 제거가 판정을 바꾸지 않음(실제 fixture 30문항 일치로 확인) |
| 2. 알 수 없는 필드 이름 보고 | 해소 | `scripts/check_eval_regression.py:31-38` `require_fields`가 알 수 없는·누락 필드 **이름**만 출력. 최상위(`:43-53`)·행(`:78`)·기대 판정(`:98`) 세 곳 모두 이 함수를 거침. 테스트 `test_eval_regression_gate.py:80-91`이 fixture/row/expected 3경우에 이름 포함·값 미포함을 단언 |

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Offline replay verdict gate / Expected verdicts unchanged | 충족 | `scripts/check_eval_regression.py:103-105` 현재 `verdict`와 기대값 대조, `:122` 문항 수 보고 후 0 반환. 기존 실패 포함은 테스트 `test_eval_regression_gate.py:35`(`expected.pass == False` 행 존재). 테스트 `:26`, `:109-114` |
| Offline replay verdict gate / Citation or refusal verdict regresses | 충족 | `scripts/check_eval_regression.py:105` 문항 id와 기대/현재 차이 수집, `:119-121` 출력 후 종료 코드 1. 테스트 `test_eval_regression_gate.py:39-51`(인용·정답·거절·실패 이유 4종 변조), `:115-118`(CLI 종료 코드 1과 `q01` 출력) |
| Complete and safe frozen corpus / Missing or duplicate question | 충족 | `scripts/check_eval_regression.py:63-69` 빈·형식 오류·중복 계획 거부, `:70-71` 개수 대조, `:74-75` 정본 질문 fixture와 대조(계획·결과 동시 축소 차단), `:80-81` 계획 밖·중복 행 거부, `:83-84` doc 분류 변경 거부. 테스트 `test_eval_regression_gate.py:54-77`(missing·duplicate·extra·empty·both·doc 등 8종) |
| Complete and safe frozen corpus / Unexpected private field | 충족 | `scripts/check_eval_regression.py:35-38` 필드 이름 보고, CLI `:116-118`에서 종료 코드 2. 테스트 `test_eval_regression_gate.py:80-91`, 직접 재현 결과 위 「새 검증」 참조 |
| Complete and safe frozen corpus / 요구 본문: 허용 필드만·답변 본문은 거절 재채점에 필요한 경우만·잘못된 자료형 실패 | 충족 | 최상위 키는 `version, source, source_sha256, question_ids, rows`, 행 키는 `ROW_FIELDS`(`:17-28`)와 정확히 일치하도록 강제. fixture 문자열에 워크스페이스 id·JWT·원문 청크·검색 근거 필드 없음. 자료형 검증 `:54-61`, `:85-102`, 테스트 `:67`(`type`). 답변 본문 제한은 위 r1 항목 1 |
| Pull request execution without provider access / Credentials unavailable | 충족 | 검사기는 로컬 fixture와 `DEFAULT_SAMPLE`만 읽고 순수 함수 `verdict` 호출(`:72`, `:103`, `:114`). 테스트 `test_eval_regression_gate.py:26-33`이 `socket.connect`를 차단한 상태로 통과 |
| Pull request execution without provider access / 요구 본문: CI 필수 단계·실패 전파 | 충족 | `.github/workflows/ci.yml:173-174` 기존 `pytest` 잡의 별도 단계로 실행, 워크플로 전체에 `continue-on-error` 없음. 테스트 `test_eval_regression_gate.py:109-120`이 종료 코드 0/1/2 전파 확인 |
| Pull request execution without provider access / 요구 본문: 한계 문서 | 충족 | `docs/ops/evaluation-map.md:56` 관문 범위(저장된 30문항 재채점, sha256·허용 필드, 외부 의존 없음), `:58` 새로 생성될 답변 품질은 검증하지 못하며 별도 유료 실측이 필요하다고 명시 |

## 조치가 필요한 항목

없음.

참고(지적 아님): tasks 1.1~1.3 체크박스, delta 동기화·아카이브·커밋은 호출자 지시에 따라 이번 리뷰 범위에서 제외했다. 구현이 끝났으므로 1.1·1.2는 체크해도 되는 상태이고, 1.3은 sync·archive 후에 처리하면 된다.

## 판정 근거

delta spec의 3개 Requirement와 4개 Scenario, 그리고 Requirement 본문의 MUST 조항(기존 실패 포함, 허용 필드 한정, 답변 본문 최소화, CI 필수 실행, 한계 문서화)이 모두 코드 경로와 테스트로 확인된다. r1의 두 지적(일반 문항 답변 본문 저장, 알 수 없는 필드 이름 미보고)은 fixture·검사기·회귀 테스트로 해소됐고, 이번 라운드에서 직접 재실행해 확인했다. 스펙 밖의 사용자 관찰 동작 추가는 없다. 그래서 판정은 `pass`다.
