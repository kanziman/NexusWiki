import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CitationSidePanel } from "@/components/CitationSidePanel";
import type { AnchorPart } from "@/lib/citation-anchors";

const singleMock = vi.fn();
const eqMock = vi.fn(() => ({ single: singleMock }));
const selectMock = vi.fn(() => ({ eq: eqMock }));
const fromMock = vi.fn(() => ({ select: selectMock }));

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    from: fromMock,
  }),
}));

describe("CitationSidePanel", () => {
  it("원문 인용 조회 실패/삭제 시 무한 로딩에 머물지 않고 안내 문구를 표시한다", async () => {
    singleMock.mockResolvedValueOnce({
      data: null,
      error: { message: "Not found" },
    });

    const part: AnchorPart = {
      type: "anchor",
      kind: "source",
      alias: "s1",
      id: "deleted-chunk-id",
    };

    render(
      <CitationSidePanel part={part} onClose={() => {}} workspaceId="ws-1" />,
    );

    await waitFor(() => {
      expect(
        screen.getByText("삭제되었거나 접근할 수 없는 원문 인용입니다."),
      ).toBeInTheDocument();
    });
  });

  it("위키 인용 조회 실패/삭제 시 무한 로딩에 머물지 않고 안내 문구를 표시한다", async () => {
    singleMock.mockResolvedValueOnce({
      data: null,
      error: { message: "Not found" },
    });

    const part: AnchorPart = {
      type: "anchor",
      kind: "wiki",
      alias: "w1",
      id: "deleted-wiki-id",
    };

    render(
      <CitationSidePanel part={part} onClose={() => {}} workspaceId="ws-1" />,
    );

    await waitFor(() => {
      expect(
        screen.getByText("삭제되었거나 접근할 수 없는 위키 문서입니다."),
      ).toBeInTheDocument();
    });
  });

  it("원문 청크가 정상 존재할 때는 청크 내용을 표시한다", async () => {
    singleMock.mockResolvedValueOnce({
      data: {
        id: "chunk-1",
        raw_source_id: "src-1",
        chunk_index: 2,
        char_start: 100,
        char_end: 200,
        content: "참조된 청크 본문 내용입니다.",
      },
    });

    const part: AnchorPart = {
      type: "anchor",
      kind: "source",
      alias: "s1",
      id: "chunk-1",
    };

    render(
      <CitationSidePanel part={part} onClose={() => {}} workspaceId="ws-1" />,
    );

    await waitFor(() => {
      expect(screen.getByText(/청크 #2/)).toBeInTheDocument();
      expect(
        screen.getByText("참조된 청크 본문 내용입니다."),
      ).toBeInTheDocument();
    });
  });
});
