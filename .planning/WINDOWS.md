---
schema_version: 1
open_count: 2
waived_count: 0
fixed_count: 0
total_count: 2
last_updated: 2026-08-06T16:27:18.424Z
---

# Broken Windows Ledger

> Cross-phase defect register. `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 02 | deviation | supabase/tests/0004_loosened_rls_violation.sql |  | 위반 픽스처가 SELECT 정책까지 풀어야 fail-first가 red가 된다 — 정책 하나만 푸는 격리 회귀 재현은 workspaces 표면에서 성립하지 않는다 | open |  | 2026-08-06T16:07:34.615Z |  |
| 2 | 02 | deviation | apps/worker/src/worker/queue.py |  | 미등록 job type이 한 번에 dead가 되지 않는다 — 0003/0007에 즉시 dead 프리미티브가 없어 fail_job(backoff=0)으로 max_attempts 안에 수렴시킨다. 0008의 dead_letter_job()이 이 자리를 닫는다 | open |  | 2026-08-06T16:27:18.424Z |  |

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
  }
]
````
