"use client";

import Link from "next/link";
import { type ReactNode, useEffect, useState } from "react";
import { Menu, Plus, X } from "lucide-react";

import { AccountMenu } from "@/components/AccountMenu";
import { WorkspaceSidebar } from "@/components/WorkspaceSidebar";
import { workspacePath } from "@/lib/workspace-path";

export type WorkspaceShellProps = {
  workspace: { id: string; name: string };
  workspaces: { id: string; name: string; kind: "personal" | "team" }[];
  currentWorkspaceId: string;
  accountEmail: string;
  children: ReactNode;
};

const LNB_COLLAPSED_STORAGE_KEY = "nexuswiki-lnb-collapsed";

export function WorkspaceShell({
  workspace,
  workspaces,
  currentWorkspaceId,
  accountEmail,
  children,
}: WorkspaceShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  // 서버 렌더와 하이드레이션이 항상 "펼침"으로 일치하도록 기본값은 false로
  // 두고, sessionStorage 값은 마운트 후에만 반영한다 — 초기 렌더에서 바로
  // 읽으면 서버(sessionStorage 없음)와 클라이언트가 갈라져 하이드레이션
  // 경고가 난다.
  const [collapsed, setCollapsed] = useState(false);
  const base = workspacePath(currentWorkspaceId);

  useEffect(() => {
    if (sessionStorage.getItem(LNB_COLLAPSED_STORAGE_KEY) === "true") {
      setCollapsed(true);
    }
  }, []);

  function toggleMobile() {
    setMobileOpen((prev) => !prev);
  }

  function closeMobile() {
    setMobileOpen(false);
  }

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      sessionStorage.setItem(LNB_COLLAPSED_STORAGE_KEY, String(next));
      return next;
    });
  }

  return (
    <div
      className={`app min-h-screen${collapsed ? " sidebar-collapsed" : ""}`}
      data-od-id="nexuswiki-workspace"
    >
      <WorkspaceSidebar
        workspaces={workspaces}
        currentWorkspaceId={currentWorkspaceId}
        accountEmail={accountEmail}
        isOpenMobile={mobileOpen}
        onCloseMobile={closeMobile}
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
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
            <AccountMenu email={accountEmail} />
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
