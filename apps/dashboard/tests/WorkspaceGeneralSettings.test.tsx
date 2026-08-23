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

  it("저장된 공개 설정을 폼에 반영한다", () => {
    // ⚠️ 이 프롭 체인이 끊겨 있으면 폼이 항상 기본값(꺼짐·빈 문자열)으로 뜬다.
    // 그 상태에서 저장하면 upsert 가 실제 값을 덮어써 표시명·설명이 null 이 되고
    // 켜져 있던 공개 공유가 조용히 꺼진다 — 화면이 보여준 적 없는 값으로.
    render(
      <WorkspaceGeneralSettings
        workspaceId="ws-1"
        initialName="내 워크스페이스"
        initialSlug="my-workspace"
        isOwner={true}
        allowPublicSharing={true}
        publicDisplayName="엔지니어링 팀"
        publicDescription="엔지니어링 지식 베이스"
      />,
    );

    expect(
      screen.getByRole("checkbox", { name: "공개 공유 마스터 킬스위치 토글" }),
    ).toBeChecked();
    expect(screen.getByDisplayValue("엔지니어링 팀")).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("엔지니어링 지식 베이스"),
    ).toBeInTheDocument();
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
      kind: "personal",
    });
  });

  it("allows owner to change workspace kind to team and saves successfully", async () => {
    const onKindChange = vi.fn();
    render(
      <WorkspaceGeneralSettings
        workspaceId="ws-1"
        initialName="내 워크스페이스"
        initialSlug="my-workspace"
        initialKind="personal"
        onKindChange={onKindChange}
        isOwner={true}
      />,
    );

    const teamRadio = screen.getByRole("radio", { name: /팀 워크스페이스/ });
    expect(teamRadio).toHaveAttribute("aria-checked", "false");

    fireEvent.click(teamRadio);
    expect(teamRadio).toHaveAttribute("aria-checked", "true");

    const saveBtn = screen.getByRole("button", { name: "저장" });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(
        screen.getByText("워크스페이스 정보가 저장되었습니다."),
      ).toBeInTheDocument();
    });
    expect(updateMock).toHaveBeenCalledWith({
      name: "내 워크스페이스",
      slug: "my-workspace",
      kind: "team",
    });
    expect(onKindChange).toHaveBeenCalledWith("team");
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
