"use client";

import { useState, type KeyboardEvent } from "react";

import { InviteForm } from "@/components/InviteForm";
import { MembersList } from "@/components/MembersList";
import { OperationsPanel } from "@/components/OperationsPanel";
import { WorkspaceGeneralSettings } from "@/components/WorkspaceGeneralSettings";

export type SettingsMembersPanelProps = {
  workspaceId: string;
  currentUserId: string;
  currentRole: string;
  workspaceName?: string;
  workspaceSlug?: string;
};

export function SettingsMembersPanel({
  workspaceId,
  currentUserId,
  currentRole,
  workspaceName = "",
  workspaceSlug = "",
}: SettingsMembersPanelProps) {
  const [refreshToken, setRefreshToken] = useState(0);
  const isOwner = currentRole === "owner";
  const canViewOperations = currentRole === "owner" || currentRole === "editor";
  const [activeTab, setActiveTab] = useState<
    "general" | "members" | "operations"
  >("general");

  const availableTabs: ("general" | "members" | "operations")[] = [
    "general",
    "members",
    ...(canViewOperations ? (["operations"] as const) : []),
  ];

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      return;
    }
    event.preventDefault();
    const currentIndex = availableTabs.indexOf(activeTab);
    let nextIndex = currentIndex;

    if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = availableTabs.length - 1;
    else if (event.key === "ArrowLeft") {
      nextIndex =
        currentIndex > 0 ? currentIndex - 1 : availableTabs.length - 1;
    } else if (event.key === "ArrowRight") {
      nextIndex =
        currentIndex < availableTabs.length - 1 ? currentIndex + 1 : 0;
    }

    const nextTab = availableTabs[nextIndex];
    setActiveTab(nextTab);
    document.getElementById(`settings-tab-${nextTab}`)?.focus();
  }

  return (
    <div className="flex flex-col gap-xl" style={{ maxWidth: "640px" }}>
      <div
        role="tablist"
        aria-label="설정"
        className="flex gap-xs border-b border-[var(--border)] bg-[var(--surface)] p-1 rounded-lg"
      >
        <button
          id="settings-tab-general"
          type="button"
          role="tab"
          aria-selected={activeTab === "general"}
          aria-controls="settings-panel-general"
          tabIndex={activeTab === "general" ? 0 : -1}
          onClick={() => setActiveTab("general")}
          onKeyDown={handleTabKeyDown}
          className={`min-h-9 cursor-pointer rounded-md px-3 text-xs font-semibold outline-none transition-colors ${
            activeTab === "general"
              ? "bg-[var(--bg)] text-[var(--accent)] shadow-sm"
              : "text-[var(--muted)] hover:text-[var(--fg)]"
          }`}
        >
          일반
        </button>

        <button
          id="settings-tab-members"
          type="button"
          role="tab"
          aria-selected={activeTab === "members"}
          aria-controls="settings-panel-members"
          tabIndex={activeTab === "members" ? 0 : -1}
          onClick={() => setActiveTab("members")}
          onKeyDown={handleTabKeyDown}
          className={`min-h-9 cursor-pointer rounded-md px-3 text-xs font-semibold outline-none transition-colors ${
            activeTab === "members"
              ? "bg-[var(--bg)] text-[var(--accent)] shadow-sm"
              : "text-[var(--muted)] hover:text-[var(--fg)]"
          }`}
        >
          멤버
        </button>

        {canViewOperations ? (
          <button
            id="settings-tab-operations"
            type="button"
            role="tab"
            aria-selected={activeTab === "operations"}
            aria-controls="settings-panel-operations"
            tabIndex={activeTab === "operations" ? 0 : -1}
            onClick={() => setActiveTab("operations")}
            onKeyDown={handleTabKeyDown}
            className={`min-h-9 cursor-pointer rounded-md px-3 text-xs font-semibold outline-none transition-colors ${
              activeTab === "operations"
                ? "bg-[var(--bg)] text-[var(--accent)] shadow-sm"
                : "text-[var(--muted)] hover:text-[var(--fg)]"
            }`}
          >
            운영 현황
          </button>
        ) : null}
      </div>

      {activeTab === "general" ? (
        <div
          id="settings-panel-general"
          role="tabpanel"
          aria-labelledby="settings-tab-general"
        >
          <WorkspaceGeneralSettings
            workspaceId={workspaceId}
            initialName={workspaceName}
            initialSlug={workspaceSlug}
            isOwner={isOwner}
          />
        </div>
      ) : activeTab === "members" ? (
        <div
          id="settings-panel-members"
          role="tabpanel"
          aria-labelledby="settings-tab-members"
          className="flex flex-col gap-xl"
        >
          <section className="flex flex-col gap-base">
            <h2 className="text-ink" style={{ font: "var(--font-title-md)" }}>
              멤버
            </h2>
            <MembersList
              key={refreshToken}
              workspaceId={workspaceId}
              currentUserId={currentUserId}
            />
          </section>

          {/* SETTINGS-03: 초대 폼은 owner에게만 노출 (버그 수정) */}
          {isOwner && (
            <section className="flex flex-col gap-base">
              <h2 className="text-ink" style={{ font: "var(--font-title-md)" }}>
                멤버 초대
              </h2>
              <InviteForm
                workspaceId={workspaceId}
                onInvited={() => setRefreshToken((token) => token + 1)}
              />
            </section>
          )}
        </div>
      ) : canViewOperations ? (
        <div
          id="settings-panel-operations"
          role="tabpanel"
          aria-labelledby="settings-tab-operations"
        >
          <OperationsPanel workspaceId={workspaceId} />
        </div>
      ) : null}
    </div>
  );
}
