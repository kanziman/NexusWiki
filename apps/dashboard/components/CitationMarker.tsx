"use client";

import type { AnchorPart } from "@/lib/citation-anchors";

export type CitationMarkerProps = {
  part: AnchorPart;
  index: number;
  resolved: boolean;
  onClick?: (part: AnchorPart) => void;
};

/**
 * 인용 마커 배지 — 스트리밍 중에는 비활성 회색 placeholder, `citations` 이벤트
 * 도착 후에는 번호 붙은 클릭 가능 배지로 in-place 치환된다 (D-09).
 *
 * 관련 태스크: 06-06-PLAN.md Task 2
 * 설계 근거: 06-UI-SPEC.md Design System(Radius `--rounded-full`) + Color(hover/active
 *            시 `--color-primary`)
 *
 * ⚠️ `resolved={false}`일 때는 `<button>`이 아니라 `<span>`으로 렌더한다 — 클릭
 * 핸들러 자체를 배선하지 않는다(disabled 버튼이 아니다). T-06-18: 위조로 밝혀질
 * 앵커까지 포함해 해소 전 모든 앵커가 완전히 동일하게, 실제 링크와 조금도 다르지
 * 않게 비활성이어야 한다 — "클릭은 되지만 아무 일도 안 일어나는" 상태조차 만들지
 * 않는다.
 */
export function CitationMarker({
  part,
  index,
  resolved,
  onClick,
}: CitationMarkerProps) {
  if (!resolved) {
    return (
      <span
        aria-hidden="true"
        data-testid="citation-marker-placeholder"
        className="mx-xs inline-flex h-4 w-4 items-center justify-center rounded-full bg-hairline align-super text-muted"
        style={{
          font: "var(--font-caption)",
          fontSize: "10px",
          fontWeight: 600,
        }}
      >
        {" "}
      </span>
    );
  }

  return (
    <button
      type="button"
      data-testid="citation-marker-resolved"
      data-kind={part.kind}
      onClick={() => onClick?.(part)}
      className="mx-xs inline-flex h-4 w-4 items-center justify-center rounded-full bg-hairline align-super text-primary transition-colors hover:bg-primary hover:text-on-primary"
      style={{ font: "var(--font-caption)", fontSize: "10px", fontWeight: 600 }}
    >
      {index + 1}
    </button>
  );
}
