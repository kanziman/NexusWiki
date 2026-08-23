import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/MembersList", () => ({
  MembersList: () => <div data-testid="members-list">Members List</div>,
}));

vi.mock("@/components/InviteForm", () => ({
  InviteForm: ({ isPersonal }: { isPersonal?: boolean }) => (
    <div
      data-testid="invite-form"
      data-is-personal={String(Boolean(isPersonal))}
    >
      Invite Form
    </div>
  ),
}));

vi.mock("@/components/OperationsPanel", () => ({
  OperationsPanel: () => (
    <div data-testid="operations-panel">Operations Panel</div>
  ),
}));

vi.mock("@/components/WorkspaceGeneralSettings", () => ({
  WorkspaceGeneralSettings: () => (
    <div data-testid="general-settings">General Settings</div>
  ),
}));

import { SettingsMembersPanel } from "@/components/SettingsMembersPanel";

describe("SettingsMembersPanel", () => {
  it("renders general tab by default and switches between tabs", () => {
    render(
      <SettingsMembersPanel
        workspaceId="ws-1"
        currentUserId="user-1"
        currentRole="owner"
        workspaceName="내 워크스페이스"
        workspaceSlug="my-workspace"
      />,
    );

    expect(screen.getByRole("tab", { name: "일반" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByTestId("general-settings")).toBeInTheDocument();

    const membersTab = screen.getByRole("tab", { name: "멤버" });
    fireEvent.click(membersTab);

    expect(membersTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("members-list")).toBeInTheDocument();
  });

  it("renders invite form only for owners in members tab", () => {
    const { rerender } = render(
      <SettingsMembersPanel
        workspaceId="ws-1"
        currentUserId="user-1"
        currentRole="viewer"
      />,
    );

    const membersTab = screen.getByRole("tab", { name: "멤버" });
    fireEvent.click(membersTab);

    expect(screen.getByTestId("members-list")).toBeInTheDocument();
    expect(screen.queryByTestId("invite-form")).not.toBeInTheDocument();

    rerender(
      <SettingsMembersPanel
        workspaceId="ws-1"
        currentUserId="user-1"
        currentRole="owner"
      />,
    );

    expect(screen.getByTestId("members-list")).toBeInTheDocument();
    expect(screen.getByTestId("invite-form")).toBeInTheDocument();
  });

  it("passes isPersonal to InviteForm based on workspaceKind", () => {
    const { rerender } = render(
      <SettingsMembersPanel
        workspaceId="ws-1"
        currentUserId="user-1"
        currentRole="owner"
        workspaceKind="personal"
      />,
    );

    const membersTab = screen.getByRole("tab", { name: "멤버" });
    fireEvent.click(membersTab);

    expect(screen.getByTestId("invite-form")).toHaveAttribute(
      "data-is-personal",
      "true",
    );

    rerender(
      <SettingsMembersPanel
        workspaceId="ws-1"
        currentUserId="user-1"
        currentRole="owner"
        workspaceKind="team"
      />,
    );

    expect(screen.getByTestId("invite-form")).toHaveAttribute(
      "data-is-personal",
      "false",
    );
  });
});
