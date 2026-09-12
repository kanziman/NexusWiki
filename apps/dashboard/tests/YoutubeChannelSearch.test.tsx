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

function channel(
  id: string,
  title = "채널",
  overrides: Partial<{
    subscriber_count: number | null;
    video_count: number | null;
    handle: string | null;
  }> = {},
) {
  return {
    channel_id: id,
    title,
    description: "설명",
    thumbnail_url: null,
    subscriber_count: null,
    video_count: null,
    handle: null,
    ...overrides,
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

  it("기본 정렬·국가와 함께 검색하고, 언어 힌트는 선택 전까지 보내지 않는다", async () => {
    mockApiFetch.mockResolvedValue({ channels: [], next_page_token: null });

    render(<YoutubeChannelSearch workspaceId="ws-1" />);
    await search();

    await waitFor(() => expect(mockApiFetch).toHaveBeenCalled());
    const call = mockApiFetch.mock.calls[0][0] as string;
    expect(call).toContain("order=relevance");
    expect(call).toContain("region_code=KR");
    expect(call).not.toContain("relevance_language");
  });

  it("정렬·언어·국가를 바꾸면 다음 검색에 반영된다", async () => {
    mockApiFetch.mockResolvedValue({ channels: [], next_page_token: null });

    render(<YoutubeChannelSearch workspaceId="ws-1" />);
    fireEvent.change(screen.getByTestId("youtube-search-order"), {
      target: { value: "videoCount" },
    });
    fireEvent.change(screen.getByTestId("youtube-search-language"), {
      target: { value: "ko" },
    });
    fireEvent.change(screen.getByTestId("youtube-search-region"), {
      target: { value: "US" },
    });
    await search();

    await waitFor(() => expect(mockApiFetch).toHaveBeenCalled());
    const call = mockApiFetch.mock.calls[0][0] as string;
    expect(call).toContain("order=videoCount");
    expect(call).toContain("relevance_language=ko");
    expect(call).toContain("region_code=US");
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

  it("채널을 고르면 그 채널의 영상 목록으로 넘어간다", async () => {
    mockApiFetch.mockResolvedValueOnce({
      channels: [channel("UC1", "쿠킹채널")],
      next_page_token: null,
    });
    render(<YoutubeChannelSearch workspaceId="ws-1" />);
    await search();
    await screen.findByTestId("youtube-channel-UC1");

    mockApiFetch.mockResolvedValueOnce({
      videos: [
        {
          video_id: "v1",
          title: "김치찌개 끓이기",
          published_at: null,
          duration_seconds: 600,
          thumbnail_url: null,
          has_captions: null,
          view_count: null,
          like_count: null,
        },
      ],
      next_page_token: null,
    });
    fireEvent.click(screen.getByTestId("youtube-channel-UC1"));

    await waitFor(() => {
      expect(screen.getByText("김치찌개 끓이기")).toBeInTheDocument();
    });
    expect(mockApiFetch.mock.calls[1][0] as string).toContain(
      "/workspaces/ws-1/youtube/channels/UC1/videos",
    );
    // 검색 UI는 대체된다 — 두 목록이 같은 화면에 있으면 "더 보기"가 어느 쪽을 늘리는지
    // 알 수 없다.
    expect(
      screen.queryByTestId("youtube-search-submit"),
    ).not.toBeInTheDocument();
  });

  it("뒤로 가면 방금 검색한 결과가 그대로 남는다", async () => {
    mockApiFetch.mockResolvedValueOnce({
      channels: [channel("UC1", "쿠킹채널")],
      next_page_token: null,
    });
    render(<YoutubeChannelSearch workspaceId="ws-1" />);
    await search();
    await screen.findByTestId("youtube-channel-UC1");

    mockApiFetch.mockResolvedValueOnce({ videos: [], next_page_token: null });
    fireEvent.click(screen.getByTestId("youtube-channel-UC1"));
    await screen.findByTestId("youtube-videos-back");

    fireEvent.click(screen.getByTestId("youtube-videos-back"));

    // 검색을 다시 부르지 않는다 — 부르면 100유닛짜리 호출이 뒤로 가기마다 나간다.
    await waitFor(() => {
      expect(screen.getByText("쿠킹채널")).toBeInTheDocument();
    });
    expect(mockApiFetch).toHaveBeenCalledTimes(2);
  });

  it("구독자 수·영상 수·핸들을 배지로 렌더한다", async () => {
    mockApiFetch.mockResolvedValue({
      channels: [
        channel("UC1", "쿠킹채널", {
          subscriber_count: 45000,
          video_count: 120,
          handle: "@cookingchannel",
        }),
      ],
      next_page_token: null,
    });

    render(<YoutubeChannelSearch workspaceId="ws-1" />);
    await search();

    await waitFor(() => {
      expect(screen.getByText("쿠킹채널")).toBeInTheDocument();
    });
    expect(screen.getByText("@cookingchannel")).toBeInTheDocument();
    expect(screen.getByText("구독자 45,000명")).toBeInTheDocument();
    expect(screen.getByText("영상 120개")).toBeInTheDocument();
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
