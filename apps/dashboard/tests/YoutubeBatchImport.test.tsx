/**
 * youtube-channel-import 슬라이스 3 — 다중 선택 일괄 수집과 영상별 결과 (Task 3.5).
 *
 * ⚠️ 이 파일이 지키는 계약 하나: **한 건의 결과가 다른 건의 결과를 가리지 않는다.**
 * 요약 한 줄로 합치거나 첫 실패에서 화면을 끊으면 사용자는 무엇을 다시 눌러야 하는지
 * 알 수 없게 된다.
 */

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
import { YoutubeVideoList } from "@/components/YoutubeVideoList";

const CHANNEL = {
  channel_id: "UC1",
  title: "쿠킹채널",
  description: "설명",
  thumbnail_url: null,
};

function video(id: string) {
  return {
    video_id: id,
    title: `영상 ${id}`,
    published_at: null,
    duration_seconds: 600,
    thumbnail_url: null,
  };
}

async function renderWithVideos(ids: string[]) {
  mockApiFetch.mockResolvedValueOnce({
    videos: ids.map(video),
    next_page_token: null,
  });
  render(
    <YoutubeVideoList
      workspaceId="ws-1"
      channel={CHANNEL}
      onBack={() => undefined}
    />,
  );
  await screen.findByTestId(`youtube-video-select-${ids[0]}`);
}

function select(id: string) {
  fireEvent.click(screen.getByTestId(`youtube-video-select-${id}`));
}

describe("YoutubeBatchImport", () => {
  beforeEach(() => {
    mockApiFetch.mockReset();
  });

  it("고른 영상만 한 요청으로 보낸다", async () => {
    await renderWithVideos(["v1", "v2", "v3"]);

    select("v1");
    select("v3");

    mockApiFetch.mockResolvedValueOnce({
      results: [
        { video_id: "v1", status: "registered", raw_source_id: "s1" },
        { video_id: "v3", status: "registered", raw_source_id: "s3" },
      ],
    });
    fireEvent.click(screen.getByTestId("youtube-ingest-selected"));

    await screen.findByTestId("youtube-batch-summary");
    const [path, init] = mockApiFetch.mock.calls[1] as [
      string,
      { method: string; body: Record<string, unknown> },
    ];
    expect(path).toBe("/workspaces/ws-1/sources/youtube-videos");
    expect(init.method).toBe("POST");
    // 고르지 않은 v2는 실려 나가지 않는다.
    expect(init.body).toEqual({
      channel_id: "UC1",
      videos: [
        { video_id: "v1", title: "영상 v1" },
        { video_id: "v3", title: "영상 v3" },
      ],
    });
  });

  it("선택하지 않으면 실행 버튼이 눌리지 않는다", async () => {
    await renderWithVideos(["v1"]);

    expect(screen.getByTestId("youtube-ingest-selected")).toBeDisabled();
    fireEvent.click(screen.getByTestId("youtube-ingest-selected"));
    // 목록 조회 한 번 말고는 나가지 않는다.
    expect(mockApiFetch).toHaveBeenCalledTimes(1);
  });

  it("전체 선택으로 이 페이지의 영상을 한 번에 고른다", async () => {
    await renderWithVideos(["v1", "v2"]);

    fireEvent.click(screen.getByTestId("youtube-select-all"));

    expect(screen.getByTestId("youtube-video-select-v1")).toBeChecked();
    expect(screen.getByTestId("youtube-video-select-v2")).toBeChecked();
    expect(screen.getByTestId("youtube-ingest-selected")).toHaveTextContent(
      "선택한 2편 수집",
    );
  });

  it("영상별 결과를 각각 표시하고 요약에서 합치지 않는다", async () => {
    await renderWithVideos(["v1", "v2", "v3"]);
    fireEvent.click(screen.getByTestId("youtube-select-all"));

    mockApiFetch.mockResolvedValueOnce({
      results: [
        { video_id: "v1", status: "registered", raw_source_id: "s1" },
        { video_id: "v2", status: "already_collected", raw_source_id: "s0" },
        { video_id: "v3", status: "failed", reason: "internal" },
      ],
    });
    fireEvent.click(screen.getByTestId("youtube-ingest-selected"));

    await waitFor(() => {
      expect(screen.getByTestId("youtube-batch-summary")).toHaveTextContent(
        "1건 수집 시작 · 1건 이미 수집됨 · 1건 실패",
      );
    });
    expect(screen.getByTestId("youtube-video-status-v1")).toHaveTextContent(
      "수집 시작됨",
    );
    // ⚠️ "이미 수집됨"이 실패로 뭉개지면 사용자는 같은 영상을 계속 다시 고른다.
    expect(screen.getByTestId("youtube-video-status-v2")).toHaveTextContent(
      "이미 수집한 영상입니다",
    );
    expect(screen.getByTestId("youtube-video-status-v3")).toHaveTextContent(
      "서버 오류로 수집하지 못했습니다",
    );
  });

  it("결과가 나온 영상은 다시 고를 수 없다", async () => {
    await renderWithVideos(["v1", "v2"]);
    select("v1");

    mockApiFetch.mockResolvedValueOnce({
      results: [{ video_id: "v1", status: "registered", raw_source_id: "s1" }],
    });
    fireEvent.click(screen.getByTestId("youtube-ingest-selected"));
    await screen.findByTestId("youtube-video-status-v1");

    // 다시 고를 수 있게 두면 "이미 수집됨"만 쌓인다.
    expect(screen.getByTestId("youtube-video-select-v1")).toBeDisabled();
    expect(screen.getByTestId("youtube-video-select-v2")).not.toBeDisabled();
  });

  it("예산 상한 결과에서 기존 크레딧 모달을 띄운다", async () => {
    await renderWithVideos(["v1", "v2"]);
    fireEvent.click(screen.getByTestId("youtube-select-all"));

    mockApiFetch.mockResolvedValueOnce({
      results: [
        { video_id: "v1", status: "failed", reason: "budget_exceeded" },
        { video_id: "v2", status: "failed", reason: "budget_exceeded" },
      ],
    });
    fireEvent.click(screen.getByTestId("youtube-ingest-selected"));

    await waitFor(() => {
      expect(
        screen.getByText("이번 달 무료 크레딧을 모두 소진했습니다"),
      ).toBeInTheDocument();
    });
    expect(screen.getByTestId("youtube-video-status-v1")).toHaveTextContent(
      "크레딧을 모두 소진해",
    );
  });

  it("요청 전체 거부를 '일부 실패'로 보이게 하지 않는다", async () => {
    await renderWithVideos(["v1", "v2"]);
    fireEvent.click(screen.getByTestId("youtube-select-all"));

    mockApiFetch.mockRejectedValueOnce(new ApiError(403, "forbidden"));
    fireEvent.click(screen.getByTestId("youtube-ingest-selected"));

    const alert = await screen.findByTestId("youtube-batch-error");
    expect(alert).toHaveTextContent("권한이 없습니다");
    // 영상별 배지도 요약도 남지 않는다 — 아무것도 등록되지 않았기 때문이다.
    expect(
      screen.queryByTestId("youtube-video-status-v1"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("youtube-batch-summary"),
    ).not.toBeInTheDocument();
  });

  it("채널을 바꾸면 이전 채널의 선택이 실려 나가지 않는다", async () => {
    await renderWithVideos(["v1"]);
    select("v1");

    mockApiFetch.mockResolvedValueOnce({
      videos: [video("other1")],
      next_page_token: null,
    });
    const { rerender } = render(
      <YoutubeVideoList
        workspaceId="ws-1"
        channel={{ ...CHANNEL, channel_id: "UC2", title: "다른채널" }}
        onBack={() => undefined}
      />,
    );
    await screen.findByTestId("youtube-video-select-other1");
    rerender(
      <YoutubeVideoList
        workspaceId="ws-1"
        channel={{ ...CHANNEL, channel_id: "UC2", title: "다른채널" }}
        onBack={() => undefined}
      />,
    );

    // ⚠️ 선택이 남으면 화면에 보이지도 않는 이전 채널 영상이 일괄 수집에 실려 나간다.
    expect(screen.getByTestId("youtube-video-select-other1")).not.toBeChecked();
  });
});
