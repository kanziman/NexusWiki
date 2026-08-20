import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const refresh = vi.fn();
const toggleWikiBookmark = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

vi.mock("@/app/bookmark-actions", () => ({
  toggleWikiBookmark: (...args: unknown[]) => toggleWikiBookmark(...args),
}));

import { FavoriteButton } from "@/components/FavoriteButton";

describe("FavoriteButton", () => {
  beforeEach(() => {
    refresh.mockReset();
    toggleWikiBookmark.mockReset();
  });

  it("초기 미즐겨찾기 상태에서 클릭하면 추가하고 라우터를 새로고침한다", async () => {
    toggleWikiBookmark.mockResolvedValue({ bookmarked: true });
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

    expect(toggleWikiBookmark).toHaveBeenCalledWith("wiki-1", "ws-1");
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "즐겨찾기 해제" }),
      ).toBeInTheDocument(),
    );
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("초기 즐겨찾기 상태에서 클릭하면 해제한다", async () => {
    toggleWikiBookmark.mockResolvedValue({ bookmarked: false });
    const user = userEvent.setup();
    render(
      <FavoriteButton
        wikiId="wiki-1"
        workspaceId="ws-1"
        initialBookmarked={true}
      />,
    );

    await user.click(screen.getByRole("button", { name: "즐겨찾기 해제" }));

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "즐겨찾기에 추가" }),
      ).toBeInTheDocument(),
    );
  });

  it("실패하면 오류를 보여주고 상태를 바꾸지 않는다", async () => {
    toggleWikiBookmark.mockResolvedValue({
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
    expect(
      screen.getByRole("button", { name: "즐겨찾기에 추가" }),
    ).toBeInTheDocument();
    expect(refresh).not.toHaveBeenCalled();
  });
});
