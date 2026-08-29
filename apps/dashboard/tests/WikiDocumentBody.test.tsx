import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WikiDocumentBody } from "@/components/WikiDocumentBody";

describe("WikiDocumentBody", () => {
  it("표 칸의 긴 코드 칩은 칸 안에서 줄바꿈되어도 서로 겹치지 않게 각각 렌더한다", () => {
    const { container } = render(
      <WikiDocumentBody
        content={`| 근거 |
| --- |
| \`docs/ops/cloud-bootstrap-record.md\`, \`docs/ops/migration-0007-record.md\` |
`}
        linkMode="public"
      />,
    );
    const codes = container.querySelectorAll("td code");
    expect(codes).toHaveLength(2);
    expect(codes[0]).toHaveClass("whitespace-nowrap");
    expect(codes[1]).toHaveClass("whitespace-nowrap");
    expect(container.querySelector("td")).toHaveClass("align-top");
  });

  it("SQL snake_case 식별자를 이탤릭으로 접지 않는다", () => {
    const { container } = render(
      <WikiDocumentBody
        content={`| 단계 | 검증기준 |
| --- | --- |
| 1 | wiki_pages_sources_idx 적용 후 Bitmap Index Scan |
| 2 | raw_sources 삭제 시 source_chunks 가 cascade |
`}
        linkMode="internal"
      />,
    );

    expect(container.querySelector("em")).toBeNull();
    expect(container.textContent).toContain("wiki_pages_sources_idx");
    expect(container.textContent).toContain("source_chunks");
  });

  it("SQL 펜스 코드 블록은 맞춤법 검사를 끈다", () => {
    const { container } = render(
      <WikiDocumentBody
        content={
          "```sql\nselect rs.source_type from public.raw_sources rs;\n```"
        }
        linkMode="public"
      />,
    );
    const pre = container.querySelector("pre");
    expect(pre).toHaveAttribute("spellcheck", "false");
    expect(pre).toHaveAttribute("lang", "zxx");
    expect(pre).toHaveTextContent("source_type");
    expect(container.querySelector("pre code")).toBeNull();
  });

  it("단어 경계의 _이탤릭_ 은 유지한다", () => {
    const { container } = render(
      <WikiDocumentBody content="이것은 _강조_ 입니다" linkMode="public" />,
    );
    expect(container.querySelector("em")).toHaveTextContent("강조");
  });
});
