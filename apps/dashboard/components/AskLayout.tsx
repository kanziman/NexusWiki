"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

export type AskLayoutProps = {
  conversation: ReactNode;
  inspector: ReactNode;
};

const MIN_CONVERSATION_WIDTH = 420;
const MIN_INSPECT_WIDTH = 360;
const SPLITTER_WIDTH = 6;
const KEYBOARD_STEP = 24;

function clampToRange(value: number, max: number): number | null {
  if (max < MIN_INSPECT_WIDTH) return null;
  return Math.min(Math.max(value, MIN_INSPECT_WIDTH), max);
}

export function buildGridTemplateColumns(
  inspectWidth: number | null,
): string | undefined {
  if (inspectWidth === null) return undefined;
  return `minmax(${MIN_CONVERSATION_WIDTH}px, 1fr) ${SPLITTER_WIDTH}px ${inspectWidth}px`;
}

/**
 * Ask 화면의 대화 | 인용 인스펙터 2열 레이아웃 — 폭 조절 가능한 스플리터를
 * 소유한다(구 OD-09, checklists_v2.json UX-05). nexuswiki-design-system.css
 * 섹션 16이 "새 상호작용 계약이라 CSS만으로 끝나지 않는다"며 이식을 미룬
 * `.split`를 여기서 배선한다.
 *
 * 조작 전 기본 폭(CSS의 `minmax(360px, 42%)`가 실제로 얼마로 렌더되는지)은
 * ResizeObserver로 인스펙터(3번째 그리드 자식)를 측정해 얻는다 — 한 번이라도
 * 드래그/키보드로 조작한 뒤에는 `inspectWidth`가 정확한 값을 이미 들고 있으므로
 * 그쪽을 우선한다(`displayWidth`). observer 왕복을 기다리지 않아도 되니
 * aria-valuenow가 조작과 동기적으로 갱신된다.
 *
 * ⚠️ 컨테이너(.ask-layout) 자체도 ResizeObserver로 지켜본다 — LNB 접기/펼치기
 * (WorkspaceShell)처럼 window resize 없이도 폭이 바뀌는 경우가 있다. 대화
 * 최소(420px)+스플리터(6px)+인스펙터 최소(360px)를 더한 786px를 컨테이너가
 * 더는 감당 못 하면(예: 900px 미디어 쿼리 구간에서 드래그해 둔 값이 남아있을
 * 때) inspectWidth를 null로 되돌려 CSS 기본 트랙 값(브레이크포인트별로 더
 * 느슨한 최소치)에 넘긴다. 아직 786px 안에 들어오면 지정값을 새 여유 폭
 * 안으로만 재클램프한다.
 */
export function AskLayout({ conversation, inspector }: AskLayoutProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [inspectWidth, setInspectWidth] = useState<number | null>(null);
  const [renderedWidth, setRenderedWidth] = useState<number | null>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const inspectEl = containerRef.current?.lastElementChild;
    if (!inspectEl) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) setRenderedWidth(entry.contentRect.width);
    });
    observer.observe(inspectEl);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const max =
        entry.contentRect.width - MIN_CONVERSATION_WIDTH - SPLITTER_WIDTH;
      setInspectWidth((current) =>
        current === null ? current : clampToRange(current, max),
      );
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  function maxInspectWidth(): number | null {
    const container = containerRef.current;
    if (!container) return null;
    return (
      container.getBoundingClientRect().width -
      MIN_CONVERSATION_WIDTH -
      SPLITTER_WIDTH
    );
  }

  function clampInspectWidth(width: number): number | null {
    const max = maxInspectWidth();
    if (max === null) return null;
    return clampToRange(width, max);
  }

  function handlePointerDown(event: React.PointerEvent<HTMLDivElement>) {
    setDragging(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!dragging || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const max = rect.width - MIN_CONVERSATION_WIDTH - SPLITTER_WIDTH;
    const next = clampToRange(rect.right - event.clientX, max);
    if (next !== null) setInspectWidth(next);
  }

  function handlePointerUp(event: React.PointerEvent<HTMLDivElement>) {
    setDragging(false);
    event.currentTarget.releasePointerCapture(event.pointerId);
  }

  // OS 제스처나 탭 전환이 드래그 도중 포인터 시퀀스를 끊으면 pointerup 없이
  // capture만 사라진다 — dragging이 true로 굳으면 이후 아무 조작 없는
  // pointermove(단순 호버)에도 폭이 계속 바뀐다.
  function handlePointerCancel() {
    setDragging(false);
  }

  const displayWidth = inspectWidth ?? renderedWidth;

  // W3C APG separator 패턴 — 방향키로 값 이동, Home/End로 최소/최대값.
  // 왼쪽 화살표는 인스펙터 쪽으로 경계를 밀어 인스펙터 폭을 넓힌다(포인터
  // 드래그와 같은 방향 감각).
  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (displayWidth === null) return;
    const max = maxInspectWidth();
    if (max === null || max < MIN_INSPECT_WIDTH) return;

    let next: number | null = null;
    switch (event.key) {
      case "ArrowLeft":
        next = clampInspectWidth(displayWidth + KEYBOARD_STEP);
        break;
      case "ArrowRight":
        next = clampInspectWidth(displayWidth - KEYBOARD_STEP);
        break;
      case "Home":
        next = MIN_INSPECT_WIDTH;
        break;
      case "End":
        next = clampInspectWidth(max);
        break;
      default:
        return;
    }
    event.preventDefault();
    if (next !== null) setInspectWidth(next);
  }

  const max = maxInspectWidth();

  return (
    <div
      ref={containerRef}
      className="ask-layout"
      data-od-id="ask-conversation-screen"
      style={{ gridTemplateColumns: buildGridTemplateColumns(inspectWidth) }}
    >
      {conversation}
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="대화·인용 인스펙터 폭 조절"
        aria-valuenow={
          displayWidth !== null ? Math.round(displayWidth) : undefined
        }
        aria-valuemin={MIN_INSPECT_WIDTH}
        aria-valuemax={max !== null ? Math.round(max) : undefined}
        tabIndex={0}
        data-od-id="inspector-splitter"
        data-testid="ask-splitter"
        data-dragging={dragging ? "true" : undefined}
        className="ask-splitter"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerCancel}
        onLostPointerCapture={handlePointerCancel}
        onKeyDown={handleKeyDown}
      />
      {inspector}
    </div>
  );
}
