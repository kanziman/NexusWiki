---
phase: 02
slug: security-spine-and-shared-domain
status: validated
nyquist_compliant: false
requirements_total: 15
covered: 12
manual_only: 3
created: 2026-08-07
---

# Phase 02 — Validation

> Nyquist 검증 커버리지: 요구사항별 자동 검증 존재 여부와 그 한계.

`nyquist_compliant: false`인 이유는 결함이 아니라 **manual-only 3건이 의도된 설계**이기
때문이다. 아래 §Manual-Only에 각각의 근거와 본래 담당 페이즈를 적었다.

---

## Test Infrastructure

| 종류 | 도구 | 설정 | 실행 |
|---|---|---|---|
| Python | pytest | 루트 `pyproject.toml` — `asyncio_mode="auto"`, `--import-mode=importlib`, `testpaths` 3곳 | `uv run pytest -q` |
| Dashboard | vitest | `apps/dashboard/vitest.config.ts` | `pnpm --dir apps/dashboard test` |
| SQL 계약 | psql | `supabase/tests/*.sql` | `bash scripts/verify_*.sh` |
| 정적 게이트 | ruff · shell grep | `.github/workflows/ci.yml` | PR 트리거 4잡 |

현재 규모: **pytest 147건** (이번 감사로 143 → 147), ruff exit 0.

⚠️ `--import-mode=importlib`는 취향이 아니다. 워크스페이스 멤버마다 같은 이름의 테스트
모듈(`test_settings.py` 등)이 생기므로 기본 prepend 모드에서는 basename 충돌로 수집이
깨진다 (02-02).

---

## Per-Requirement Map

| Req | Plan | 자동 검증 | Status |
|---|---|---|---|
| SEC-01 | 02-02 | `packages/core/tests/test_settings.py` | COVERED |
| SEC-02 | 02-03 | `apps/worker/tests/test_service_client.py` + ruff `TID251` | COVERED |
| SEC-03 | 02-09 | `scripts/ci_check_service_usage.sh` (CI 잡) | COVERED |
| SEC-04 | 02-03 | `apps/api/tests/test_user_db.py` | COVERED |
| SEC-05 | 02-09 | `scripts/ci_check_bundle_secrets.sh` (CI 잡) | COVERED |
| SEC-06 | 02-04 | `apps/api/tests/test_workspaces_isolation.py` | COVERED (로컬) · CI에서 skip |
| DOM-01 | 02-01 | — | **MANUAL-ONLY** |
| DOM-02 | 02-06 | `supabase/tests/0007_queue_functions.sql` via `scripts/verify_queue_functions.sh` | COVERED ← 이번에 메움 |
| DOM-03 | 02-06 | 〃 | COVERED ← 이번에 메움 |
| DOM-04 | 02-06 | 〃 | COVERED ← 이번에 메움 |
| DOM-05 | 02-05 | `packages/core/tests/test_tokenizer.py` | COVERED |
| DOM-06 | 02-05 | `packages/core/tests/test_tokenizer_db.py` (실제 DB) + `test_tokenizer.py` | COVERED ← 이번에 메움 |
| DOM-07 | 02-05 | `packages/core/tests/test_slug.py` | COVERED |
| DOM-08 | 02-07 | `apps/worker/tests/test_queue.py`, `test_handlers.py` | COVERED (로컬) · 통합분 CI skip |
| DOM-09 | 02-08 | `apps/worker/tests/test_queue_baseline.py` (계산 로직) | **MANUAL-ONLY** (실측) |

---

## Validation Audit 2026-08-07

| Metric | Count |
|--------|-------|
| Gaps found | 3 |
| Resolved | 2 |
| Escalated to manual-only | 1 |

### 메운 갭 1 — `0007` SQL 계약을 실행하는 러너가 없었다

`supabase/tests/0007_queue_functions.sql`은 존재하고 손으로 돌리면 통과했지만 **어떤 러너도
실행하지 않았다** — pytest도, CI도, 스크립트도. 코드상 유일한 참조가 `test_queue.py:6`의
**주석**이었다. 같은 위치의 `0005_storage_policies.sql`에는 러너가 있었다는 점이 비대칭을
드러낸다.

`scripts/verify_queue_functions.sh` 추가 (`verify_storage_policies.sh` 관례를 그대로 따름).

**공허하지 않음을 먼저 증명했다:** 스크래치패드 사본에서 잠금 소유자 단언을
(`v_rows <> 0` → `<> 1`) 뒤집어 실행 → **exit 3**(psql `ON_ERROR_STOP` 전파). 저장소의
마이그레이션·테스트 파일은 건드리지 않았다. 그 위에서만 정상 경로의 exit 0
(`queue_functions: ok`)을 신뢰한다.

### 메운 갭 2 — DOM-06 왕복이 DB를 쓰지 않았다

`test_tokenizer.py`의 `_phrase_matches`가 `phraseto_tsquery`의 `<->` 인접성을 **Python으로
재구현**하고 있었다. docstring이 정직하게 밝히고 있었으나, 시뮬레이션이 실제 Postgres와
어긋나도 테스트는 계속 green이다.

⚠️ 이것이 `CLAUDE.md`가 못박은 실패 형태다 — "색인 시점과 질의 시점 토크나이저가 동일해야
함, **불일치는 조용히 실패함**". 시뮬레이션은 그 불일치를 감지할 수 없는 위치에 있다.

`packages/core/tests/test_tokenizer_db.py` 추가 — 실제 `to_tsvector('simple', bigram(...))
@@ phraseto_tsquery('simple', bigram(...))` 왕복 4건:

- 유니코드 3형(NFC·NFD·전각) 교차 9쌍이 서로를 검색해 낸다
- 부분 문자열 질의가 매치한다
- **무관한 질의는 매치하지 않는다** — 모든 단언이 `t`로 나오는 공허한 테스트를 막는 장치
- 토큰 경계가 보존된다 — 교차 토큰 bigram `"어검"`은 매치하면 안 된다

기존 시뮬레이션 테스트는 **삭제하지 않았다.** 새 DB 테스트는 시뮬레이션을 현실에 정박시키는
추가물이며, 시뮬레이션 자체는 DB 없이 도는 빠른 회귀로 남는다.

로컬 스택 부재 시 `pytest.skip` (기존 `conftest.py:203` · `test_queue.py:482` 관례).
`to_tsquery`가 아니라 `phraseto_tsquery`만 쓴다 — bigram 문자열을 `to_tsquery`에 넣는 것은
문서화된 안티패턴이다.

---

## Manual-Only

| Req | 이유 | 본래 담당 |
|---|---|---|
| DOM-01 | 02-01은 **트랜스포트 결정을 위한 일회성 스파이크**다. `scripts/spike_db_transport.py`와 `docs/ops/db-transport-spike.md`가 근거이며, 결정(`decisions.db_transport` = rpc)이 잠긴 뒤에는 회귀 대상이 아니다. 계획 회귀는 Phase 4 `RTV-08`이 `EXPLAIN` 파싱으로 이어받는다 | Phase 4 `RTV-08` |
| DOM-09 | reap 기준선은 **배포 환경에서의 실측 관측**이다. `test_queue_baseline.py`가 계산 로직(최근접 순위, 표본 200 문턱, 콜드 분리)을 덮지만 측정 자체는 재현 가능한 단위 테스트가 아니다 | Phase 3 (LLM 잡 p99 재측정) |
| SEC-06 · DOM-08 통합분 | 러너에 Supabase 스택을 **세우지 않는 것이 02-09의 의도된 설계**다. 세우면 이 잡이 검증하는 대상이 애플리케이션이 아니라 "CLI가 러너에서 뜨는가"가 된다. `-rs`로 건너뛴 테스트를 파일·행·사유까지 인쇄하므로 skip이 조용히 사라지지는 않는다 | Phase 7 `OPS-04` (전수 스위트) |

---

## 알려진 한계

⚠️ **`verify_queue_functions.sh`와 `verify_storage_policies.sh` 둘 다 CI에 연결돼 있지
않다.** 기존 관례를 따른 결과이며 양쪽 모두 수동 게이트로 남는다. CI 연결은 별도 작업이고,
연결하려면 러너에 스택을 세워야 하므로 위 Manual-Only 3번 항목과 같은 판단이 걸린다.

⚠️ **두 러너 모두 SQL 실패 시 아무것도 인쇄하지 않고 종료한다** (명령 치환 + `set -e`로
psql의 stderr가 삼켜진다). 새 러너가 기존 것에서 그대로 물려받은 결함이다. 고칠 때는
둘을 함께 고쳐야 한다 — 한쪽만 고치면 관례가 갈라진다.

## Sign-Off

- 요구사항 15건 중 12건 자동 검증, 3건 manual-only (근거 기록됨)
- `uv run pytest -q` → **147 passed**
- `uv run ruff check apps packages` → **All checks passed**
- `bash scripts/verify_queue_functions.sh` → **exit 0** (`queue_functions: ok`)
- 구현 파일·마이그레이션 무변경 (`git diff --name-only supabase/migrations/` 빈 출력)
