import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/Dropzone", () => ({
  Dropzone: () => <div data-testid="dropzone" />,
}));

vi.mock("@/components/JobStepper", () => ({
  JobStepper: () => <div data-testid="job-stepper" />,
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(),
}));

import { SourcesList } from "@/components/SourcesList";

describe("SourcesList", () => {
  it("preserves the approved empty-state copy", () => {
    render(<SourcesList workspaceId="ws-1" initialSources={[]} />);

    expect(screen.getByText("아직 등록된 소스가 없습니다")).toBeInTheDocument();
    expect(
      screen.getByText(
        "파일을 드래그하거나 URL/텍스트를 붙여넣어 첫 소스를 추가하세요.",
      ),
    ).toBeInTheDocument();
  });

  it("keeps a truncated source title available to assistive technology", () => {
    const title =
      "A very long research source title that must remain available";
    render(
      <SourcesList
        workspaceId="ws-1"
        initialSources={[
          {
            id: "source-1",
            title,
            source_type: "text",
            created_at: "2026-08-12T00:00:00Z",
            content_hash: "hash-1",
          },
        ]}
      />,
    );

    const sourceTitle = screen.getByText(title);
    expect(sourceTitle).toHaveAttribute("title", title);
    expect(sourceTitle).toHaveAttribute("aria-label", title);
    expect(sourceTitle.closest("a")).toHaveAttribute(
      "href",
      "/w/ws-1/sources/source-1",
    );
    expect(screen.getByText("2026년 8월 12일")).toBeInTheDocument();
  });

  it("links '상세 보기' to the source detail route instead of expanding inline", () => {
    render(
      <SourcesList
        workspaceId="ws-1"
        initialSources={[
          {
            id: "source-1",
            title: "회의록",
            source_type: "text",
            created_at: "2026-08-12T00:00:00Z",
            content_hash: "hash-1",
          },
        ]}
      />,
    );

    const detailLink = screen.getByRole("link", { name: "상세 보기" });
    expect(detailLink).toHaveAttribute("href", "/w/ws-1/sources/source-1");
  });

  it("filters sources by MIME type tabs", () => {
    const sampleSources = [
      {
        id: "source-1",
        title: "설계문서.pdf",
        source_type: "file",
        mime_type: "application/pdf",
        created_at: "2026-08-12T00:00:00Z",
        content_hash: "hash-1",
      },
      {
        id: "source-2",
        title: "노트.md",
        source_type: "text",
        mime_type: "text/markdown",
        created_at: "2026-08-13T00:00:00Z",
        content_hash: "hash-2",
      },
    ];

    render(<SourcesList workspaceId="ws-1" initialSources={sampleSources} />);

    expect(screen.getByText("설계문서.pdf")).toBeInTheDocument();
    expect(screen.getByText("노트.md")).toBeInTheDocument();

    const pdfTab = screen.getByRole("tab", { name: /PDF/ });
    fireEvent.click(pdfTab);

    expect(screen.getByText("설계문서.pdf")).toBeInTheDocument();
    expect(screen.queryByText("노트.md")).not.toBeInTheDocument();

    const textTab = screen.getByRole("tab", { name: /텍스트\/마크다운/ });
    fireEvent.click(textTab);

    expect(screen.queryByText("설계문서.pdf")).not.toBeInTheDocument();
    expect(screen.getByText("노트.md")).toBeInTheDocument();
  });
});
