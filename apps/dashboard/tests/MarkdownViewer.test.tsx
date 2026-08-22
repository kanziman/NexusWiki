import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MarkdownViewer } from "@/components/MarkdownViewer";

describe("MarkdownViewer", () => {
  it("renders ordered lists and rejects executable links", () => {
    render(
      <MarkdownViewer
        content={"1. 첫째\n2. 둘째\n\n[위험](data:text/html,bad)"}
      />,
    );

    expect(screen.getByRole("list").tagName).toBe("OL");
    expect(screen.getByText("위험").closest("a")).toBeNull();
  });
});
