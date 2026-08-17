import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PublicSharingSettings } from "@/components/PublicSharingSettings";

const mockUpsert = vi.fn();
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    from: () => ({
      upsert: (...args: unknown[]) => mockUpsert(...args),
    }),
  }),
}));

describe("PublicSharingSettings", () => {
  it("renders public sharing killswitch toggle and public url preview", () => {
    render(
      <PublicSharingSettings
        workspaceId="ws-1"
        workspaceSlug="engineering"
        isOwner={true}
        initialAllowPublicSharing={false}
      />,
    );

    expect(screen.getByText("공개 공유 (Public Sharing)")).toBeInTheDocument();
    expect(screen.getByText("공개 공유 마스터 킬스위치")).toBeInTheDocument();
    expect(
      screen.getByText(
        "공개 공유가 꺼져 있습니다. 모든 외부 공개 URL(/p/...)이 즉시 404로 차단됩니다.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("/p/engineering/[페이지_슬러그]"),
    ).toBeInTheDocument();
  });

  it("allows owner to toggle killswitch and submit successfully", async () => {
    mockUpsert.mockResolvedValueOnce({ error: null });

    render(
      <PublicSharingSettings
        workspaceId="ws-1"
        workspaceSlug="engineering"
        isOwner={true}
        initialAllowPublicSharing={false}
      />,
    );

    const toggle = screen.getByRole("checkbox", {
      name: "공개 공유 마스터 킬스위치 토글",
    });
    fireEvent.click(toggle);

    expect(
      screen.getByText(
        "공개 공유가 활성화되어 있습니다. 승인된 위키 문서가 외부 URL로 공개됩니다.",
      ),
    ).toBeInTheDocument();

    const saveButton = screen.getByRole("button", { name: "공개 설정 저장" });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockUpsert).toHaveBeenCalledWith(
        expect.objectContaining({
          workspace_id: "ws-1",
          workspace_slug: "engineering",
          allow_public_sharing: true,
        }),
      );
      expect(
        screen.getByText("공개 설정이 성공적으로 저장되었습니다."),
      ).toBeInTheDocument();
    });
  });

  it("disables inputs and hides save button for non-owner", () => {
    render(
      <PublicSharingSettings
        workspaceId="ws-1"
        workspaceSlug="engineering"
        isOwner={false}
        initialAllowPublicSharing={false}
      />,
    );

    const toggle = screen.getByRole("checkbox", {
      name: "공개 공유 마스터 킬스위치 토글",
    });
    expect(toggle).toBeDisabled();

    const nameInput = screen.getByRole("textbox", {
      name: "공개 워크스페이스 표시명 (선택)",
    });
    expect(nameInput).toBeDisabled();

    expect(
      screen.queryByRole("button", { name: "공개 설정 저장" }),
    ).not.toBeInTheDocument();
  });
});
