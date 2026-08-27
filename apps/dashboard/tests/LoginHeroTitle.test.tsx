import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoginHeroTitle } from "@/components/LoginHeroTitle";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("LoginHeroTitle", () => {
  it("감소 모션에서는 밑줄을 즉시 완성 상태로 렌더링한다", () => {
    Object.defineProperty(window, "matchMedia", {
      configurable: true,
      value: vi.fn().mockReturnValue({
        matches: true,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    });

    render(<LoginHeroTitle />);

    expect(screen.getByText("답으로 연결하다.")).toHaveClass("is-complete");
  });
});
