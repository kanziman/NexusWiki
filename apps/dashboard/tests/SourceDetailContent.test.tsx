import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/JobStepper", () => ({
  JobStepper: () => <div>처리 상태</div>,
}));

import { SourceDetailContent } from "@/components/SourceDetailContent";

describe("SourceDetailContent", () => {
  it("shows source trace data and lets a member select an ordered chunk", () => {
    render(
      <SourceDetailContent
        workspaceId="ws-1"
        source={{
          id: "source-1",
          title: "원문.md",
          source_type: "upload",
          mime_type: "text/markdown",
          created_at: "2026-08-22T00:00:00Z",
          content: "# 전체 원문",
        }}
        chunks={[
          {
            id: "chunk-1",
            raw_source_id: "source-1",
            chunk_index: 0,
            char_start: 0,
            char_end: 8,
            content: "첫 번째 청크",
          },
          {
            id: "chunk-2",
            raw_source_id: "source-1",
            chunk_index: 1,
            char_start: 9,
            char_end: 18,
            content: "두 번째 청크",
          },
        ]}
        citingPages={[
          {
            id: "wiki-1",
            title: "연결 문서",
            slug: "linked",
            category: "guides",
          },
        ]}
      />,
    );

    expect(
      screen.getByRole("link", { name: /원문 소스 목록/ }),
    ).toHaveAttribute("href", "/w/ws-1/sources");
    expect(screen.getByRole("link", { name: "연결 문서" })).toHaveAttribute(
      "href",
      "/w/ws-1/wiki/linked",
    );

    const secondChunk = screen.getByRole("button", { name: /청크 #2/ });
    fireEvent.click(secondChunk);
    expect(secondChunk).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("좌표: 9–18")).toBeInTheDocument();
  });

  it("shows explicit empty states without claiming indexing success", () => {
    render(
      <SourceDetailContent
        workspaceId="ws-1"
        source={{
          id: "source-1",
          title: "비어 있는 원문.txt",
          source_type: "upload",
          created_at: "2026-08-22T00:00:00Z",
          content: null,
        }}
        chunks={[]}
        citingPages={[]}
      />,
    );

    expect(screen.getByText("추출된 청크가 없습니다")).toBeInTheDocument();
    expect(
      screen.getByText(/아직 이 소스를 인용한 위키 문서가 없습니다/),
    ).toBeInTheDocument();
    expect(screen.queryByText("5채널 하이브리드 색인 완료")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "추출된 전체 원문" }));
    expect(
      screen.getByText("추출된 텍스트 내용이 없습니다."),
    ).toBeInTheDocument();
  });
});
