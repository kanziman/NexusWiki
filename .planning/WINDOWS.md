---
schema_version: 1
open_count: 4
waived_count: 0
fixed_count: 0
total_count: 4
last_updated: 2026-08-07T05:52:49.323Z
---

# Broken Windows Ledger

> Cross-phase defect register. `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 02 | deviation | supabase/tests/0004_loosened_rls_violation.sql |  | 위반 픽스처가 SELECT 정책까지 풀어야 fail-first가 red가 된다 — 정책 하나만 푸는 격리 회귀 재현은 workspaces 표면에서 성립하지 않는다 | open |  | 2026-08-06T16:07:34.615Z |  |
| 2 | 02 | deviation | apps/worker/src/worker/queue.py |  | 미등록 job type이 한 번에 dead가 되지 않는다 — 0003/0007에 즉시 dead 프리미티브가 없어 fail_job(backoff=0)으로 max_attempts 안에 수렴시킨다. 0008의 dead_letter_job()이 이 자리를 닫는다 | open |  | 2026-08-06T16:27:18.424Z |  |
| 3 | 02 | unmet-truth | docs/ops/reap-timeout-baseline.md |  | 프로브 워크스페이스 정리 미확인 — jobs에 DELETE 권한이 없어 219여 건의 프로브 잡 행이 그 워크스페이스 삭제 cascade로만 정리된다 (02-08) | open |  | 2026-08-07T05:52:49.206Z |  |
| 4 | 02 | unmet-truth | apps/worker/src/worker/queue_baseline.py |  | failures 1건의 원인 미상 — 프로브가 인큐 실패·claim 0행·남의 잡 claim·complete 0행을 카운터 하나로 뭉쳐 세고 사유를 로그로 남기지 않는다. 사유별 분리가 Phase 3 재측정의 선행 과제 (02-08) | open |  | 2026-08-07T05:52:49.323Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "02",
    "file": "supabase/tests/0004_loosened_rls_violation.sql",
    "line": null,
    "description": "위반 픽스처가 SELECT 정책까지 풀어야 fail-first가 red가 된다 — 정책 하나만 푸는 격리 회귀 재현은 workspaces 표면에서 성립하지 않는다",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-06T16:07:34.615Z",
    "resolved_at": null
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "02",
    "file": "apps/worker/src/worker/queue.py",
    "line": null,
    "description": "미등록 job type이 한 번에 dead가 되지 않는다 — 0003/0007에 즉시 dead 프리미티브가 없어 fail_job(backoff=0)으로 max_attempts 안에 수렴시킨다. 0008의 dead_letter_job()이 이 자리를 닫는다",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-06T16:27:18.424Z",
    "resolved_at": null
  },
  {
    "id": 3,
    "kind": "unmet-truth",
    "phase": "02",
    "file": "docs/ops/reap-timeout-baseline.md",
    "line": null,
    "description": "프로브 워크스페이스 정리 미확인 — jobs에 DELETE 권한이 없어 219여 건의 프로브 잡 행이 그 워크스페이스 삭제 cascade로만 정리된다 (02-08)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-07T05:52:49.206Z",
    "resolved_at": null
  },
  {
    "id": 4,
    "kind": "unmet-truth",
    "phase": "02",
    "file": "apps/worker/src/worker/queue_baseline.py",
    "line": null,
    "description": "failures 1건의 원인 미상 — 프로브가 인큐 실패·claim 0행·남의 잡 claim·complete 0행을 카운터 하나로 뭉쳐 세고 사유를 로그로 남기지 않는다. 사유별 분리가 Phase 3 재측정의 선행 과제 (02-08)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-07T05:52:49.323Z",
    "resolved_at": null
  }
]
````
