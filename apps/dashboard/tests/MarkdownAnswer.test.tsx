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
    expect(screen.getByText("pnpm test").closest("pre")).not.toBeNull();
    expect(screen.getByRole("button", { name: "1" })).toHaveAttribute(
      "data-kind",
      "source",
    );
  });

  it("SQL 펜스 코드 블록은 위키 본문과 같이 맞춤법 검사를 끈다", () => {
    const { container } = render(
      <MarkdownAnswer
        segments={[
          {
            type: "text",
            value:
              "```sql\nFOREIGN KEY (parent_id, workspace_id)\nREFERENCES parent_table (id, workspace_id)\n```",
          },
        ]}
        resolved
        onMarkerClick={vi.fn()}
      />,
    );

    const pre = container.querySelector("pre");
    expect(pre).toHaveAttribute("spellcheck", "false");
    expect(pre).toHaveAttribute("lang", "zxx");
    expect(pre).toHaveTextContent("parent_id");
    expect(container.querySelector("pre code")).toBeNull();
  });

  it("SQL snake_case 식별자를 이탤릭으로 접지 않는다", () => {
    const { container } = render(
      <MarkdownAnswer
        segments={[
          {
            type: "text",
            value:
              "| 단계 | 검증기준 |\n| --- | --- |\n| 1 | wiki_pages_sources_idx 적용 후 Bitmap Index Scan |",
          },
        ]}
        resolved
        onMarkerClick={vi.fn()}
      />,
    );

    expect(container.querySelector("em")).toBeNull();
    expect(container.textContent).toContain("wiki_pages_sources_idx");
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
