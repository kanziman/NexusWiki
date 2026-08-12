import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CitationMarker } from "@/components/CitationMarker";
import type { AnchorPart } from "@/lib/citation-anchors";

const part: AnchorPart = {
  type: "anchor",
  kind: "source",
  alias: "s1",
  id: "uuid-1",
};

describe("CitationMarker", () => {
  it("resolved=false는 비활성 placeholder로 렌더되고 클릭해도 onClick이 호출되지 않는다", () => {
    const onClick = vi.fn();
    render(
      <CitationMarker
        part={part}
        index={0}
        resolved={false}
        onClick={onClick}
      />,
    );

    const placeholder = screen.getByTestId("citation-marker-placeholder");
    fireEvent.click(placeholder);

    expect(onClick).not.toHaveBeenCalled();
    // resolved=false에는 button 롤 자체가 없다 — onClick 배선이 아예 없다는
    // 증거(그냥 disabled 버튼이 아니라).
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("resolved=true는 번호 배지 버튼으로 렌더되고 클릭 시 onClick(part)가 호출된다", () => {
    const onClick = vi.fn();
    render(<CitationMarker part={part} index={2} resolved onClick={onClick} />);

    const button = screen.getByRole("button", { name: "3" });
    fireEvent.click(button);

    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith(part);
  });

  it("onClick이 주어지지 않아도 resolved=true 클릭은 에러 없이 무시된다", () => {
    render(<CitationMarker part={part} index={0} resolved />);
    const button = screen.getByRole("button", { name: "1" });
    expect(() => fireEvent.click(button)).not.toThrow();
  });
});
