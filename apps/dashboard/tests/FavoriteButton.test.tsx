import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const setWikiBookmark = vi.fn();

vi.mock("@/app/bookmark-actions", () => ({
  setWikiBookmark: (...args: unknown[]) => setWikiBookmark(...args),
}));

import { FavoriteButton } from "@/components/FavoriteButton";

describe("FavoriteButton", () => {
  beforeEach(() => {
    setWikiBookmark.mockReset();
  });

  it("초기 미즐겨찾기 상태에서 클릭하면 낙관적으로 추가 상태를 보여주고 서버에 true를 보낸다", async () => {
    setWikiBookmark.mockResolvedValue({ bookmarked: true });
    const user = userEvent.setup();
    render(
      <FavoriteButton
        wikiId="wiki-1"
        workspaceId="ws-1"
        initialBookmarked={false}
      />,
    );

    expect(
      screen.getByRole("button", { name: "즐겨찾기에 추가" }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "즐겨찾기에 추가" }));

    // 낙관적 업데이트라 서버 응답을 기다리지 않고 즉시 반영된다.
    expect(
      screen.getByRole("button", { name: "즐겨찾기 해제" }),
    ).toBeInTheDocument();
    expect(setWikiBookmark).toHaveBeenCalledWith("wiki-1", "ws-1", true);
  });

  it("초기 즐겨찾기 상태에서 클릭하면 false를 보내 해제한다", async () => {
    setWikiBookmark.mockResolvedValue({ bookmarked: false });
    const user = userEvent.setup();
    render(
      <FavoriteButton
        wikiId="wiki-1"
        workspaceId="ws-1"
        initialBookmarked={true}
      />,
    );

    await user.click(screen.getByRole("button", { name: "즐겨찾기 해제" }));

    expect(setWikiBookmark).toHaveBeenCalledWith("wiki-1", "ws-1", false);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "즐겨찾기에 추가" }),
      ).toBeInTheDocument(),
    );
  });

  it("실패하면 낙관적 업데이트를 되돌리고 오류를 보여준다", async () => {
    setWikiBookmark.mockResolvedValue({
      error: "즐겨찾기에 추가하지 못했습니다.",
    });
    const user = userEvent.setup();
    render(
      <FavoriteButton
        wikiId="wiki-1"
        workspaceId="ws-1"
        initialBookmarked={false}
      />,
    );

    await user.click(screen.getByRole("button", { name: "즐겨찾기에 추가" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "즐겨찾기에 추가하지 못했습니다.",
    );
    // 되돌아간 상태 — 다시 "추가" 버튼으로 표시된다.
    expect(
      screen.getByRole("button", { name: "즐겨찾기에 추가" }),
    ).toBeInTheDocument();
  });
});
