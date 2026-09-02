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
        expect(push).toHaveBeenCalledWith("/w/ws-1/wiki?deleted=true");
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
      expect(screen.getByTestId("select-all-checkbox")).toBeInTheDocument();
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

    it("마지막 페이지(2페이지)의 유일한 위키를 삭제하면 1페이지로 자동 보정된다", async () => {
      const ninePages = Array.from({ length: 9 }, (_, i) => ({
        id: `wiki-${i + 1}`,
        slug: `page-${i + 1}`,
        title: `위키문서-${i + 1}`,
        category: "concepts",
        content: `내용 ${i + 1}`,
        verification_status: "verified",
        disputed: false,
      }));

      apiFetch.mockResolvedValueOnce({
        id: "wiki-9",
        workspace_id: "ws-1",
        title: "위키문서-9",
      });

      render(
        <WikiLibrary
          pages={ninePages}
          workspaceId="ws-1"
          canVerify={true}
          isOwner={true}
        />,
      );

      // 2페이지로 이동
      const page2Btn = screen.getByRole("button", { name: "2 페이지" });
      fireEvent.click(page2Btn);
      expect(screen.getByText("위키문서-9")).toBeInTheDocument();

      // 9번 위키 삭제
      const deleteBtn = screen.getByTestId("delete-wiki-item-wiki-9");
      fireEvent.click(deleteBtn);
      const confirmBtn = screen.getByTestId("confirm-delete-wiki-item-btn");
      fireEvent.click(confirmBtn);

      // 1페이지로 자동 이동하여 1페이지 항목들이 보여야 함
      await waitFor(() => {
        expect(screen.getByText("위키문서-1")).toBeInTheDocument();
        expect(screen.queryByText("위키문서-9")).not.toBeInTheDocument();
      });
    });
  });
});
