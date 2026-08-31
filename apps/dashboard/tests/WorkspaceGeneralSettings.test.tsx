import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const pushMock = vi.hoisted(() => vi.fn());
const refreshMock = vi.hoisted(() => vi.fn());
const updateMock = vi.hoisted(() => vi.fn());
const deleteMock = vi.hoisted(() => vi.fn());
const state = vi.hoisted(() => ({
  memberCount: 1,
  remainingWorkspaces: [] as { workspace_id: string }[],
  deleteData: [{ id: "ws-1" }] as unknown[] | null,
  deleteError: null as { message: string } | null,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: refreshMock, push: pushMock }),
}));

vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(() => ({
    from: (table: string) => {
      if (table === "workspace_members") {
        return {
          select: () => ({
            eq: () =>
              Promise.resolve({ count: state.memberCount, error: null }),
            neq: () => ({
              limit: () =>
                Promise.resolve({
                  data: state.remainingWorkspaces,
                  error: null,
                }),
            }),
          }),
        };
      }
      return {
        update: updateMock.mockReturnValue({
          eq: () => ({
            select: async () => ({
              data: [{ id: "ws-1", name: "새 이름", slug: "new-slug" }],
              error: null,
            }),
          }),
        }),
        delete: deleteMock.mockReturnValue({
          eq: () => ({
            select: async () => ({
              data: state.deleteData,
              error: state.deleteError,
            }),
          }),
        }),
      };
    },
  })),
}));

import { WorkspaceGeneralSettings } from "@/components/WorkspaceGeneralSettings";

describe("WorkspaceGeneralSettings", () => {
  beforeEach(() => {
    updateMock.mockClear();
    deleteMock.mockClear();
    pushMock.mockClear();
    refreshMock.mockClear();
    state.memberCount = 1;
    state.remainingWorkspaces = [];
    state.deleteData = [{ id: "ws-1" }];
    state.deleteError = null;
  });

  it("저장된 공개 설정을 폼에 반영한다", () => {
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
    expect(
      screen.getByRole("button", { name: "워크스페이스 삭제" }),
    ).toBeDisabled();
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

  it("팀에서 개인으로 전환할 때 다른 멤버가 있으면 에러 메시지를 표시하고 저장을 차단한다", async () => {
    state.memberCount = 3; // 소유자 외 2명 참여 중
    render(
      <WorkspaceGeneralSettings
        workspaceId="ws-1"
        initialName="우리 팀 워크스페이스"
        initialSlug="team-workspace"
        initialKind="team"
        isOwner={true}
      />,
    );

    const personalRadio = screen.getByRole("radio", {
      name: /개인 워크스페이스/,
    });
    fireEvent.click(personalRadio);

    const saveBtn = screen.getByRole("button", { name: "저장" });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/다른 멤버\(2명\)가 참여 중인 워크스페이스는/),
      ).toBeInTheDocument();
    });
    expect(updateMock).not.toHaveBeenCalled();
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

  describe("위험 구역 (워크스페이스 삭제)", () => {
    it("소유자는 삭제 모달을 열고 워크스페이스 이름이 일치해야만 영구 삭제가 가능하다", async () => {
      state.remainingWorkspaces = [{ workspace_id: "ws-2" }];

      render(
        <WorkspaceGeneralSettings
          workspaceId="ws-1"
          initialName="삭제할 워크스페이스"
          initialSlug="delete-me"
          isOwner={true}
        />,
      );

      const deleteTriggerBtn = screen.getByRole("button", {
        name: "워크스페이스 삭제",
      });
      expect(deleteTriggerBtn).not.toBeDisabled();

      fireEvent.click(deleteTriggerBtn);

      // 모달 표시 확인
      expect(screen.getByText("워크스페이스 삭제 확인")).toBeInTheDocument();

      const confirmInput = screen.getByPlaceholderText("삭제할 워크스페이스");
      const confirmDeleteBtn = screen.getByRole("button", {
        name: "영구 삭제",
      });

      // 이름 불일치 시 삭제 버튼 비활성화
      expect(confirmDeleteBtn).toBeDisabled();

      fireEvent.change(confirmInput, { target: { value: "틀린 이름" } });
      expect(confirmDeleteBtn).toBeDisabled();

      // 이름 일치 시 삭제 버튼 활성화 및 실행
      fireEvent.change(confirmInput, {
        target: { value: "삭제할 워크스페이스" },
      });
      expect(confirmDeleteBtn).toBeEnabled();

      fireEvent.click(confirmDeleteBtn);

      await waitFor(() => {
        expect(deleteMock).toHaveBeenCalled();
        expect(pushMock).toHaveBeenCalledWith("/w/ws-2");
      });
    });

    it("남은 다른 워크스페이스가 없으면 삭제 후 온보딩(/onboarding)으로 리다이렉트한다", async () => {
      state.remainingWorkspaces = []; // 마지막 워크스페이스

      render(
        <WorkspaceGeneralSettings
          workspaceId="ws-1"
          initialName="마지막 워크스페이스"
          initialSlug="last-ws"
          isOwner={true}
        />,
      );

      fireEvent.click(
        screen.getByRole("button", { name: "워크스페이스 삭제" }),
      );

      const confirmInput = screen.getByPlaceholderText("마지막 워크스페이스");
      fireEvent.change(confirmInput, {
        target: { value: "마지막 워크스페이스" },
      });

      fireEvent.click(screen.getByRole("button", { name: "영구 삭제" }));

      await waitFor(() => {
        expect(deleteMock).toHaveBeenCalled();
        expect(pushMock).toHaveBeenCalledWith("/onboarding");
      });
    });

    it("삭제 실패 시 모달에 인라인 에러 메시지를 표시한다", async () => {
      state.deleteData = [];
      state.deleteError = { message: "삭제 권한이 없습니다." };

      render(
        <WorkspaceGeneralSettings
          workspaceId="ws-1"
          initialName="삭제 실패 테스트"
          initialSlug="fail-ws"
          isOwner={true}
        />,
      );

      fireEvent.click(
        screen.getByRole("button", { name: "워크스페이스 삭제" }),
      );

      const confirmInput = screen.getByPlaceholderText("삭제 실패 테스트");
      fireEvent.change(confirmInput, {
        target: { value: "삭제 실패 테스트" },
      });

      fireEvent.click(screen.getByRole("button", { name: "영구 삭제" }));

      await waitFor(() => {
        expect(screen.getByText("삭제 권한이 없습니다.")).toBeInTheDocument();
      });
      expect(pushMock).not.toHaveBeenCalled();
    });
  });

  describe("BYOK (커스텀 API 키) 설정", () => {
    it("API 키가 없을 때 등록 폼과 외부 발급 링크를 렌더링한다", () => {
      render(
        <WorkspaceGeneralSettings
          workspaceId="ws-1"
          initialName="내 워크스페이스"
          initialSlug="my-ws"
          isOwner={true}
        />,
      );

      expect(
        screen.getByLabelText("AI 모델 및 API 키 설정"),
      ).toBeInTheDocument();
      expect(
        screen.getByLabelText("OpenRouter API 키 등록"),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: /OpenRouter 키 발급받기/ }),
      ).toHaveAttribute("href", "https://openrouter.ai/keys");
    });

    it("등록된 API 키가 있을 때 마스킹된 키와 무제한 활성화 뱃지를 표시한다", () => {
      render(
        <WorkspaceGeneralSettings
          workspaceId="ws-1"
          initialName="내 워크스페이스"
          initialSlug="my-ws"
          initialCustomApiKey="sk-or-v1-abcdef1234567890abcdef1234"
          isOwner={true}
        />,
      );

      expect(screen.getByText("무제한 활성화됨")).toBeInTheDocument();
      expect(screen.getByText("sk-or-v1••••••••1234")).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "API 키 변경" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "API 키 삭제" }),
      ).toBeInTheDocument();
    });

    it("소유자가 새 API 키를 입력하고 저장할 수 있다", async () => {
      render(
        <WorkspaceGeneralSettings
          workspaceId="ws-1"
          initialName="내 워크스페이스"
          initialSlug="my-ws"
          isOwner={true}
        />,
      );

      const keyInput = screen.getByLabelText("OpenRouter API 키 등록");
      fireEvent.change(keyInput, {
        target: { value: "sk-or-v1-new-secret-key-1234567890" },
      });

      fireEvent.click(screen.getByRole("button", { name: "API 키 저장" }));

      await waitFor(() => {
        expect(updateMock).toHaveBeenCalled();
        expect(
          screen.getByText(
            "내 API 키가 등록되었습니다! 이제 크레딧 차감 없이 무제한으로 이용할 수 있습니다.",
          ),
        ).toBeInTheDocument();
      });
    });

    it("소유자가 등록된 API 키를 삭제할 수 있다", async () => {
      render(
        <WorkspaceGeneralSettings
          workspaceId="ws-1"
          initialName="내 워크스페이스"
          initialSlug="my-ws"
          initialCustomApiKey="sk-or-v1-abcdef1234567890abcdef1234"
          isOwner={true}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: "API 키 삭제" }));

      await waitFor(() => {
        expect(updateMock).toHaveBeenCalled();
        expect(
          screen.getByText(
            "API 키가 삭제되었습니다. 기본 무료 크레딧 쿼터로 전환되었습니다.",
          ),
        ).toBeInTheDocument();
      });
    });
  });
});
