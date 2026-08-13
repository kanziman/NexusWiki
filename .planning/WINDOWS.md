---
schema_version: 1
open_count: 13
waived_count: 0
fixed_count: 1
total_count: 14
last_updated: 2026-08-13T00:21:08.579Z
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
| 5 | 03 | deviation | supabase/migrations/0008_embedding_dimension.sql |  | 클라우드에서 service_role이 public.search_chunks EXECUTE를 갖는다 — pg_default_acl 로컬/클라우드 차이, 0009의 revoke 한 줄로 정정 | fixed |  | 2026-08-08T02:07:27.655Z | 2026-08-08T06:58:43.333Z |
| 6 | 03 | unrun-verify | apps/worker/src/worker/db/service.py |  | COMP-07 축소 재처리의 실제 삭제 경로가 관측되지 않았다 — 스모크가 같은 본문을 재처리해 removed_count=0이었다. 청크가 줄어드는 입력으로 확인 필요 | open |  | 2026-08-08T08:16:13.778Z |  |
| 7 | 03 | stub | apps/worker/src/worker/handlers/parse.py |  | source_chunks.search_tsv와 tsv_tokenizer_version을 비워 둔다 — 어휘 채널(RTV)은 Phase 4가 색인 RPC(0010)와 함께 소급 색인해야 한다 | open |  | 2026-08-08T08:16:13.922Z |  |
| 8 | 03 | stub | apps/worker/src/worker/handlers/parse.py |  | content가 빈 파일·URL 소스는 SourceNotExtractedError로 끊긴다 — 추출 분기는 03-06(ING-03/ING-04)이 채운다 | open |  | 2026-08-08T08:16:14.047Z |  |
| 9 | 03 | unrun-verify | apps/worker/src/worker/llm.py |  | 오류 되먹임 재시도가 실제 모델에서 복구로 이어지는지 미관측 — 1회차가 스키마를 만족해 재시도 경로가 실호출에서 타지 않았다 | open |  | 2026-08-08T08:16:14.169Z |  |
| 10 | 04 | unrun-verify | docs/ops/hnsw-order-benchmark.md |  | strict_order 대 relaxed_order 비교 실행이 없다 — 고정 코퍼스가 12/12/8행이라 플래너가 HNSW를 고르지 않는다(Phase 2 관측 btree+sort 233 대 HNSW 349,657). 그 규모의 수치는 다른 플랜을 재는 것이라 T-04-12(오도하는 튜닝)에 해당한다. 두 기본값은 제약·안전 기본값으로 유지했을 뿐 측정되지 않았다. 그래프 off/on 비교도 러너에 토글이 없어 불가. Phase 7 OPS 이월 (04-04 Task 3 수용기준 #1 미충족) | open |  | 2026-08-11T09:06:03.966Z |  |
| 11 | 06 | deviation | apps/dashboard/app/globals.css |  | Tailwind max-w-*/w-*/h-* 유틸리티가 이 프로젝트의 커스텀 --spacing-{xs,sm,base,lg,xl,xxl,section} @theme 오버라이드와 이름이 겹치면 --container-*(Tailwind 기본) 대신 --spacing-*로 잘못 해석된다 (실측: max-w-xl -> 32px, 06-03 SettingsMembersPanel에서 발견/수정). max-w-md는 안전(--spacing-md 미정의). 이후 Phase 6 플랜은 xs/sm/base/lg/xl/xxl/section과 겹치는 크기 유틸리티 사용 전 getComputedStyle로 실측 확인할 것. | open |  | 2026-08-12T09:19:45.765Z |  |
| 12 | 06 | unrun-verify | apps/dashboard/components/WikiPageContent.tsx |  | WikiLink 네비게이션(해소/red)과 4종 verification 콜아웃, disputed 우선순위를 로컬 스택 대상 실제 클릭스루로 검증하지 못했다 — Playwright 라이브 검증 시도가 반복 중단되어(watchdog) 정적 검증(vitest/tsc/next build)만으로 대체했다. 시딩한 테스트 데이터/계정은 정리 완료(0행 확인) | open |  | 2026-08-12T14:32:01.260Z |  |
| 13 | 06 | deviation | apps/dashboard/app/ |  | App Router에 error.tsx/not-found.tsx가 전혀 없다 — 처리되지 않은 예외나 잘못된 라우트가 Next의 기본(브랜드 없는) 에러 화면으로 떨어진다. 06-UI-REVIEW.md Pillar 6. | open |  | 2026-08-13T00:21:08.459Z |  |
| 14 | 06 | deviation | apps/dashboard/components/GraphCanvas.tsx |  | 카테고리별 노드 색상 8개가 CSS 커스텀 프로퍼티 대신 리터럴 hex로 하드코딩돼 있다 (Cytoscape 스타일시트 API가 CSS var를 직접 못 받아서) — 각 줄에 // --color-x 주석은 있지만 실제 값은 안 읽는다. 06-UI-REVIEW.md Pillar 3. | open |  | 2026-08-13T00:21:08.579Z |  |

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
  },
  {
    "id": 5,
    "kind": "deviation",
    "phase": "03",
    "file": "supabase/migrations/0008_embedding_dimension.sql",
    "line": null,
    "description": "클라우드에서 service_role이 public.search_chunks EXECUTE를 갖는다 — pg_default_acl 로컬/클라우드 차이, 0009의 revoke 한 줄로 정정",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-08T02:07:27.655Z",
    "resolved_at": "2026-08-08T06:58:43.333Z"
  },
  {
    "id": 6,
    "kind": "unrun-verify",
    "phase": "03",
    "file": "apps/worker/src/worker/db/service.py",
    "line": null,
    "description": "COMP-07 축소 재처리의 실제 삭제 경로가 관측되지 않았다 — 스모크가 같은 본문을 재처리해 removed_count=0이었다. 청크가 줄어드는 입력으로 확인 필요",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-08T08:16:13.778Z",
    "resolved_at": null
  },
  {
    "id": 7,
    "kind": "stub",
    "phase": "03",
    "file": "apps/worker/src/worker/handlers/parse.py",
    "line": null,
    "description": "source_chunks.search_tsv와 tsv_tokenizer_version을 비워 둔다 — 어휘 채널(RTV)은 Phase 4가 색인 RPC(0010)와 함께 소급 색인해야 한다",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-08T08:16:13.922Z",
    "resolved_at": null
  },
  {
    "id": 8,
    "kind": "stub",
    "phase": "03",
    "file": "apps/worker/src/worker/handlers/parse.py",
    "line": null,
    "description": "content가 빈 파일·URL 소스는 SourceNotExtractedError로 끊긴다 — 추출 분기는 03-06(ING-03/ING-04)이 채운다",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-08T08:16:14.047Z",
    "resolved_at": null
  },
  {
    "id": 9,
    "kind": "unrun-verify",
    "phase": "03",
    "file": "apps/worker/src/worker/llm.py",
    "line": null,
    "description": "오류 되먹임 재시도가 실제 모델에서 복구로 이어지는지 미관측 — 1회차가 스키마를 만족해 재시도 경로가 실호출에서 타지 않았다",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-08T08:16:14.169Z",
    "resolved_at": null
  },
  {
    "id": 10,
    "kind": "unrun-verify",
    "phase": "04",
    "file": "docs/ops/hnsw-order-benchmark.md",
    "line": null,
    "description": "strict_order 대 relaxed_order 비교 실행이 없다 — 고정 코퍼스가 12/12/8행이라 플래너가 HNSW를 고르지 않는다(Phase 2 관측 btree+sort 233 대 HNSW 349,657). 그 규모의 수치는 다른 플랜을 재는 것이라 T-04-12(오도하는 튜닝)에 해당한다. 두 기본값은 제약·안전 기본값으로 유지했을 뿐 측정되지 않았다. 그래프 off/on 비교도 러너에 토글이 없어 불가. Phase 7 OPS 이월 (04-04 Task 3 수용기준 #1 미충족)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-11T09:06:03.966Z",
    "resolved_at": null
  },
  {
    "id": 11,
    "kind": "deviation",
    "phase": "06",
    "file": "apps/dashboard/app/globals.css",
    "line": null,
    "description": "Tailwind max-w-*/w-*/h-* 유틸리티가 이 프로젝트의 커스텀 --spacing-{xs,sm,base,lg,xl,xxl,section} @theme 오버라이드와 이름이 겹치면 --container-*(Tailwind 기본) 대신 --spacing-*로 잘못 해석된다 (실측: max-w-xl -> 32px, 06-03 SettingsMembersPanel에서 발견/수정). max-w-md는 안전(--spacing-md 미정의). 이후 Phase 6 플랜은 xs/sm/base/lg/xl/xxl/section과 겹치는 크기 유틸리티 사용 전 getComputedStyle로 실측 확인할 것.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-12T09:19:45.765Z",
    "resolved_at": null
  },
  {
    "id": 12,
    "kind": "unrun-verify",
    "phase": "06",
    "file": "apps/dashboard/components/WikiPageContent.tsx",
    "line": null,
    "description": "WikiLink 네비게이션(해소/red)과 4종 verification 콜아웃, disputed 우선순위를 로컬 스택 대상 실제 클릭스루로 검증하지 못했다 — Playwright 라이브 검증 시도가 반복 중단되어(watchdog) 정적 검증(vitest/tsc/next build)만으로 대체했다. 시딩한 테스트 데이터/계정은 정리 완료(0행 확인)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-12T14:32:01.260Z",
    "resolved_at": null
  },
  {
    "id": 13,
    "kind": "deviation",
    "phase": "06",
    "file": "apps/dashboard/app/",
    "line": null,
    "description": "App Router에 error.tsx/not-found.tsx가 전혀 없다 — 처리되지 않은 예외나 잘못된 라우트가 Next의 기본(브랜드 없는) 에러 화면으로 떨어진다. 06-UI-REVIEW.md Pillar 6.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-13T00:21:08.459Z",
    "resolved_at": null
  },
  {
    "id": 14,
    "kind": "deviation",
    "phase": "06",
    "file": "apps/dashboard/components/GraphCanvas.tsx",
    "line": null,
    "description": "카테고리별 노드 색상 8개가 CSS 커스텀 프로퍼티 대신 리터럴 hex로 하드코딩돼 있다 (Cytoscape 스타일시트 API가 CSS var를 직접 못 받아서) — 각 줄에 // --color-x 주석은 있지만 실제 값은 안 읽는다. 06-UI-REVIEW.md Pillar 3.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-13T00:21:08.579Z",
    "resolved_at": null
  }
]
````
