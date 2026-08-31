import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push,
  }),
}));

const apiFetch = vi.fn();
vi.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

import { WikiLibrary } from "@/components/WikiLibrary";
import { WikiPageContent } from "@/components/WikiPageContent";

describe("Wiki Deletion (Individual)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const samplePage = {
    id: "wiki-1",
    slug: "sample-doc",
    title: "아키텍처 가이드",
    content: "## 섹션 1\n가이드 내용",
    category: "guides",
    verification_status: "verified",
    verified_by: "user-1",
    verified_at: "2026-08-31T00:00:00Z",
    expires_at: null,
    disputed: false,
  };

  describe("WikiPageContent Deletion", () => {
    it("isOwner=false 일 때는 문서 삭제 버튼이 노출되지 않는다", () => {
      render(
        <WikiPageContent
          page={samplePage}
          links={[]}
          workspaceId="ws-1"
          workspaceSlug="my-workspace"
          canVerify={true}
          isOwner={false}
          initialBookmarked={false}
          initialPublishedSlug={null}
        />,
      );

      expect(screen.queryByTestId("delete-wiki-btn")).not.toBeInTheDocument();
    });

    it("isOwner=true 일 때는 문서 삭제 버튼이 노출되고 삭제 확인 모달을 통해 영구 삭제할 수 있다", async () => {
      apiFetch.mockResolvedValueOnce({
        id: "wiki-1",
        workspace_id: "ws-1",
        title: "아키텍처 가이드",
      });

      render(
        <WikiPageContent
          page={samplePage}
          links={[]}
          workspaceId="ws-1"
          workspaceSlug="my-workspace"
          canVerify={true}
          isOwner={true}
          initialBookmarked={false}
          initialPublishedSlug={null}
        />,
      );

      const deleteBtn = screen.getByTestId("delete-wiki-btn");
      expect(deleteBtn).toBeInTheDocument();

      fireEvent.click(deleteBtn);

      expect(screen.getByText("위키 문서 영구 삭제")).toBeInTheDocument();
      expect(
        screen.getAllByText(/아키텍처 가이드/).length,
      ).toBeGreaterThanOrEqual(1);

      const confirmBtn = screen.getByTestId("confirm-delete-wiki-btn");
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(apiFetch).toHaveBeenCalledWith("/workspaces/ws-1/wiki/wiki-1", {
          method: "DELETE",
        });
      });

      await waitFor(() => {
        expect(push).toHaveBeenCalledWith("/w/ws-1/wiki");
      });
    });
  });

  describe("WikiLibrary Item Deletion", () => {
    it("isOwner=false 일 때는 개별 삭제 아이콘이 노출되지 않는다", () => {
      render(
        <WikiLibrary
          pages={[samplePage]}
          workspaceId="ws-1"
          canVerify={true}
          isOwner={false}
        />,
      );

      expect(
        screen.queryByTestId("delete-wiki-item-wiki-1"),
      ).not.toBeInTheDocument();
    });

    it("isOwner=true 일 때 개별 삭제 아이콘을 클릭하여 문서를 영구 삭제하면 목록에서 제거된다", async () => {
      apiFetch.mockResolvedValueOnce({
        id: "wiki-1",
        workspace_id: "ws-1",
        title: "아키텍처 가이드",
      });

      render(
        <WikiLibrary
          pages={[samplePage]}
          workspaceId="ws-1"
          canVerify={true}
          isOwner={true}
        />,
      );

      const itemDeleteBtn = screen.getByTestId("delete-wiki-item-wiki-1");
      expect(itemDeleteBtn).toBeInTheDocument();

      fireEvent.click(itemDeleteBtn);

      expect(screen.getByText("위키 문서 영구 삭제")).toBeInTheDocument();

      const confirmBtn = screen.getByTestId("confirm-delete-wiki-item-btn");
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(apiFetch).toHaveBeenCalledWith("/workspaces/ws-1/wiki/wiki-1", {
          method: "DELETE",
        });
      });

      await waitFor(() => {
        expect(
          screen.getByText("'아키텍처 가이드' 문서가 영구 삭제되었습니다."),
        ).toBeInTheDocument();
        expect(
          screen.queryByTestId("delete-wiki-item-wiki-1"),
        ).not.toBeInTheDocument();
      });
    });
  });
});
