import { render, screen } from "@testing-library/react";
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
    expect(screen.getByText("2026년 8월 12일")).toBeInTheDocument();
  });
});
