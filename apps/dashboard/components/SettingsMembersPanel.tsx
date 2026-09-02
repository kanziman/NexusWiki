"use client";

import { useEffect, useState, type KeyboardEvent } from "react";

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
  workspaceKind?: "personal" | "team";
  initialCustomApiKey?: string | null;
  allowPublicSharing?: boolean;
  publicDisplayName?: string;
  publicDescription?: string;
};

type TabId = "general" | "members" | "operations";

// 라벨에 이모지를 붙이지 않는다 — 불변식 §7.2 Zero Emojis
// (workspace-settings-prd.md §3.1, 프로토타입 정정 12번).
const TAB_LABELS: Record<TabId, string> = {
  general: "일반",
  members: "멤버",
  operations: "운영 현황",
};

export function SettingsMembersPanel({
  workspaceId,
  currentUserId,
  currentRole,
  workspaceName = "",
  workspaceSlug = "",
  workspaceKind = "personal",
  initialCustomApiKey = null,
  allowPublicSharing = false,
  publicDisplayName = "",
  publicDescription = "",
}: SettingsMembersPanelProps) {
  const [refreshToken, setRefreshToken] = useState(0);
  const [currentKind, setCurrentKind] = useState<"personal" | "team">(
    workspaceKind,
  );
  const isOwner = currentRole === "owner";
  const canViewOperations = currentRole === "owner" || currentRole === "editor";
  const [activeTab, setActiveTab] = useState<TabId>("general");

  useEffect(() => {
    setCurrentKind(workspaceKind);
  }, [workspaceKind]);

  const availableTabs: TabId[] = [
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
    <>
      <nav className="tabs" role="tablist" aria-label="설정">
        {availableTabs.map((tab) => (
          <button
            key={tab}
            id={`settings-tab-${tab}`}
            type="button"
            role="tab"
            aria-selected={activeTab === tab}
            aria-controls={`settings-panel-${tab}`}
            tabIndex={activeTab === tab ? 0 : -1}
            onClick={() => setActiveTab(tab)}
            onKeyDown={handleTabKeyDown}
            className={`tab ${activeTab === tab ? "active" : ""}`}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </nav>

      {activeTab === "general" ? (
        <section
          id="settings-panel-general"
          role="tabpanel"
          aria-labelledby="settings-tab-general"
          className="panel active"
        >
          <WorkspaceGeneralSettings
            workspaceId={workspaceId}
            initialName={workspaceName}
            initialSlug={workspaceSlug}
            initialKind={currentKind}
            initialCustomApiKey={initialCustomApiKey}
            onKindChange={setCurrentKind}
            isOwner={isOwner}
            allowPublicSharing={allowPublicSharing}
            publicDisplayName={publicDisplayName}
            publicDescription={publicDescription}
          />
        </section>
      ) : activeTab === "members" ? (
        <section
          id="settings-panel-members"
          role="tabpanel"
          aria-labelledby="settings-tab-members"
          className="panel active"
        >
          <div className="section-head">
            <div>
              <h2>멤버 관리</h2>
              <p>워크스페이스에 접근할 수 있는 사용자와 역할입니다.</p>
            </div>
          </div>

          <MembersList
            key={refreshToken}
            workspaceId={workspaceId}
            currentUserId={currentUserId}
          />

          {/* SETTINGS-03: 초대 폼은 owner에게만 노출 (버그 수정) */}
          {isOwner && (
            <InviteForm
              workspaceId={workspaceId}
              isPersonal={currentKind === "personal"}
              onInvited={() => setRefreshToken((token) => token + 1)}
            />
          )}
        </section>
      ) : canViewOperations ? (
        <section
          id="settings-panel-operations"
          role="tabpanel"
          aria-labelledby="settings-tab-operations"
          className="panel active"
        >
          <OperationsPanel workspaceId={workspaceId} />
        </section>
      ) : null}
    </>
  );
}
