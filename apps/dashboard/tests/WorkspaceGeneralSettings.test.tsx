import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const updateMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(() => ({
    from: () => ({
      update: updateMock.mockReturnValue({
        eq: () => ({
          select: async () => ({
            data: [{ id: "ws-1", name: "새 이름", slug: "new-slug" }],
            error: null,
          }),
        }),
      }),
    }),
  })),
}));

import { WorkspaceGeneralSettings } from "@/components/WorkspaceGeneralSettings";

describe("WorkspaceGeneralSettings", () => {
  beforeEach(() => {
    updateMock.mockClear();
  });

  it("renders disabled inputs and role note for non-owners", () => {
    render(
      <WorkspaceGeneralSettings
        workspaceId="ws-1"
        initialName="내 워크스페이스"
        initialSlug="my-workspace"
        isOwner={false}
      />,
    );

    const nameInput = screen.getByLabelText("워크스페이스 이름");
    const slugInput = screen.getByLabelText("워크스페이스 슬러그");

    expect(nameInput).toBeDisabled();
    expect(slugInput).toBeDisabled();
    expect(
      screen.getByText(
        "소유자(Owner)만 워크스페이스 설정을 변경할 수 있습니다.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "저장" }),
    ).not.toBeInTheDocument();
  });

  it("allows owner to edit name and slug and saves successfully", async () => {
    render(
      <WorkspaceGeneralSettings
        workspaceId="ws-1"
        initialName="내 워크스페이스"
        initialSlug="my-workspace"
        isOwner={true}
      />,
    );

    const nameInput = screen.getByLabelText("워크스페이스 이름");
    const slugInput = screen.getByLabelText("워크스페이스 슬러그");
    const saveBtn = screen.getByRole("button", { name: "저장" });

    expect(nameInput).not.toBeDisabled();
    expect(slugInput).not.toBeDisabled();

    fireEvent.change(nameInput, { target: { value: "새 이름" } });
    fireEvent.change(slugInput, { target: { value: "new-slug" } });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(
        screen.getByText("워크스페이스 정보가 저장되었습니다."),
      ).toBeInTheDocument();
    });
    expect(updateMock).toHaveBeenCalledWith({
      name: "새 이름",
      slug: "new-slug",
    });
  });

  it("shows error message when slug format is invalid", async () => {
    render(
      <WorkspaceGeneralSettings
        workspaceId="ws-1"
        initialName="내 워크스페이스"
        initialSlug="my-workspace"
        isOwner={true}
      />,
    );

    const slugInput = screen.getByLabelText("워크스페이스 슬러그");
    const saveBtn = screen.getByRole("button", { name: "저장" });

    fireEvent.change(slugInput, { target: { value: "INVALID SLUG!" } });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(
        screen.getByText(
          "슬러그는 1자 이상 80자 이하의 영문 소문자, 숫자, 한글, 하이픈(-)만 사용할 수 있습니다.",
        ),
      ).toBeInTheDocument();
    });
    expect(updateMock).not.toHaveBeenCalled();
  });
});
