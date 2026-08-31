import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
vi.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

import { WikiLibrary, WikiLibraryPage } from "@/components/WikiLibrary";

describe("WikiLibrary Bulk Actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const samplePages: WikiLibraryPage[] = [
    {
      id: "wiki-1",
      slug: "doc-1",
      title: "아키텍처 개요",
      category: "concepts",
      content: "아키텍처 상세 내용",
      verification_status: "unverified",
      disputed: false,
    },
    {
      id: "wiki-2",
      slug: "doc-2",
      title: "API 명세",
      category: "guides",
      content: "API 엔드포인트 설명",
      verification_status: "unverified",
      disputed: false,
    },
  ];

  it("canVerify=false 일 때는 체크박스와 일괄 작업 툴바가 노출되지 않는다", () => {
    render(
      <WikiLibrary pages={samplePages} workspaceId="ws-1" canVerify={false} />,
    );

    expect(screen.queryByTestId("select-all-checkbox")).not.toBeInTheDocument();
    expect(screen.queryByTestId("select-wiki-wiki-1")).not.toBeInTheDocument();
    expect(screen.queryByTestId("bulk-action-bar")).not.toBeInTheDocument();
  });

  it("canVerify=true 일 때 체크박스를 선택하면 일괄 작업 바가 노출되고 일괄 검증을 실행할 수 있다", async () => {
    apiFetch.mockResolvedValueOnce({
      verified_count: 2,
      verified_pages: [
        {
          id: "wiki-1",
          slug: "doc-1",
          verification_status: "verified",
          verified_by: "user-1",
          verified_at: "2026-08-31T00:00:00Z",
          expires_at: null,
          disputed: false,
        },
        {
          id: "wiki-2",
          slug: "doc-2",
          verification_status: "verified",
          verified_by: "user-1",
          verified_at: "2026-08-31T00:00:00Z",
          expires_at: null,
          disputed: false,
        },
      ],
    });

    render(
      <WikiLibrary pages={samplePages} workspaceId="ws-1" canVerify={true} />,
    );

    const selectAllCheckbox = screen.getByTestId("select-all-checkbox");
    expect(selectAllCheckbox).toBeInTheDocument();

    // 전체 선택 클릭
    fireEvent.click(selectAllCheckbox);

    expect(screen.getByTestId("bulk-action-bar")).toBeInTheDocument();
    expect(screen.getByText("2개 문서 선택됨")).toBeInTheDocument();

    const bulkVerifyBtn = screen.getByTestId("bulk-verify-btn");
    fireEvent.click(bulkVerifyBtn);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/workspaces/ws-1/wiki/bulk-verify",
        {
          method: "POST",
          body: {
            page_ids: ["wiki-1", "wiki-2"],
            verification_status: "verified",
          },
        },
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText("2개의 문서가 검증 완료되었습니다."),
      ).toBeInTheDocument();
      expect(screen.queryByTestId("bulk-action-bar")).not.toBeInTheDocument();
    });
  });

  it("선택 일괄 발행을 누르면 bulk-publish API를 호출하고 피드백을 표시한다", async () => {
    apiFetch.mockResolvedValueOnce({
      published_count: 1,
      published_pages: [
        {
          wiki_page_id: "wiki-1",
          workspace_id: "ws-1",
          published_slug: "doc-1",
          workspace_slug: "ws-slug",
          published_at: "2026-08-31T00:00:00Z",
          public_path: "/p/ws-slug/doc-1",
        },
      ],
    });

    render(
      <WikiLibrary pages={samplePages} workspaceId="ws-1" canVerify={true} />,
    );

    const selectDoc1 = screen.getByTestId("select-wiki-wiki-1");
    fireEvent.click(selectDoc1);

    expect(screen.getByText("1개 문서 선택됨")).toBeInTheDocument();

    const bulkPublishBtn = screen.getByTestId("bulk-publish-btn");
    fireEvent.click(bulkPublishBtn);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/workspaces/ws-1/wiki/bulk-publish",
        {
          method: "POST",
          body: {
            page_ids: ["wiki-1"],
          },
        },
      );
    });

    await waitFor(() => {
      expect(
        screen.getByText("1개의 문서가 공개 발행되었습니다."),
      ).toBeInTheDocument();
    });
  });
});
