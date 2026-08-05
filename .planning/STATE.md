---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 01
current_phase_name: bootstrap-and-ground-truth
status: executing
stopped_at: Completed 01-03-PLAN.md
last_updated: "2026-08-05T03:21:27.406Z"
last_activity: 2026-08-03
last_activity_desc: Phase 01 execution started
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 8
  completed_plans: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-01)

**Core value:** 질문에 대한 답이 원문 청크와 컴파일된 위키 페이지 양쪽으로 추적 가능해야 한다
**Current focus:** Phase 01 — bootstrap-and-ground-truth

## Current Position

Phase: 01 (bootstrap-and-ground-truth) — EXECUTING
Plan: 6 of 8
Status: Ready to execute
Last activity: 2026-08-03 — Phase 01 execution started

Progress: [██████░░░░] 63%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 15 min | 3 tasks | 20 files |
| Phase 01 P02 | 30min | 3 tasks | 3 files |
| Phase 01 P05 | 14min | 3 tasks | 16 files |
| Phase 01 P06 | 3h | 3 tasks | 6 files |
| Phase 01 P03 | 1d | 3 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: DB 레이어(`0001`~`0004`, `0006`)는 Validated — 로드맵이 재구현하지 않음. v1에 남은 스키마는 `0005`(Phase 1)와 `0007`(Phase 2)뿐
- [Roadmap]: 리전은 싱가포르 양쪽 확정 (Railway에 서울·도쿄 없음). Supabase 프로젝트 생성 후 변경 불가 → Phase 1 P0
- [Roadmap]: RTV-06 골든 질의 세트를 ops에서 retrieval(Phase 4)로 이동 — 가중치·`k`·청크 크기·그래프 채널 가치를 판정하는 전제 조건
- [Roadmap]: OPS-01(`usage_events` + 인큐 시점 비용 상한)을 첫 LLM 호출과 같은 페이즈(3)에 배치
- [Roadmap]: UI-06 Cytoscape 캔버스는 Phase 6의 마지막 표면 (연구 3건이 독립적으로 최저 우선순위 결론)
- [Phase 01]: Storage 경로 파서는 UUID/UUID/파일명 형식만 허용하고 나머지는 null로 거부한다. — D-05: 잘못된 UUID를 22P02 서버 오류가 아닌 정책 거부로 처리한다.
- [Phase 01]: sources 객체에는 UPDATE 정책을 만들지 않아 사용자 원본 덮어쓰기를 차단한다. — D-07: content_hash 멱등성과 원본 추적성을 유지한다.
- [Phase 01]: Railway api/worker는 단일 Dockerfile을 공유하고 worker만 Custom Start Command를 사용한다. — 동일 코드 런타임 경계를 유지한다.
- [Phase 01]: Railway 개별 빌드 다이제스트가 다르면 커밋 SHA·Dockerfile 경로·런타임 GIT_SHA 3항 일치로 동일 빌드를 판정한다. — SPEC R8 2차 판정.
- [Phase 01]: State A was proven, so push-clean was selected instead of recreating the project. — Both the migration ledger and target public schema were empty immediately before the one-way push.

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1] `0005`(Storage)는 첫 클라우드 `db push` **이전에** 적용해야 함 — 이미 적용된 `0006`보다 번호가 낮아 이후에 넣으면 로컬/클라우드 순서가 어긋남
- [Phase 1] 2025-11 이후 생성 프로젝트에는 legacy 키가 발급되지 않음 — `sb_publishable_`/`sb_secret_` 체계로 시작해야 함
- [Phase 2] DB 트랜스포트 미결 — `create function ... SET hnsw.iterative_scan`이 Supabase RPC로 실제 적용되는지가 판정 기준. 스파이크 전까지 라우터를 쓰지 말 것
- [Phase 2] `0003`의 `jobs`에 하트비트 가능 컬럼이 있는지 미확인 — 없으면 컴파일을 더 작은 잡으로 분할 (워커 루프 작성 전 확인)
- [Phase 3] 한국어 청킹 파라미터는 문헌 없음 — 실측 튜닝 대상. PDF 품질 게이트 임계값은 실제 픽스처(스캔본·다단·표 위주) 필요

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-08-05T03:21:06.284Z
Stopped at: Completed 01-03-PLAN.md
Resume file: None
