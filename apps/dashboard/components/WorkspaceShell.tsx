"use client";

import Link from "next/link";
import { type ReactNode, useState } from "react";
import { Menu, Plus, X } from "lucide-react";

import { WorkspaceSidebar } from "@/components/WorkspaceSidebar";
import { workspacePath } from "@/lib/workspace-path";

export type WorkspaceShellProps = {
  workspace: { id: string; name: string };
  workspaces: { id: string; name: string }[];
  currentWorkspaceId: string;
  accountEmail: string;
  children: ReactNode;
};

export function WorkspaceShell({
  workspace,
  workspaces,
  currentWorkspaceId,
  accountEmail,
  children,
}: WorkspaceShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const base = workspacePath(currentWorkspaceId);

  function toggleMobile() {
    setMobileOpen((prev) => !prev);
  }

  function closeMobile() {
    setMobileOpen(false);
  }

  return (
    <div className="app min-h-screen" data-od-id="nexuswiki-workspace">
      <WorkspaceSidebar
        workspaces={workspaces}
        currentWorkspaceId={currentWorkspaceId}
        accountEmail={accountEmail}
        isOpenMobile={mobileOpen}
        onCloseMobile={closeMobile}
      />

      <div
        className={`mobile-scrim ${mobileOpen ? "show" : ""}`}
        onClick={closeMobile}
        aria-hidden="true"
      />

      <div className="workspace flex flex-col min-w-0 flex-1">
        <header className="topbar" data-od-id="workspace-topbar">
          <div className="crumb">
            <strong className="truncate">{workspace.name}</strong>
          </div>
          <div className="top-actions">
            <Link
              href={`${base}/sources`}
              className="button"
              data-od-id="add-source-button"
            >
              <Plus size={14} aria-hidden="true" />
              <span>소스 추가</span>
            </Link>
            <Link
              href={`${base}/ask`}
              className="button primary"
              data-od-id="ask-top-button"
            >
              <span>질문 시작</span>
            </Link>
            <button
              type="button"
              onClick={toggleMobile}
              className="mobile-nav-button"
              data-od-id="mobile-menu-button"
              aria-label={mobileOpen ? "메뉴 닫기" : "메뉴 열기"}
            >
              {mobileOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </header>

        <main className="workspace-main flex-1 min-w-0">{children}</main>
      </div>
    </div>
  );
}
