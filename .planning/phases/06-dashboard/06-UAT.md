---
status: testing
phase: 06-dashboard
source: [06-VERIFICATION.md]
started: 2026-08-13T00:20:00+09:00
updated: 2026-08-13T00:20:00+09:00
---

## Current Test

number: 1
name: Full ingest flow — dropzone to job-chain completion
expected: |
  Drop a file/URL/text source with apps/api + worker + supabase running. Real stage names
  shown throughout (업로드 → 파싱 → 컴파일 → 링크 동기화 → 임베딩), never an indeterminate
  spinner. A dead job shows a retry button. Polling stops once the chain reaches a terminal
  state, and resumes on retry/cancel (WR-04 fix).
awaiting: user response

## Tests

### 1. Full ingest flow — dropzone to job-chain completion
expected: 실제 단계 이름으로 진행 표시, dead job 재시도 버튼, 종료 상태에서 폴링 정지·재시도 시 재개
result: [pending]

### 2. Full ask flow — dual-citation markers
expected: |
  Ask a real question against seeded evidence. Placeholder markers are inert during
  streaming; after the citations SSE frame they become clickable numbered badges. Clicking
  a wiki-kind marker and a source-kind marker within the same dual-cited sentence each opens
  exactly its own cited content (single-card-per-click is the accepted interpretation of
  D-10 per the applied override — this test also confirms/refutes whether that's sufficient
  in practice).
result: [pending]

### 3. Wiki viewer — all verification states + red links
expected: |
  Seed wiki_pages covering all 4 verification states (verified/expired/partial/unverified) +
  disputed + a resolved/red WikiLink pair. Read-only banner always shown. Correct callout per
  state. Disputed always takes visual priority over the verification callout. Resolved
  WikiLinks navigate; red links show the "아직 작성되지 않음 · 지금 생성" CTA and route to
  /sources with prefill (WINDOWS.md #12).
result: [pending]

### 4. Graph canvas — 1000-node cap notice
expected: |
  Seed a workspace with >1,000 wiki_pages, load the graph canvas. The exact cap notice
  "이 워크스페이스는 그래프 표시 한도(1,000개 노드)를 초과했습니다 — 카테고리 필터로 범위를
  좁혀주세요." appears — never a silent truncation — and does NOT appear at exactly 1,000
  rows (WR-01 off-by-one fix).
result: [pending]

### 5. Member removal under RLS-blocked condition
expected: |
  Attempt to remove a member in a state where RLS should block the delete. The
  "멤버를 제거하지 못했습니다." banner is shown and the member stays in the list (06-REVIEW-FIX.md
  WR-03 fix — confirms a 0-row delete result is detected, not silently treated as success).
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
