# Spec Conformance 리뷰 — offline-eval-regression-gate r1

- 판정: needs_fix
- 대상: `a6191e2` 위 미커밋 작업 트리의 회귀 관문 CLI·fixture·테스트·CI·평가 지도. eval-reliability의 별도 변경은 제외.
- 일시: 2026-11-08
- 새 검증: `UV_CACHE_DIR=/private/tmp/nexuswiki-uv-cache uv run --offline pytest apps/worker/tests/test_eval_regression_gate.py` — 12개 통과. 실제 fixture와 사설 필드 주입을 별도 실행해 아래 미충족을 재현했다.

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Offline replay verdict gate / Expected verdicts unchanged | 충족 | `scripts/check_eval_regression.py:84`에서 현재 verdict와 기대값 비교, `:103` 문항 수 출력. 테스트 `test_eval_regression_gate.py:26`, `:73` |
| Offline replay verdict gate / Citation or refusal verdict regresses | 충족 | `scripts/check_eval_regression.py:85` 차이 수집, `:100` 종료 코드 1. 테스트 `test_eval_regression_gate.py:39` 인용·키워드·거절·이유 변조 및 `:73` 실제 CLI 실패 |
| Complete and safe frozen corpus / Missing or duplicate question | 충족 | `scripts/check_eval_regression.py:50` 비어 있는 계획과 중복 거부, `:57` 개수 대조, `:64` 계획 밖·중복 거부. 테스트 `test_eval_regression_gate.py:54` |
| Complete and safe frozen corpus / Unexpected private field | 부분 미충족 | `scripts/check_eval_regression.py:61`에서 거부하지만 `:62` 메시지에 필드 이름이 없다. `workspace_id` 주입 시 `행 필드가 허용 목록과 다르다`만 출력 |
| Complete and safe frozen corpus / 요구 본문: 거절 재채점에 필요한 경우만 답변 본문 허용 | 미충족 | `scripts/fixtures/eval_regression.v1.json:42`부터 일반 문항의 전체 답변이 저장돼 있다. 별도 집계 결과 doc != none인 29개 문항 모두 비어 있지 않은 answer를 포함한다. 현재 `ask_replay.verdict`는 일반 문항 답변 본문을 읽지 않으며 `check_eval_regression.py:67`은 모든 행의 answer 문자열을 필수로 요구한다 |
| Pull request execution without provider access / Credentials unavailable | 충족 | `scripts/check_eval_regression.py:95` 로컬 파일만 읽고 순수 판정 함수 호출. 네트워크 차단 테스트 `test_eval_regression_gate.py:26`. `.github/workflows/ci.yml:173` 기존 pytest 잡 안의 필수 실행 단계이며 실패 무시 설정 없음 |
| Pull request execution without provider access / 한계 문서 | 충족 | `docs/ops/evaluation-map.md:56`, `:58` 저장된 출력 재채점과 새 생성 출력 품질 검증의 차이를 명시 |

## 조치가 필요한 항목

1. **불필요한 일반 문항 답변 본문 제거** — fixture의 29개 일반 문항 답변은 거절 재채점에 필요하지 않으므로 계약이 허용하지 않는다. 일반 문항에서는 answer를 제외하거나 빈 값으로 제한하고, 거절 문항에만 필요한 본문을 보존한다. 검사기에서도 그 제한을 검증하고 회귀 테스트를 추가한다. 원본 sha256은 원본 파일 기준 그대로 유지한다.
2. **알 수 없는 필드 이름을 오류에 포함** — 최상위·행·기대 판정의 알 수 없는 필드를 이름으로 출력해야 한다. `workspace_id` 주입 시 오류 메시지에 필드 이름이 포함되는 테스트를 추가한다. 값은 출력할 필요가 없다.

## 판정 근거

주요 재채점 및 실패 전파 동작은 구현됐고 테스트도 통과한다. 다만 fixture의 답변 본문 최소화와 알 수 없는 필드 이름 보고라는 명시 계약 두 항목이 충족되지 않았다. 둘 다 현재 스펙 범위 안에서 fixture·검사기·테스트를 수정할 수 있으므로 `needs_fix`다. 아직 미완료로 표시된 아카이브·최종 커밋은 이번 구현 리뷰의 지적 대상에서 제외했다.

## 2026-11-09 추가 확인

부모 에이전트의 재확인 요청에 따라 canonical fixture의 문항·doc 대조가 추가된 현재 코드를 다시 읽고 같은 테스트 명령을 새로 실행했다. 14개 테스트가 통과했다. 이 보강은 계획 목록과 결과를 함께 줄이는 누락을 막지만, 위 두 지적에는 변경이 없다. 일반 문항의 비어 있지 않은 답변은 여전히 29개이며 `workspace_id` 주입 오류에도 필드 이름이 나오지 않는다. 구현 수정 전 동일 지적의 추가 확인이므로 새 리뷰 라운드로 세지 않으며 r1 판정은 `needs_fix`로 유지한다.
