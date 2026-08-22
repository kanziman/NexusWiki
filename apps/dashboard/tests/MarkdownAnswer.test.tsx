import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MarkdownAnswer } from "@/components/MarkdownAnswer";
import type { AnchorPart, TextPart } from "@/lib/citation-anchors";

describe("MarkdownAnswer", () => {
  it("renders rich blocks while preserving resolved citation position", () => {
    const segments: (TextPart | AnchorPart)[] = [
      {
        type: "text",
        value:
          "## 결과\n1. 첫 단계\n2. 둘째 단계\n\n```bash\npnpm test\n```\n\n근거 ",
      },
      {
        type: "anchor",
        alias: "s1",
        kind: "source",
        id: "chunk-1",
      },
      { type: "text", value: " 확인" },
    ];

    render(
      <MarkdownAnswer segments={segments} resolved onMarkerClick={vi.fn()} />,
    );

    expect(screen.getByRole("heading", { name: "결과" })).toBeInTheDocument();
    expect(screen.getByRole("list").tagName).toBe("OL");
    expect(screen.getByText("pnpm test").closest("code")).not.toBeNull();
    expect(screen.getByRole("button", { name: "1" })).toHaveAttribute(
      "data-kind",
      "source",
    );
  });

  it("keeps unsafe links as text and safe links navigable", () => {
    render(
      <MarkdownAnswer
        segments={[
          {
            type: "text",
            value: "[안전](https://example.com) [위험](javascript:alert(1))",
          },
        ]}
        resolved
        onMarkerClick={vi.fn()}
      />,
    );

    expect(screen.getByRole("link", { name: "안전" })).toHaveAttribute(
      "href",
      "https://example.com",
    );
    expect(screen.getByText("위험").closest("a")).toBeNull();
  });
});
