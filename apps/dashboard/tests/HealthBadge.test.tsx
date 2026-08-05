import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HealthBadge } from "@/components/HealthBadge";

describe("HealthBadge", () => {
  it("상태별 한국어 라벨과 안정적인 상태 속성을 렌더링한다", () => {
    const { rerender } = render(<HealthBadge status="ok" />);

    expect(screen.getByText("정상")).toHaveAttribute("data-status", "ok");

    rerender(<HealthBadge status="degraded" />);
    expect(screen.getByText("저하")).toHaveAttribute("data-status", "degraded");

    rerender(<HealthBadge status="unknown" />);
    expect(screen.getByText("알 수 없음")).toHaveAttribute(
      "data-status",
      "unknown",
    );
  });
});
