# Phase 6: Dashboard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-12
**Phase:** 6-Dashboard
**Areas discussed:** 인증 & 워크스페이스 전환, 소스 드롭존 & 잡 진행 상태, Ask UI — 인용 마커 & 이중 Citation 카드

---

## 초기 영역 선택

사용자에게 4개 후보 영역을 제시했다: (1) 인증 & 워크스페이스 전환, (2) 소스 드롭존 & 잡 진행 상태, (3) Ask UI — 인용 마커 & 이중 Citation 카드, (4) 위키 뷰어 & 지식 캔버스.

**사용자 선택:** 1, 2, 3 (위키 뷰어 & 캔버스는 선택하지 않음 → Claude's Discretion으로 CONTEXT.md에 기록)

---

## 인증 & 워크스페이스 전환

| Question | Option | Description | Selected |
|---|---|---|---|
| 로그인 방식 | 이메일+비밀번호 | Supabase Auth 기본 흐름, 가장 단순 | ✓ |
| | 매직링크만 | 비밀번호 관리 부담 없음, 온보딩 마찰 가능 | |
| | 둘 다 지원 | 유연하지만 상태 분기 증가 | |
| 세션/쿠키 처리 | @supabase/ssr 공식 패키지 | Next.js App Router 공식 지원, CVE-2025-29927 회피 검증됨 | ✓ |
| | 직접 쿠키 파싱 | 라이브러리 의존성 없지만 보안 로직 직접 검증 필요 | |
| 워크스페이스 전환 UX | 상단 드롭다운 | 어디서든 즉시 전환, /w/[workspaceId]로 이동 | ✓ |
| | 별도 목록 페이지 | 전환 시 페이지 이동 필요 | |
| 멤버 초대 위치 | 워크스페이스 설정 페이지 | 이메일+역할 폼, 상태 관리 단순 | ✓ |
| | 모달 팝업 | 어디서든 빠르지만 상태 관리 복잡 | |

**User's choice:** 모든 질문에서 권장(recommended) 옵션 선택.
**Notes:** 없음.

---

## 소스 드롭존 & 잡 진행 상태

**User's choice:** 사용자가 "recommand best practice for each, and apply this"로 지시 — 대화형 질문 없이 베스트 프랙티스를 Claude가 선택해 적용.

적용된 결정 (CONTEXT.md D-05~D-08):
- 잡 진행은 실제 단계 이름 스테퍼("업로드→파싱→컴파일→링크 동기화→임베딩"), 불확정 스피너 금지
- 파일/URL/텍스트 탭 통합 드롭존
- 재투입 시 "이미 수집됨 — 건너뜀" 배너
- `dead` 잡 재시도 버튼

**Notes:** ING-06/ING-02/ING-07 요구사항 문구를 그대로 반영.

---

## Ask UI — 인용 마커 & 이중 Citation 카드

**User's choice:** 위와 동일하게 "recommand best practice" 지시로 자동 적용.

적용된 결정 (CONTEXT.md D-09~D-11):
- 절 옆 위첨자 번호 배지, 스트리밍 중 placeholder → `citations` 이벤트 도착 시 in-place 치환
- 클릭 시 사이드 패널에 위키/원문 카드 나란히 표시(원문은 char_start/char_end 하이라이트)
- 근거 없음 상태는 경고 카드로 시각적 구분

**Notes:** API-01의 SSE 이벤트 순서(meta→delta*→citations→done)와 D-02(05-CONTEXT.md) 앵커 별칭 스킴을 그대로 소비하도록 설계.

---

## Claude's Discretion

- **위키 뷰어(UI-05) 세부 UX** — 이번 세션에서 논의되지 않음. planner/researcher가 읽기전용 배너, 레드 링크 CTA, 상태 콜아웃을 기존 요구사항 문구대로 설계.
- **Cytoscape 지식 캔버스(UI-06) 세부 UX** — 이번 세션에서 논의되지 않음. planner/researcher가 렌즈 필터(`wiki_pages.category`)와 PostgREST 1000행 상한 처리, Phase 5의 그래프 읽기 RPC 경계(depth≤2·fan-out cap·cycle guard)를 기반으로 설계.
- 정확한 컴포넌트 분해, 디렉토리 구조, 상태관리 라이브러리 선택 — planner 재량.

## Deferred Ideas

None — discussion stayed within phase scope.
