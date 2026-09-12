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
import {
  YoutubeVideoList,
  formatCount,
  formatDuration,
  resultLabel,
  summarize,
} from "@/components/YoutubeVideoList";

const CHANNEL = {
  channel_id: "UC1",
  title: "쿠킹채널",
  description: "설명",
  thumbnail_url: null,
  subscriber_count: null,
  video_count: null,
  handle: null,
};

function video(id: string, overrides: Record<string, unknown> = {}) {
  return {
    video_id: id,
    title: `영상 ${id}`,
    published_at: "2026-01-02T03:04:05Z",
    duration_seconds: 754,
    thumbnail_url: null,
    has_captions: null,
    view_count: null,
    like_count: null,
    ...overrides,
  };
}

function renderList() {
  return render(
    <YoutubeVideoList
      workspaceId="ws-1"
      channel={CHANNEL}
      onBack={() => undefined}
    />,
  );
}

describe("formatDuration", () => {
  it("길이를 모르는 것과 0초를 구분한다", () => {
    // 서버가 `null`을 보내는 이유가 이 구분이다 — 0:00으로 접으면 "빈 영상"으로 읽힌다.
    expect(formatDuration(null)).toBe("길이 정보 없음");
    expect(formatDuration(0)).toBe("0:00");
  });

  it("한 시간을 넘으면 시:분:초로 쓴다", () => {
    expect(formatDuration(754)).toBe("12:34");
    expect(formatDuration(3725)).toBe("1:02:05");
  });
});

describe("formatCount", () => {
  it("null은 빈 문자열이다 — 0으로 접지 않는다", () => {
    expect(formatCount(null)).toBe("");
  });

  it("천 단위 구분자를 붙인다", () => {
    expect(formatCount(12345)).toBe("12,345");
  });
});

describe("resultLabel", () => {
  it("이미 수집됨을 실패 문구로 뭉개지 않는다", () => {
    expect(
      resultLabel({ video_id: "v1", status: "already_collected" }),
    ).toContain("이미 수집한");
    expect(
      resultLabel({ video_id: "v1", status: "already_collected" }),
    ).not.toContain("실패");
  });

  it("모르는 사유도 빈 문구로 두지 않는다", () => {
    // 토큰이 늘었는데 문구 표를 갱신하지 않으면 배지가 비어버린다.
    expect(
      resultLabel({ video_id: "v1", status: "failed", reason: "새로운토큰" }),
    ).toBe("수집하지 못했습니다.");
  });
});

describe("summarize", () => {
  it("등록·이미 수집됨·실패를 한 숫자로 합치지 않는다", () => {
    const text = summarize([
      { video_id: "a", status: "registered" },
      { video_id: "b", status: "already_collected" },
      { video_id: "c", status: "failed", reason: "internal" },
    ]);
    expect(text).toBe("1건 수집 시작 · 1건 이미 수집됨 · 1건 실패");
  });

  it("전부 성공하면 군더더기를 붙이지 않는다", () => {
    expect(summarize([{ video_id: "a", status: "registered" }])).toBe(
      "1건 수집 시작",
    );
  });
});

describe("YoutubeVideoList", () => {
  beforeEach(() => {
    mockApiFetch.mockReset();
  });

  it("제목·게시일·길이와 함께 영상 목록을 렌더한다", async () => {
    mockApiFetch.mockResolvedValue({
      videos: [video("v1")],
      next_page_token: null,
    });

    renderList();

    await waitFor(() => {
      expect(screen.getByText("영상 v1")).toBeInTheDocument();
    });
    expect(screen.getByText("12:34")).toBeInTheDocument();
    expect(screen.getByText("2026년 1월 2일")).toBeInTheDocument();
    expect(mockApiFetch.mock.calls[0][0] as string).toContain(
      "/workspaces/ws-1/youtube/channels/UC1/videos",
    );
  });

  it("has_captions 값과 무관하게 자막 배지를 표시하지 않고 선택도 막지 않는다", async () => {
    // ⚠️ YouTube의 contentDetails.caption은 공식 게시 자막 트랙 여부만 반영해
    // 대부분의 자동 생성 자막 영상에서 false로 온다 — 배지를 두면 거의 모든
    // 영상에 경고가 떠 신호 가치가 없어진다(실제 수집은 비공식 경로를 쓴다).
    mockApiFetch.mockResolvedValue({
      videos: [video("v1", { has_captions: false })],
      next_page_token: null,
    });

    renderList();

    await waitFor(() => {
      expect(screen.getByText("영상 v1")).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("youtube-video-no-captions-v1"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("youtube-video-select-v1")).not.toBeDisabled();
  });

  it("조회수·좋아요 수를 표시하고, 없는 값은 조용히 생략한다", async () => {
    mockApiFetch.mockResolvedValue({
      videos: [
        video("v1", { view_count: 12345, like_count: 678 }),
        video("v2", { view_count: 99, like_count: null }),
      ],
      next_page_token: null,
    });

    renderList();

    await waitFor(() => {
      expect(screen.getByText("조회수 12,345회")).toBeInTheDocument();
    });
    expect(screen.getByText("좋아요 678개")).toBeInTheDocument();
    expect(screen.getByText("조회수 99회")).toBeInTheDocument();
    expect(screen.queryByText(/좋아요 0개/)).not.toBeInTheDocument();
  });

  it("다음 페이지를 이어서 붙인다", async () => {
    mockApiFetch.mockResolvedValueOnce({
      videos: [video("v1")],
      next_page_token: "PAGE2",
    });
    renderList();
    await waitFor(() => {
      expect(screen.getByTestId("youtube-videos-more")).toBeInTheDocument();
    });

    mockApiFetch.mockResolvedValueOnce({
      videos: [video("v2")],
      next_page_token: null,
    });
    fireEvent.click(screen.getByTestId("youtube-videos-more"));

    await waitFor(() => {
      expect(screen.getByText("영상 v2")).toBeInTheDocument();
    });
    // 이어붙이기지 교체가 아니다.
    expect(screen.getByText("영상 v1")).toBeInTheDocument();
    expect(mockApiFetch.mock.calls[1][0] as string).toContain(
      "page_token=PAGE2",
    );
  });

  it("사라진 채널을 '영상 없음'이 아니라 소멸 사유로 안내한다", async () => {
    mockApiFetch.mockRejectedValue(
      new ApiError(404, "youtube_channel_not_found"),
    );

    renderList();

    const alert = await screen.findByTestId("youtube-videos-error");
    expect(alert).toHaveTextContent("더 이상 찾을 수 없습니다");
    expect(
      screen.queryByText("이 채널에는 아직 수집할 수 있는 영상이 없습니다."),
    ).not.toBeInTheDocument();
  });

  it("쿼터 소진과 업스트림 장애를 다른 문구로 구분한다", async () => {
    mockApiFetch.mockRejectedValue(new ApiError(503, "youtube_quota_exceeded"));
    const { unmount } = renderList();
    expect(await screen.findByTestId("youtube-videos-error")).toHaveTextContent(
      "모두 썼습니다",
    );
    unmount();

    mockApiFetch.mockRejectedValue(new ApiError(502, "youtube_unavailable"));
    renderList();
    const alert = await screen.findByTestId("youtube-videos-error");
    expect(alert).toHaveTextContent("연결하지 못했습니다");
    expect(alert).not.toHaveTextContent("모두 썼습니다");
  });

  it("더 보기 실패는 이미 받은 목록을 지우지 않는다", async () => {
    mockApiFetch.mockResolvedValueOnce({
      videos: [video("v1")],
      next_page_token: "PAGE2",
    });
    renderList();
    await screen.findByTestId("youtube-videos-more");

    mockApiFetch.mockRejectedValueOnce(
      new ApiError(502, "youtube_unavailable"),
    );
    fireEvent.click(screen.getByTestId("youtube-videos-more"));

    await screen.findByTestId("youtube-videos-error");
    expect(screen.getByText("영상 v1")).toBeInTheDocument();
  });
});
