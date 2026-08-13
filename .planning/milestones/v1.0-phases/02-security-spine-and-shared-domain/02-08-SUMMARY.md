---
phase: 02-security-spine-and-shared-domain
plan: 08
subsystem: backend
tags: [job-queue, worker, observability, baseline, reap-timeout, railway, tdd]

# Dependency graph
requires:
  - phase: 02-security-spine-and-shared-domain
    provides: "02-07의 queue.py claim→complete 루프와 noop 핸들러, ServiceDb._rpc의 0행 정규화"
  - phase: 02-security-spine-and-shared-domain
    provides: "02-06의 0007 — jobs_dedup_idx와 섹션 8 최소권한 매트릭스(service_role의 jobs INSERT 권한, DELETE 부재)"
  - phase: 02-security-spine-and-shared-domain
    provides: "02-02의 WorkerSettings — 새 토글 필드가 얹히는 자리"
  - phase: 01-bootstrap-and-ground-truth
    provides: "01-08의 rtt.py 측정 방법론 — 콜드 분리·워밍업 5회·최근접 순위 백분위"
provides:
  - "worker.queue_baseline.measure_queue_roundtrip — claim→complete 왕복 측정 장치"
  - "worker.queue_baseline.QueueBaselineResult — p99를 포함한 7필드 결과"
  - "QUEUE_BASELINE_P99_MIN_SAMPLES=200 — 표본이 부족하면 p99를 주장하지 않는 문턱"
  - "ServiceDb.enqueue_job — worker가 잡을 인큐하는 첫 경로 (Phase 3의 생산자가 이어받는다)"
  - "ServiceDb._insert — Prefer: return=representation을 붙인 PostgREST insert 헬퍼"
  - "WorkerSettings.QUEUE_BASELINE_ENABLED / QUEUE_BASELINE_WORKSPACE_ID"
  - "docs/ops/reap-timeout-baseline.md — 실측 기준선과 잠정 타임아웃 2초, 그리고 그 한계"
affects: [phase-03]

# Actuals (#2632)
actuals:
  tokens: 41000
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "측정 구간의 경계를 헤더의 ASCII 도식으로 못 박는다 — 무엇을 재고 있는지 모호하면 그 숫자로 타임아웃을 유도할 수 없다"
    - "표본 수가 문턱에 못 미치면 통계량을 계산하지 않고 None으로 둔다 — 주장을 줄이는 것이 값을 지어내는 것보다 싸다"
    - "산출 방식을 선행 기준선(rtt.py)과 동일하게 유지해 두 숫자를 같은 표에서 읽을 수 있게 한다"

key-files:
  created:
    - apps/worker/src/worker/queue_baseline.py
    - apps/worker/tests/test_queue_baseline.py
    - docs/ops/reap-timeout-baseline.md
  modified:
    - apps/worker/src/worker/settings.py
    - apps/worker/src/worker/__main__.py
    - apps/worker/src/worker/db/service.py
    - .planning/STATE.md

key-decisions:
  - "측정 구간은 claim→complete이며 인큐는 구간 밖이다 — reap_stale_jobs가 보는 나이가 locked_at 기준이고 locked_at은 claim 시점에 찍히므로, 인큐 대기는 타임아웃이 덮어야 하는 구간이 아니다"
  - "성공 표본 200 미만이면 p99_ms를 None으로 둔다 — 최근접 순위 p99가 사실상 최댓값이 되어 'p99'라는 이름이 한 표본에 근거 없는 신뢰를 준다"
  - "표본 시도를 220회로 잡았다 — 200으로 두면 실패 한 번에 p99를 잃는다. 실제로 1회 실패했고 219로 문턱을 넘겼다"
  - "claim에 types=['noop'] 필터를 걸고 자기 잡이 아니면 release_job으로 반납한다 — claim_job은 id 지정이 불가능한 전역 폴링이라, 이 검사가 없으면 프로브가 운영 잡을 핸들러 없이 완료 처리한다"
  - "잠정 타임아웃 2초를 도출하되 reap_stale_jobs 기본 15분은 바꾸지 않는다 — 2초는 noop 전용 큐의 하한이며 Phase 3 컴파일 잡에 적용하면 전부 이중 처리된다"
  - "프로브가 자기 잡을 지우지 못한다 — 0007 섹션 8이 jobs에 어느 롤에도 DELETE를 주지 않으므로, 정리는 처분 가능한 워크스페이스 삭제의 cascade가 유일한 경로다"

patterns-established:
  - "관측값의 형태가 예상과 다르면 그 차이를 결함이 아니라 측정 설계의 귀결로 설명하고 문서에 남긴다 — cold_first_ms가 p50의 1.52배에 그친 이유는 워밍업 분리 실패가 아니라 인큐가 커넥션 비용을 먼저 치렀기 때문이다"
  - "실패 카운터를 사유별로 나누지 않은 것이 관측의 한계가 된다 — 다음 측정 전에 고칠 항목으로 문서에 명시한다"

requirements-completed: [DOM-09]

coverage:
  - id: D1
    description: "결과 dataclass가 cold_first_ms·p50·p95·p99·sample_count·warmup_count·failures 일곱 필드를 갖는다"
    requirement: DOM-09
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_queue_baseline.py#test_result_populates_all_seven_fields"
        status: pass
      - kind: manual
        ref: "uv run python -c 'fields(QueueBaselineResult)' → ok"
        status: pass
    human_judgment: false
  - id: D2
    description: "주입한 시계로 만든 알려진 표본에서 최근접 순위 p50/p95/p99가 기대값과 일치한다"
    requirement: DOM-09
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_queue_baseline.py#test_nearest_rank_percentiles (200표본 1..200 → 100/190/198)"
        status: pass
    human_judgment: false
  - id: D3
    description: "콜드 첫 왕복이 워밍업·표본과 분리되어 별도 필드에 담긴다"
    requirement: DOM-09
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_queue_baseline.py#test_cold_first_roundtrip_is_separated_from_warmups_and_samples"
        status: pass
    human_judgment: false
  - id: D4
    description: "성공 표본 200 이상이면 p99가 값을 갖고, 199면 None이다 — 표본이 부족한데 p99를 주장하지 않는다"
    requirement: DOM-09
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_queue_baseline.py#test_two_hundred_samples_yield_a_p99"
        status: pass
      - kind: unit
        ref: "apps/worker/tests/test_queue_baseline.py#test_one_hundred_ninety_nine_samples_refuse_to_claim_a_p99"
        status: pass
    human_judgment: false
  - id: D5
    description: "왕복이 실패하면 failures가 증가하고 그 회차가 표본에 들어가지 않으며, 표본이 0이어도 예외를 던지지 않는다"
    requirement: DOM-09
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_queue_baseline.py#test_failed_roundtrips_are_counted_and_excluded_from_samples"
        status: pass
      - kind: unit
        ref: "apps/worker/tests/test_queue_baseline.py#test_no_successful_samples_yields_no_percentiles"
        status: pass
      - kind: unit
        ref: "apps/worker/tests/test_queue_baseline.py#test_transport_errors_are_counted_not_raised"
        status: pass
    human_judgment: false
  - id: D6
    description: "프로브가 남의 잡을 집으면 complete하지 않고 release_job으로 반납한다"
    requirement: DOM-09
    verification:
      - kind: unit
        ref: "apps/worker/tests/test_queue_baseline.py#test_a_foreign_claim_is_released_and_discarded"
        status: pass
    human_judgment: false
  - id: D7
    description: "배포된 Railway asia-southeast1 worker가 ap-southeast-1 Supabase를 상대로 claim→complete 왕복을 실측했다"
    requirement: DOM-09
    verification:
      - kind: manual
        ref: "railway deploy logs — worker.queue_baseline_measured (2026-08-07T05:43:23.964564Z, git_sha 60c1e80), 일곱 키 전부 존재"
        status: pass
    human_judgment: false
  - id: D8
    description: "잠정 타임아웃과 그 유도 근거·noop 한계·Phase 3 재측정·하트비트 미추가 결정이 docs/ops/에 함께 남았다"
    requirement: DOM-09
    verification:
      - kind: manual
        ref: "docs/ops/reap-timeout-baseline.md — 6개 절 + D-16/D-17/noop/Phase 3 문자열 전수 확인"
        status: pass
    human_judgment: false
  - id: D9
    description: "측정이 남긴 219여 건의 프로브 잡 행이 실제로 정리되었는지"
    verification: []
    human_judgment: true
    rationale: "프로브 워크스페이스 UUID를 전달받지 못했고 삭제 여부를 확인하지 못했다. 0007 섹션 8이 jobs에 DELETE를 주지 않으므로 정리 경로는 그 워크스페이스 삭제의 cascade 하나뿐이다. 클라우드 프로젝트를 직접 조회할 수 있는 사람이 확인해야 한다."
  - id: D10
    description: "failures 1건의 실제 원인"
    verification: []
    human_judgment: true
    rationale: "프로브가 인큐 실패·claim 0행·남의 잡 claim·complete 0행을 카운터 하나로 뭉쳐 세고 사유를 로그로 남기지 않는다. 로그만으로는 판별 불가이며, 원인을 지어내지 않고 '관측됐으나 원인 미상'으로 기록했다. 사유별 카운터 분리가 Phase 3 재측정의 선행 과제다."

# Metrics
duration: 체크포인트 대기 포함 약 13h (실작업 약 35min)
completed: 2026-08-07
status: complete
---

# Phase 02 Plan 08: reap 타임아웃 실측 기준선 Summary

**Railway `asia-southeast1` worker가 `ap-southeast-1` Supabase를 상대로 `noop` claim→complete 왕복 219회를 실측해 p99 127.054 ms를 얻었고, 그 숫자가 실제로 말해 주는 것은 "reap 타임아웃을 정하는 것은 전송이 아니라 핸들러 지속시간"이라는 사실이다**

## Performance

- **Duration:** 실작업 약 35분 (Task 1 약 15분 + 체크포인트 + Task 3 약 20분). 사이에 Railway 실측을 위한 사람 개입 대기가 있었다
- **Completed:** 2026-08-07
- **Tasks:** 3 (TDD 1 + 배포 실측 1 + 문서 1)
- **Files:** 신규 3, 수정 4
- **Tests:** 133 → 143 (worker 큐 기준선 10건 추가)

## Accomplishments

- **`reap_stale_jobs`의 기본 15분에 처음으로 데이터가 붙었다 — 그런데 그 데이터가 말하는 것은 15분이 맞다/틀리다가 아니다.** 전송 p99는 127.054 ms이고 15분은 900,000 ms다. 전송은 타임아웃의 **0.0141%**다. 이 측정이 실제로 한 일은 15분의 정당화 후보 하나("전송 비용을 감안한 값")를 제거하고, 나머지 99.99%가 전부 **핸들러 지속시간 예산**임을 드러낸 것이다. 그 예산의 근거는 여전히 이 측정 밖에 있다.
- **잠정치 2초를 유도했고, 동시에 그것을 적용하지 말라고 못 박았다.** `127.054 ms × 안전계수 10 ≈ 1.271 s → 2초`. 안전계수 10의 근거는 관측의 약점 셋이다 — 표본이 30초 창 하나뿐이고, 실패 1건의 원인이 미상이며, 로그에 표본 최댓값이 없어 p99가 우리가 가진 가장 높은 순위 통계다. 셋 다 꼬리를 과소평가하는 방향이다. 그리고 이 2초는 `noop` 전용 큐의 하한이라, Phase 3 컴파일 잡에 그대로 적용하면 **전부 이중 처리된다**. 문서에서 가장 비싼 오독이 그것이므로 그 문장을 한계 절의 첫 항목으로 올렸다.
- **표본 220회 시도는 여유가 아니라 필요였다.** SPEC R11은 p99를 주장하려면 200회를 요구하는데, 실제 측정에서 1회가 실패해 219가 나왔다. `QUEUE_BASELINE_SAMPLE_COUNT`를 200으로 두었다면 199로 떨어져 p99를 잃고 이 플랜의 핵심 산출물이 p95로 후퇴했을 것이다. 여유 20회가 실제로 소진됐다.
- **측정 구간의 경계를 골랐고, 그 선택이 숫자의 의미를 정한다.** 인큐를 측정 밖에 둔 이유는 `reap_stale_jobs`가 보는 나이가 `locked_at` 기준이고 `locked_at`은 claim 시점에 찍히기 때문이다(`0003:185-196`). 인큐부터 claim까지의 대기는 큐에 잡이 쌓인 정도이지 워커가 락을 쥐고 있는 시간이 아니다. 이 경계를 파일 헤더에 ASCII 도식으로 남겼다 — 무엇을 재고 있는지 모호하면 그 숫자로 타임아웃을 유도할 수 없다.
- **관측값이 예상과 어긋난 지점을 결함이 아니라 설계의 귀결로 설명했다.** `cold_first_ms` 128.606 ms는 p50의 1.52배에 그친다. Phase 1 RTT에서는 29.3배(851.138 / 29.093)였다. 워밍업 분리가 실패한 것이 아니라, 측정 구간이 claim부터 시작하는데 그 앞의 인큐 POST가 같은 httpx 클라이언트로 먼저 나가 TCP/TLS 수립 비용을 이미 치렀기 때문이다. 즉 이 문서의 콜드는 커넥션 수립 비용을 **담고 있지 않으며**, `rtt-baseline.md`의 851 ms와 같은 종류의 값으로 읽으면 안 된다. 플랜의 `⚠️`가 요구한 확인이 바로 이것이었다.
- **숫자가 엉뚱한 것을 재고 있지 않다는 정합성 확인 둘.** (a) 측정 구간에 PostgREST RPC가 2회 들어 있고 Phase 1 단일 GET p50이 29.093 ms이므로 순수 왕복만 58.186 ms인데, 관측 p50 84.492 ms와의 차이 26.306 ms가 두 큐 함수의 서버 측 실행과 POST 오버헤드에 해당한다. (b) 기동부터 측정 종료까지 29.847초에 226회차를 돌아 회차당 132.1 ms이고, 측정 구간 p50을 빼면 남는 47.6 ms가 의도적으로 제외한 인큐 POST 몫이다.
- **프로브가 운영 잡을 삼키지 않는다.** `claim_job`은 id로 지정할 수 없는 전역 폴링이다. `types=['noop']` 필터를 걸고, 그래도 자기 잡이 아닌 것이 잡히면 `complete`가 아니라 `release_job`으로 반납한다. 이 검사가 없으면 프로브가 남의 잡을 핸들러 없이 완료 처리해 **실제 일이 조용히 사라진다**.

## Task Commits

1. **Task 1: 측정 장치 (TDD)** — `f1b0ef2` (test, RED) → `2679fa2` (feat, GREEN)
2. **체크포인트 블로커 기록** — `ef6a764` (docs, STATE.md)
3. **Task 2: Railway 실측** — 코드 변경 없음. 관측값은 배포 커밋 `60c1e80`의 로그로 확보
4. **Task 3: 기준선 문서** — `f34b105`

## Task 2 실측 원문

```text
event: worker.started
git_sha: 60c1e8009e7871e6dc790e25319528285b5c269c
timestamp: 2026-08-07T05:42:54.117256Z

event: worker.rtt_skipped
reason: disabled
timestamp: 2026-08-07T05:42:54.117377Z

event: worker.queue_baseline_measured
cold_first_ms: 128.60616770982742
p50_ms: 84.49230343103409
p95_ms: 107.92132467031479
p99_ms: 127.05407291650772
sample_count: 219
warmup_count: 5
failures: 1
git_sha: 60c1e8009e7871e6dc790e25319528285b5c269c
job_id: bootstrap
workspace_id: bootstrap
timestamp: 2026-08-07T05:43:23.964564Z
```

- **측정 시각:** 2026-08-07 14:43:23 KST (`2026-08-07T05:43:23.964564Z`)
- **배포 커밋 SHA:** `60c1e8009e7871e6dc790e25319528285b5c269c`
- **소요:** 05:42:54 → 05:43:24, 약 29.85초에 226회차(콜드 1 + 워밍업 5 + 표본 220)
- **일곱 키 전부 존재:** `cold_first_ms` · `p50_ms` · `p95_ms` · `p99_ms` · `sample_count` · `warmup_count` · `failures`
- **p99 주장 가능:** `sample_count` 219 ≥ `QUEUE_BASELINE_P99_MIN_SAMPLES` 200
- **실패 위치는 표본 구간:** 표본 시도 220회 중 219회 성공이고 `failures`가 1이므로, 콜드와 워밍업 6회는 모두 성공했고 그 1건은 표본 구간에서 났다. 이것은 산술이지 별도 관측이 아니다

⚠️ `git_sha`가 이 저장소의 `f1b0ef2`·`2679fa2`(Task 1)를 조상으로 포함하는 `60c1e80`이므로, 측정된 코드가 이 플랜이 만든 그 코드다. 로그에 자격증명은 섞이지 않았다(T-02-51 육안 확인).

## Files Created/Modified

### 신규

- `apps/worker/src/worker/queue_baseline.py` — 헤더에 측정 구간 경계 ASCII 도식. `_perf_counter` 모듈 별칭을 유지해 테스트가 시계를 주입할 수 있다. `QUEUE_BASELINE_P99_MIN_SAMPLES=200` 위의 `⚠️`가 "값을 지어내지 않는 것이 여기서 유일하게 옳은 동작"이라는 근거를 담는다.
- `apps/worker/tests/test_queue_baseline.py` (10 tests) — 시계 주입 + `FakeQueue` 대역. 플랜의 `<behavior>` 7건에 상수 문턱·전송 예외·남의 잡 반납 3건을 더했다.
- `docs/ops/reap-timeout-baseline.md` — `rtt-baseline.md`의 절 골격(`## 측정 일시` → `## 방법` → `## 결과` → …)과 우측 정렬 수치 표를 그대로 따랐다.

### 수정

- `apps/worker/src/worker/settings.py` — `QUEUE_BASELINE_ENABLED: bool = False`(기본이 거짓인 것이 요점이다)와 `QUEUE_BASELINE_WORKSPACE_ID: str | None = None`. 둘 다 필수 필드가 아니므로 02-02가 세운 부팅 실패 계약을 건드리지 않는다.
- `apps/worker/src/worker/__main__.py` — `_run_queue_baseline_probe`가 `run_queue_loop` **앞에서** 한 번 돈다. 순서가 중요하다 — 루프가 먼저 돌면 프로브 잡과 루프가 서로 잡을 뺏는다.
- `apps/worker/src/worker/db/service.py` — `ServiceDb.enqueue_job` + `_insert`. `TABLE_HELPERS`에 등록되어 `workspace_id` 기본값 없는 키워드 전용 인자 규칙을 그대로 받는다.
- `.planning/STATE.md` — 체크포인트 블로커.

## Decisions Made

- **측정 구간에서 인큐를 제외한다.** `reap_stale_jobs`가 보는 것은 `locked_at` 이후 경과 시간이고 `locked_at`은 claim 시점에 찍힌다. 인큐 대기는 큐 적체이지 락 점유가 아니므로 타임아웃이 덮어야 할 구간이 아니다.
- **표본 200 미만이면 p99를 계산하지 않는다.** 최근접 순위 p99가 사실상 최댓값이 되어 "p99"라는 이름이 한 표본에 근거 없는 신뢰를 준다. 분기 테스트 2건(199 → `None`, 200 → 값)이 이것을 고정한다.
- **시도 횟수 220, 문턱 200으로 분리한다.** 두 값을 같게 두면 실패 한 번에 p99를 잃는다. 실제로 1회 실패했다.
- **`claim`에 type 필터를 건다 — 02-07의 큐 루프와 정반대 선택이다.** 루프는 미등록 type을 데드레터로 보내야 하므로 필터를 걸지 **않는다**. 프로브는 반대로 자기가 만든 종류만 집어야 하며, 자기 잡이 아니면 `release_job`으로 반납한다. 같은 함수를 부르는 두 호출부가 반대 이유로 반대 선택을 하는 것이고, 그 이유를 양쪽 코드에 각각 남겼다.
- **잠정치를 유도하되 `reap_stale_jobs` 기본값은 바꾸지 않는다.** 잠정치를 문서에 남기는 것까지가 Phase 2의 범위다(02-SPEC.md Out of scope). `git diff --name-only supabase/migrations/`가 빈 출력임을 확인했다.
- **프로브 워크스페이스를 밖에서 주입받는다.** `service_role`은 `workspaces`에 SELECT만 갖고(0007 섹션 8) `jobs`에는 DELETE 권한이 없다. 프로브가 워크스페이스를 만들 수도, 자기 잡을 지울 수도 없으므로, 처분 가능한 워크스페이스 id를 설정으로 받고 정리는 그 삭제의 cascade에 맡긴다.

## Deviations from Plan

### 계획과의 차이 (자동 수정 아님)

**1. "각 왕복은 자기 잡을 만들고 자기가 지운다"가 현재 권한 매트릭스에서 성립하지 않는다**

플랜 Task 1 `<action>`이 각 회차의 자기 정리를 요구한다. 실제 표면을 확인한 결과 **불가능하다**:

- `0007` 섹션 8의 최소권한 매트릭스는 `jobs`에 `service_role`에게 `select, insert, update`만 준다. **DELETE는 어느 롤에도 없다** — 잡 이력이 곧 감사 기록이기 때문이다.
- 02-07-SUMMARY도 같은 사실을 이미 기록했다: "`jobs`에는 어느 롤도 DELETE 권한이 없으므로 정리는 워크스페이스 삭제의 cascade가 유일한 경로다."
- 남은 길은 `jobs`를 직접 DELETE할 권한을 새로 주는 것인데, 그것은 이 플랜의 `files_modified` 밖(마이그레이션)이고 감사 기록 설계를 뒤집는 변경이다.

**택한 것:** 각 회차가 자기 잡을 만드는 부분은 그대로 두고(고유 `target_id`로 `jobs_dedup_idx`를 만족시킨다), 삭제는 포기하되 그 대신 **프로브 잡을 처분 가능한 워크스페이스 하나에 가둔다**. `QUEUE_BASELINE_WORKSPACE_ID` 설정이 그 장치이며, 정리는 그 워크스페이스 삭제의 cascade다. 삭제 시도를 아예 하지 않는다 — 매 회차 42501을 받는 것은 소음일 뿐이다.

**남은 것:** 이번 측정의 프로브 워크스페이스 UUID를 전달받지 못했고 삭제 여부도 확인하지 못했다. 219여 건의 잡 행이 클라우드에 남아 있을 수 있다. 미결 항목으로 문서(§한계 4)와 아래 Known Stubs에 남겼다.

**2. `db/service.py`가 이 플랜의 `files_modified` 밖인데 수정했다**

프로브가 잡을 인큐하려면 insert 경로가 필요한데 `ServiceDb`에는 읽기 헬퍼(`get_job`/`list_jobs`)와 큐 RPC 헬퍼만 있었다. `enqueue_job` + `_insert`를 추가했고, `TABLE_HELPERS`에 등록해 기존 분류 테스트(`workspace_id`가 기본값 없는 키워드 전용)의 규율을 그대로 받게 했다. 02-06·02-07이 같은 이유(호출부 불일치를 만든 쪽이 같은 페이즈)로 이 파일을 고친 선례를 따랐다. 부수 효과로 Phase 3의 잡 생산자(ING-01)가 쓸 인큐 경로가 미리 생겼다.

**3. `QUEUE_BASELINE_WORKSPACE_ID` 설정 필드가 플랜에 없다**

플랜의 산출물 표는 `QUEUE_BASELINE_ENABLED` 하나만 명시한다. 그러나 프로브는 잡을 만들 워크스페이스가 있어야 하고 `service_role`은 그것을 만들 수 없다. 필수가 아닌 선택 필드(`str | None = None`)로 추가해 02-02의 부팅 실패 계약을 건드리지 않았고, 값이 없으면 프로브를 돌리지 않고 `worker.queue_baseline_skipped`를 남긴다.

**4. Task 2가 체크포인트를 거쳤다**

배포·서비스 env 변경·재시작은 이 실행의 권한 밖이며, 이 환경에는 `railway` CLI도 없었다(`command -v railway` → 없음). 숫자를 지어내지 않고 중단한 뒤 필요한 것 넷(CLI · worker env 4종 보강 · 프로브 워크스페이스 · 토글 절차)을 정리해 반환했고, 사람이 실측한 로그 원문을 받아 재개했다. Task 3의 표 값은 그 원문에서 그대로 옮긴 것이며 재입력하거나 반올림하지 않았다.

---

**Total deviations:** 0 auto-fixed + 4 문서화된 차이
**Impact on plan:** 산출물 3종은 플랜 그대로다. 확대된 것은 `db/service.py`의 인큐 헬퍼와 설정 필드 하나이며, 축소된 것은 회차별 잡 자기 정리 하나다 — 그리고 그것은 구현 선택이 아니라 권한 매트릭스가 막은 것이다.

## Issues Encountered

- **`failures: 1`의 원인을 알 수 없다.** 프로브가 인큐 실패·claim 0행·남의 잡 claim·complete 0행을 카운터 하나로 뭉쳐 세고 사유를 로그로 남기지 않는다. 원인을 추정해 적는 대신 "관측됐으나 원인 미상"으로 기록했고, 사유별 카운터 분리를 Phase 3 재측정의 선행 과제로 남겼다. 이 한 줄이 이 플랜에서 가장 지키기 어려웠던 규율이다 — 그럴듯한 원인 하나를 적는 것이 훨씬 쉬웠다.
- **콜드 값이 기대와 다른 형태로 나왔다.** 플랜의 `⚠️`는 `cold_first_ms`가 `p50_ms`보다 현저히 크지 않으면 그 사실을 기록하라고 요구했다. 1.52배였고, 원인은 측정 구간이 claim부터 시작해 인큐가 커넥션 비용을 먼저 치른 것이다. 워밍업 분리 자체는 정상 동작했다.
- **실행 중 저장소가 외부에서 전진했다.** 체크포인트 대기 동안 02-09 작업과 `pull`이 들어와 HEAD가 `ef6a764`에서 `60c1e80`으로 옮겨졌다. Task 1의 세 커밋이 여전히 HEAD의 조상임을 `git merge-base --is-ancestor`로 확인했고, 그 SHA가 곧 측정된 배포 커밋이다 — 즉 측정 대상 코드가 이 플랜의 코드임이 SHA로 확정된다.

## Known Stubs

없음. 아래 둘은 스텁이 아니라 **관측의 미결 항목**이다.

- **프로브 워크스페이스 정리 미확인.** UUID를 전달받지 못했고 삭제 여부도 모른다. `jobs`에 DELETE 권한이 없어 219여 건의 잡 행은 그 워크스페이스 삭제 cascade로만 사라진다. 클라우드를 조회할 수 있는 사람이 확인해야 한다.
- **`failures: 1`의 사유 미상.** 로그만으로 판별 불가. 프로브의 실패 카운터를 사유별로 나누는 것이 Phase 3 재측정 전 과제다.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: residual-data | `apps/worker/src/worker/queue_baseline.py` | T-02-48(클라우드 `jobs`에 잔여 프로브 행)의 완화가 부분적이다. 각 회차가 자기 잡을 지운다는 플랜의 완화책은 `0007` 섹션 8의 DELETE 부재로 성립하지 않으며, 대신 처분 가능한 워크스페이스에 가두는 방식으로 대체했다. 이번 실행의 워크스페이스 삭제는 미확인 |
| threat_flag: unverified-assumption | `docs/ops/reap-timeout-baseline.md` | 잠정 2초의 안전계수 10은 관측된 분산이 아니라 **관측의 약점 셋**(단일 30초 창·실패 원인 미상·표본 최댓값 부재)에서 나온 판단이다. Phase 3 재측정이 이 계수를 실제 분포로 대체해야 한다 |

## User Setup Required

`user_setup: []` — 새 패키지는 없다. 단 재측정이 필요할 때는 Railway `worker` 서비스에 `QUEUE_BASELINE_ENABLED=true`와 `QUEUE_BASELINE_WORKSPACE_ID=<처분 가능한 워크스페이스 uuid>`를 설정하고 재시작한 뒤, 측정이 끝나면 `QUEUE_BASELINE_ENABLED`를 거짓으로 되돌려야 한다. ⚠️ `api` 서비스에는 절대 설정하지 않는다 — 큐 프로브는 `service_role`을 쓰므로 `api`에 켜면 SEC-01의 물리적 집행 지점(01-CONTEXT.md > D-12)이 흐려진다.

## Next Phase Readiness

**준비된 것**

- **Phase 3이 이어받을 숫자와 그 사용법이 문서 한 곳에 있다.** `docs/ops/reap-timeout-baseline.md`의 `## 다운스트림`이 LLM 잡 p99 재측정과 COMP-04 잡 분할을 명시한다.
- **재측정 장치가 그대로 재사용된다.** `measure_queue_roundtrip`은 잡 종류에 무관하다. Phase 3은 `QUEUE_BASELINE_JOB_TYPE`을 컴파일 잡으로 바꾸고 표본 수를 줄이면 같은 형태의 기준선을 얻는다(LLM 잡은 220회를 돌릴 수 없으므로 표본 문턱과 p99 주장 여부를 다시 판단해야 한다).
- **`ServiceDb.enqueue_job`이 생겼다.** Phase 3의 잡 생산자(ING-01)가 인큐할 경로가 이미 있고, `target_id` 계약과 23505 처리 책임이 docstring에 적혀 있다.

**확인이 필요한 것**

- ⚠️ **잠정 2초를 큐에 적용하면 안 된다.** Phase 3 컴파일 잡이 전부 이중 처리된다. 문서 `## 잠정 타임아웃`과 `## 한계 1`이 이 경고를 담고 있으나, 값만 보고 옮겨 적는 실수가 이 산출물의 가장 큰 위험이다.
- ⚠️ **프로브 잡 219여 건이 클라우드에 남아 있을 수 있다.**
- ⚠️ **`PLATFORM_GRACE_SECONDS = 30.0`은 여전히 가정이다.** 02-07이 남긴 미확인 항목이며, 이번 실측은 기동 경로만 관측했으므로 SIGTERM 경로는 여전히 배포 컨테이너에서 확인되지 않았다.

## Self-Check: PASSED

- 신규 3개 파일 전부 디스크에 존재 — `apps/worker/src/worker/queue_baseline.py`, `apps/worker/tests/test_queue_baseline.py`, `docs/ops/reap-timeout-baseline.md`
- 커밋 4개 전부 git 이력에 존재하며 HEAD의 조상 — `f1b0ef2`, `2679fa2`, `ef6a764`, `f34b105`
- 플랜 `<verification>` 5개 항목 전수 통과: `pytest apps/worker/tests/test_queue_baseline.py -q` exit 0 (10 passed) · `worker.queue_baseline_measured`가 일곱 키를 모두 담고 로그에 존재 · 문서가 6개 절과 `D-16`·`D-17`·`noop`·`Phase 3` 문자열을 모두 포함 · `git diff --name-only supabase/migrations/` 빈 출력 · 측정 후 `QUEUE_BASELINE_ENABLED` 복구는 사람이 수행(코드 기본값은 `False`)
- Task 1 수용기준 전수 통과: 필드 7개 집합 `ok` · `_perf_counter` 별칭 존재 + `SAMPLE_COUNT=220 ≥ 200` `ok` · `QUEUE_BASELINE_ENABLED` 기본 `False` `ok` · 199 → `p99_ms is None` 단언 존재 · 200 → `p99_ms` 값 단언 존재 · 10개 테스트 수집 (요구 7 이상) · `grep -c 'worker.queue_baseline_measured' __main__.py` = 1 · `02-CONTEXT.md > D-17` 2건 · `⚠️` 3건 · `ruff check apps packages` exit 0
- Task 3 수용기준 전수 통과: 6개 절 존재 · 표 값이 로그 원문과 자릿수까지 일치(128.606 / 84.492 / 107.921 / 127.054 / 219 / 5 / 1) · `## 잠정 타임아웃`이 6단계 유도 논리를 문장으로 담음 · `## 한계`가 `noop`·`Phase 3`·`D-16`·하트비트 근거 3개·ROADMAP 성공기준 5의 미충족 부분을 포함 · 마이그레이션 무변경 · 표본 219 ≥ 200이므로 p99 열을 채웠고 그 자격을 표 위에 명시
- 전체 스위트 `uv run pytest -q` 143 passed

---
*Phase: 02-security-spine-and-shared-domain*
*Completed: 2026-08-07*
