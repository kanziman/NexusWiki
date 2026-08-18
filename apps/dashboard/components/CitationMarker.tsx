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
        className="cite-pending"
      >
        {" "}
      </span>
    );
  }

  // .cite / .cite.source 는 섹션 15(위키 리더)가 소유하는 공용 마커다. 리더와
  // 대화가 같은 물건을 가리키므로 두 화면이 갈라지면 안 된다 — 이중 Citation 의
  // 두 출처(원문 청크 · 위키 페이지)를 색으로 구분하는 규칙도 그쪽에 있다.
  return (
    <button
      type="button"
      data-testid="citation-marker-resolved"
      data-kind={part.kind}
      onClick={() => onClick?.(part)}
      className={`cite ${part.kind === "source" ? "source" : ""}`}
    >
      {index + 1}
    </button>
  );
}
