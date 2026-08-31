import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const apiFetch = vi.fn();
vi.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/components/JobStepper", () => ({
  JobStepper: () => <div data-testid="job-stepper" />,
}));

vi.mock("@/components/Dropzone", () => ({
  Dropzone: () => <div data-testid="dropzone" />,
}));

vi.mock("@/components/MarkdownViewer", () => ({
  MarkdownViewer: ({ content }: { content: string }) => <div>{content}</div>,
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(),
}));

import { SourceDetailContent } from "@/components/SourceDetailContent";
import { SourcesList } from "@/components/SourcesList";

describe("Source Deletion", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("SourceDetailContent", () => {
    const sampleSource = {
      id: "src-1",
      title: "삭제할 소스.pdf",
      source_type: "file",
      mime_type: "application/pdf",
      byte_size: 1024,
      content_hash: "hash-1",
      created_at: "2026-08-12T00:00:00Z",
      content: "본문 내용",
    };

    it("소유자가 아니면 소스 삭제 버튼이 노출되지 않는다", () => {
      render(
        <SourceDetailContent
          workspaceId="ws-1"
          source={sampleSource}
          chunks={[]}
          citingPages={[]}
          isOwner={false}
        />,
      );

      expect(screen.queryByTestId("delete-source-btn")).not.toBeInTheDocument();
    });

    it("소유자일 때 소스 삭제 버튼이 노출되고 삭제 모달에서 영구 삭제를 실행할 수 있다", async () => {
      apiFetch.mockResolvedValueOnce({ id: "src-1", workspace_id: "ws-1" });

      render(
        <SourceDetailContent
          workspaceId="ws-1"
          source={sampleSource}
          chunks={[]}
          citingPages={[]}
          isOwner={true}
        />,
      );

      const deleteBtn = screen.getByTestId("delete-source-btn");
      expect(deleteBtn).toBeInTheDocument();

      fireEvent.click(deleteBtn);

      expect(screen.getByText("원문 소스 영구 삭제")).toBeInTheDocument();
      expect(screen.getAllByText(/삭제할 소스\.pdf/).length).toBeGreaterThan(0);

      const confirmBtn = screen.getByTestId("confirm-delete-source-btn");
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(apiFetch).toHaveBeenCalledWith(
          "/workspaces/ws-1/sources/src-1",
          {
            method: "DELETE",
          },
        );
        expect(push).toHaveBeenCalledWith("/w/ws-1/sources?deleted=true");
      });
    });
  });

  describe("SourcesList", () => {
    const sampleSources = [
      {
        id: "src-1",
        title: "설계문서.pdf",
        source_type: "file",
        mime_type: "application/pdf",
        byte_size: 1024,
        created_at: "2026-08-12T00:00:00Z",
        content_hash: "hash-1",
      },
    ];

    it("소유자가 아니면 목록 행에 삭제 아이콘 버튼이 없다", () => {
      render(
        <SourcesList
          workspaceId="ws-1"
          initialSources={sampleSources}
          isOwner={false}
        />,
      );

      expect(
        screen.queryByTestId("delete-source-btn-src-1"),
      ).not.toBeInTheDocument();
    });

    it("소유자일 때 목록에서 삭제 버튼을 누르고 모달에서 영구 삭제하면 목록에서 사라진다", async () => {
      apiFetch.mockResolvedValueOnce({ id: "src-1", workspace_id: "ws-1" });

      render(
        <SourcesList
          workspaceId="ws-1"
          initialSources={sampleSources}
          isOwner={true}
        />,
      );

      const deleteBtn = screen.getByTestId("delete-source-btn-src-1");
      expect(deleteBtn).toBeInTheDocument();

      fireEvent.click(deleteBtn);

      expect(screen.getByText("원문 소스 영구 삭제")).toBeInTheDocument();

      const confirmBtn = screen.getByTestId("confirm-delete-source-btn");
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(apiFetch).toHaveBeenCalledWith(
          "/workspaces/ws-1/sources/src-1",
          {
            method: "DELETE",
          },
        );
      });

      await waitFor(() => {
        expect(screen.queryByText("설계문서.pdf")).not.toBeInTheDocument();
        expect(
          screen.getByText("'설계문서.pdf' 원본 소스가 영구 삭제되었습니다."),
        ).toBeInTheDocument();
      });
    });

    it("마지막 페이지(2페이지)의 유일한 항목을 삭제하면 1페이지로 자동 보정된다", async () => {
      const nineSources = Array.from({ length: 9 }, (_, i) => ({
        id: `src-${i + 1}`,
        title: `문서-${i + 1}.pdf`,
        source_type: "file",
        mime_type: "application/pdf",
        byte_size: 1024,
        created_at: "2026-08-12T00:00:00Z",
        content_hash: `hash-${i + 1}`,
      }));

      apiFetch.mockResolvedValueOnce({ id: "src-9", workspace_id: "ws-1" });

      render(
        <SourcesList
          workspaceId="ws-1"
          initialSources={nineSources}
          isOwner={true}
        />,
      );

      // 2페이지로 이동
      const page2Btn = screen.getByRole("button", { name: "2 페이지" });
      fireEvent.click(page2Btn);
      expect(screen.getByText("문서-9.pdf")).toBeInTheDocument();

      // 9번 문서 삭제
      const deleteBtn = screen.getByTestId("delete-source-btn-src-9");
      fireEvent.click(deleteBtn);
      const confirmBtn = screen.getByTestId("confirm-delete-source-btn");
      fireEvent.click(confirmBtn);

      // 1페이지로 자동 이동하여 1페이지 항목들이 보여야 함
      await waitFor(() => {
        expect(screen.getByText("문서-1.pdf")).toBeInTheDocument();
        expect(screen.queryByText("문서-9.pdf")).not.toBeInTheDocument();
      });
    });
  });
});
