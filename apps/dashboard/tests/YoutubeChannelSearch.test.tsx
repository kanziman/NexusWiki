import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockApiFetch = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/api-client")>(
      "@/lib/api-client",
    );
  return { ...actual, apiFetch: mockApiFetch };
});

import { ApiError } from "@/lib/api-client";
import { YoutubeChannelSearch } from "@/components/YoutubeChannelSearch";

function channel(id: string, title = "채널") {
  return {
    channel_id: id,
    title,
    description: "설명",
    thumbnail_url: null,
  };
}

async function search(keyword = "요리") {
  fireEvent.change(screen.getByTestId("youtube-search-input"), {
    target: { value: keyword },
  });
  fireEvent.click(screen.getByTestId("youtube-search-submit"));
}

describe("YoutubeChannelSearch", () => {
  beforeEach(() => {
    mockApiFetch.mockReset();
  });

  it("검색 결과의 채널을 렌더한다", async () => {
    mockApiFetch.mockResolvedValue({
      channels: [channel("UC1", "쿠킹채널")],
      next_page_token: null,
    });

    render(<YoutubeChannelSearch workspaceId="ws-1" />);
    await search();

    await waitFor(() => {
      expect(screen.getByText("쿠킹채널")).toBeInTheDocument();
    });
    const call = mockApiFetch.mock.calls[0][0] as string;
    expect(call).toContain("/workspaces/ws-1/youtube/channels");
    expect(call).toContain("q=%EC%9A%94%EB%A6%AC");
  });

  it("쿼터 소진을 '결과 없음'이 아니라 소진 사유로 안내한다", async () => {
    mockApiFetch.mockRejectedValue(new ApiError(503, "youtube_quota_exceeded"));

    render(<YoutubeChannelSearch workspaceId="ws-1" />);
    await search();

    const alert = await screen.findByTestId("youtube-search-error");
    // ⚠️ 이 문구가 "검색 결과가 없습니다"로 대체되면 사용자는 검색어를 계속 바꿔가며
    //    재시도하는데, 쿼터가 이미 없으므로 전부 실패한다.
    expect(alert).toHaveTextContent("YouTube 검색 횟수를 모두 썼습니다");
    expect(
      screen.queryByText("검색 결과가 없습니다. 다른 키워드로 시도해 보세요."),
    ).not.toBeInTheDocument();
  });

  it("업스트림 장애와 쿼터 소진을 다른 문구로 구분한다", async () => {
    mockApiFetch.mockRejectedValue(new ApiError(502, "youtube_unavailable"));

    render(<YoutubeChannelSearch workspaceId="ws-1" />);
    await search();

    const alert = await screen.findByTestId("youtube-search-error");
    expect(alert).toHaveTextContent("연결하지 못했습니다");
    expect(alert).not.toHaveTextContent("모두 썼습니다");
  });

  it("검색 실패 시 이전 결과를 남기지 않는다", async () => {
    mockApiFetch.mockResolvedValueOnce({
      channels: [channel("UC1", "첫검색채널")],
      next_page_token: null,
    });
    render(<YoutubeChannelSearch workspaceId="ws-1" />);
    await search();
    await waitFor(() => {
      expect(screen.getByText("첫검색채널")).toBeInTheDocument();
    });

    mockApiFetch.mockRejectedValueOnce(
      new ApiError(503, "youtube_quota_exceeded"),
    );
    await search("베이킹");

    // 실패했는데 이전 결과가 남아 있으면 사용자는 새 검색이 성공했다고 믿는다.
    await waitFor(() => {
      expect(screen.queryByText("첫검색채널")).not.toBeInTheDocument();
    });
  });

  it("다음 페이지를 이어서 붙인다", async () => {
    mockApiFetch.mockResolvedValueOnce({
      channels: [channel("UC1", "채널1")],
      next_page_token: "PAGE2",
    });
    render(<YoutubeChannelSearch workspaceId="ws-1" />);
    await search();
    await waitFor(() => {
      expect(screen.getByTestId("youtube-search-more")).toBeInTheDocument();
    });

    mockApiFetch.mockResolvedValueOnce({
      channels: [channel("UC2", "채널2")],
      next_page_token: null,
    });
    fireEvent.click(screen.getByTestId("youtube-search-more"));

    await waitFor(() => {
      expect(screen.getByText("채널2")).toBeInTheDocument();
    });
    // 이어붙이기지 교체가 아니다.
    expect(screen.getByText("채널1")).toBeInTheDocument();
    expect(mockApiFetch.mock.calls[1][0] as string).toContain(
      "page_token=PAGE2",
    );
  });

  it("더 보기 실패는 이미 받은 목록을 지우지 않는다", async () => {
    mockApiFetch.mockResolvedValueOnce({
      channels: [channel("UC1", "채널1")],
      next_page_token: "PAGE2",
    });
    render(<YoutubeChannelSearch workspaceId="ws-1" />);
    await search();
    await waitFor(() => {
      expect(screen.getByTestId("youtube-search-more")).toBeInTheDocument();
    });

    mockApiFetch.mockRejectedValueOnce(
      new ApiError(502, "youtube_unavailable"),
    );
    fireEvent.click(screen.getByTestId("youtube-search-more"));

    await screen.findByTestId("youtube-search-error");
    expect(screen.getByText("채널1")).toBeInTheDocument();
  });

  it("빈 키워드로는 요청하지 않는다", async () => {
    render(<YoutubeChannelSearch workspaceId="ws-1" />);
    fireEvent.change(screen.getByTestId("youtube-search-input"), {
      target: { value: "   " },
    });
    fireEvent.click(screen.getByTestId("youtube-search-submit"));

    expect(mockApiFetch).not.toHaveBeenCalled();
  });
});
