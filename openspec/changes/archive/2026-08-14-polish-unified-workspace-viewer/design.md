## Context

See proposal.md - Why. `ContentViewer.tsx`의 현재 탭 마크업:

```tsx
<div role="tablist" aria-label="콘텐츠 뷰어" ...>
  {TABS.map((item) => (
    <button role="tab" aria-selected={tab === item.id} onClick={...}>{item.label}</button>
  ))}
</div>
<div className="flex-1">{/* 활성 탭만 렌더 */}</div>
```

## Goals / Non-Goals

**Goals:**
- 네 항목(그래프 메뉴, 높이 유틸리티, workspace_id 스코프, 탭 접근성)을 전부 이번 change로 닫는다.

**Non-Goals:**
- 탭 콘텐츠 자체(위키/소스/그래프/마인드맵 렌더링 로직) 변경 — 이미 HHH-20에서 구현됨, 이번엔 껍데기(nav, 레이아웃, 접근성)만 다룬다.
- `GraphLensFilter`의 미사용 `workspaceId` prop 정리 — 이 change의 발견 범위 밖(별도 사소한 이슈), 손대지 않는다.

## Decisions

- **탭 ARIA 패턴을 W3C APG 표준대로 완전히 구현**: `role="tablist"`/`"tab"`을 이미 선언해놓고 절반만 구현된 상태였다 — 절반 구현보다는 제대로 하거나(`role="group"`으로 낮추거나) 둘 중 하나인데, 콘텐츠가 상호 배타적 뷰(문서/소스/그래프/마인드맵)라 의미상 진짜 탭이 맞다. `role="group"`으로 낮추지 않고 마저 구현한다: 각 탭 버튼에 `id="tab-<tabId>"`/`aria-controls="panel-<tabId>"`, 패널에 `id="panel-<tabId>"`/`role="tabpanel"`/`aria-labelledby="tab-<tabId>"`. 방향키(←/→)로 포커스 이동 + roving `tabIndex`(활성 탭만 0, 나머지 -1) — `GraphLensFilter`의 칩 그룹(`role="group"`, 전부 tabIndex 기본값)과는 의도적으로 다른 패턴이다: 칩은 다중 선택 가능한 필터이고, 이 탭은 상호 배타적 뷰 전환이라 시맨틱이 다르다.
- **높이 유틸리티는 인라인 style 리터럴로**: `GraphCanvas.tsx:295-299`/`CitationSidePanel.tsx:114-115`와 동일하게, `calc(100vh - var(--spacing-xxl) * 2)`를 인라인 `style`의 문자열로 넣는다 — 새 패턴을 만들지 않고 이미 두 곳에서 검증된 회피법을 재사용.

## Risks / Trade-offs

- [Risk] 화살표 키 이동을 추가하면서 기존 Tab 키 포커스 이동 동작을 깨뜨릴 수 있음 → Mitigation: roving tabindex는 W3C APG 표준 패턴이고, Tab 키는 여전히 탭 그룹 전체를 하나의 정지점으로 다루며(활성 탭만 tabIndex 0) 진입/이탈은 그대로 동작한다 — 테스트로 확인.
