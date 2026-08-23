"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
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

function getSectionTitle(pathname: string, isBookmarked: boolean): string {
  const segments = pathname.split("/").filter(Boolean);
  const sub = segments.slice(2).join("/");

  if (!sub) return "홈 대시보드";
  if (sub.startsWith("sources")) return "원문 소스";
  if (sub.startsWith("wiki")) return isBookmarked ? "즐겨찾기" : "위키 문서";
  if (sub.startsWith("ask")) return "질문하기";
  if (sub.startsWith("backlog")) return "미완성 백로그";
  if (sub.startsWith("graph")) return "지식 그래프";
  if (sub.startsWith("settings")) return "설정";
  return "홈 대시보드";
}

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
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const isBookmarked = searchParams.get("bookmarked") === "true";
  const sectionTitle = getSectionTitle(pathname, isBookmarked);

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
          <div className="crumb flex items-center gap-1.5 text-xs text-[var(--muted)]">
            <span className="truncate max-w-[160px] text-[var(--muted)] font-normal">
              {workspace.name}
            </span>
            <span
              className="text-[var(--border-strong)] opacity-60 font-mono"
              aria-hidden="true"
            >
              /
            </span>
            <strong className="truncate font-semibold text-[var(--fg)]">
              {sectionTitle}
            </strong>
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
