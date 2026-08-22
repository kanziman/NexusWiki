"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  BookOpen,
  CircleAlert,
  Compass,
  FileText,
  HelpCircle,
  Layers,
  Map,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Sparkles,
  Star,
  Upload,
  Users,
} from "lucide-react";

import { WorkspaceSwitcher } from "@/components/WorkspaceSwitcher";
import { workspacePath } from "@/lib/workspace-path";

export type WorkspaceSidebarProps = {
  workspaces: { id: string; name: string; kind: "personal" | "team" }[];
  currentWorkspaceId: string;
  accountEmail: string;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
};

const CATEGORIES = [
  { slug: "concepts", label: "개념", icon: Sparkles },
  { slug: "entities", label: "엔티티", icon: Layers },
  { slug: "guides", label: "가이드", icon: BookOpen },
  { slug: "maps", label: "맵", icon: Map },
] as const;

export function WorkspaceSidebar({
  workspaces,
  currentWorkspaceId,
  accountEmail,
  isOpenMobile = false,
  onCloseMobile,
  collapsed = false,
  onToggleCollapsed,
}: WorkspaceSidebarProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const base = workspacePath(currentWorkspaceId);
  const currentCategory = searchParams.get("category");
  const isBookmarkedFilterActive =
    pathname.startsWith(`${base}/wiki`) &&
    searchParams.get("bookmarked") === "true";

  const initial = accountEmail ? accountEmail.charAt(0).toUpperCase() : "W";

  function handleItemClick() {
    if (onCloseMobile) {
      onCloseMobile();
    }
  }

  return (
    <aside
      // collapsed와 mobile-open을 동시에 걸지 않는다 — 모바일 서랍은 폭이
      // 이미 고정(position:fixed)이라 collapsed의 아이콘 레일 조판이 필요
      // 없고, 같이 걸면 서랍 안에서 라벨 없는 아이콘만 보이는 혼란을 만든다.
      className={`sidebar ${isOpenMobile ? "mobile-open" : ""}${collapsed && !isOpenMobile ? " collapsed" : ""}`}
      data-od-id="primary-navigation"
    >
      <div className="w-full">
        <WorkspaceSwitcher
          workspaces={workspaces}
          currentWorkspaceId={currentWorkspaceId}
        />
      </div>

      {onToggleCollapsed && !isOpenMobile ? (
        <button
          type="button"
          onClick={onToggleCollapsed}
          className="icon-btn"
          data-od-id="lnb-collapse-toggle"
          aria-label={collapsed ? "메뉴 펼치기" : "메뉴 접기"}
        >
          {collapsed ? (
            <PanelLeftOpen className="nav-icon" aria-hidden="true" />
          ) : (
            <PanelLeftClose className="nav-icon" aria-hidden="true" />
          )}
        </button>
      ) : null}

      <nav className="nav-stack" aria-label="주요 메뉴">
        <Link
          href={base}
          onClick={handleItemClick}
          aria-label="홈 대시보드"
          aria-current={
            pathname === base && !currentCategory ? "page" : undefined
          }
          className={`nav-item ${pathname === base && !currentCategory ? "active" : ""}`}
        >
          <Compass className="nav-icon" aria-hidden="true" />
          <span>홈 대시보드</span>
        </Link>

        <Link
          href={`${base}/sources`}
          onClick={handleItemClick}
          aria-label="원문 소스"
          aria-current={
            pathname.startsWith(`${base}/sources`) ? "page" : undefined
          }
          className={`nav-item ${pathname.startsWith(`${base}/sources`) ? "active" : ""}`}
        >
          <Upload className="nav-icon" aria-hidden="true" />
          <span>원문 소스</span>
        </Link>

        <Link
          href={`${base}/ask`}
          onClick={handleItemClick}
          aria-label="질문하기"
          aria-current={pathname.startsWith(`${base}/ask`) ? "page" : undefined}
          className={`nav-item ${pathname.startsWith(`${base}/ask`) ? "active" : ""}`}
        >
          <HelpCircle className="nav-icon" aria-hidden="true" />
          <span>질문하기</span>
        </Link>

        <Link
          href={`${base}/wiki`}
          onClick={handleItemClick}
          aria-label="위키 문서"
          aria-current={
            pathname.startsWith(`${base}/wiki`) && !isBookmarkedFilterActive
              ? "page"
              : undefined
          }
          className={`nav-item ${pathname.startsWith(`${base}/wiki`) && !isBookmarkedFilterActive ? "active" : ""}`}
        >
          <FileText className="nav-icon" aria-hidden="true" />
          <span>위키 문서</span>
        </Link>

        <Link
          href={`${base}/backlog`}
          onClick={handleItemClick}
          aria-label="미완성 백로그"
          aria-current={
            pathname.startsWith(`${base}/backlog`) ? "page" : undefined
          }
          className={`nav-item ${pathname.startsWith(`${base}/backlog`) ? "active" : ""}`}
        >
          <CircleAlert className="nav-icon" aria-hidden="true" />
          <span>미완성 백로그</span>
        </Link>

        <Link
          href={`${base}/wiki?bookmarked=true`}
          onClick={handleItemClick}
          aria-label="즐겨찾기"
          aria-current={isBookmarkedFilterActive ? "page" : undefined}
          className={`nav-item ${isBookmarkedFilterActive ? "active" : ""}`}
        >
          <Star className="nav-icon" aria-hidden="true" />
          <span>즐겨찾기</span>
        </Link>

        <div className="nav-label" aria-hidden="true">
          <span>카테고리</span>
        </div>

        {CATEGORIES.map(({ slug, label, icon: Icon }) => {
          const isCategoryActive =
            pathname === base && currentCategory === slug;
          const href = `${base}?category=${slug}`;

          return (
            <Link
              key={slug}
              href={href}
              onClick={handleItemClick}
              data-category={slug}
              aria-label={label}
              aria-current={isCategoryActive ? "page" : undefined}
              className={`nav-item ${isCategoryActive ? "active" : ""}`}
            >
              <Icon className="nav-icon" aria-hidden="true" />
              <span>{label}</span>
            </Link>
          );
        })}

        <div className="nav-label" aria-hidden="true">
          <span>팀 관리</span>
        </div>

        <Link
          href={`${base}/settings`}
          onClick={handleItemClick}
          aria-label="팀원 & 역할 관리"
          aria-current={
            pathname.startsWith(`${base}/settings`) ? "page" : undefined
          }
          className={`nav-item ${pathname.startsWith(`${base}/settings`) ? "active" : ""}`}
        >
          <Users className="nav-icon" aria-hidden="true" />
          <span>팀원 &amp; 역할 관리</span>
        </Link>
      </nav>

      <div
        className="profile"
        data-od-id="user-profile"
        aria-label={accountEmail}
      >
        <div className="avatar">{initial}</div>
        <div className="profile-text">
          <strong className="truncate">{accountEmail.split("@")[0]}</strong>
          <span className="truncate">{accountEmail}</span>
        </div>
        <Link
          href={`${base}/settings`}
          onClick={handleItemClick}
          className="icon-btn"
          aria-label="설정"
        >
          <Settings className="nav-icon" aria-hidden="true" />
        </Link>
      </div>
    </aside>
  );
}
