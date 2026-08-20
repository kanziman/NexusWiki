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
  Settings,
  Sparkles,
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
}: WorkspaceSidebarProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const base = workspacePath(currentWorkspaceId);
  const currentCategory = searchParams.get("category");

  const initial = accountEmail ? accountEmail.charAt(0).toUpperCase() : "W";

  function handleItemClick() {
    if (onCloseMobile) {
      onCloseMobile();
    }
  }

  return (
    <aside
      className={`sidebar ${isOpenMobile ? "mobile-open" : ""}`}
      data-od-id="primary-navigation"
    >
      <div className="w-full">
        <WorkspaceSwitcher
          workspaces={workspaces}
          currentWorkspaceId={currentWorkspaceId}
        />
      </div>

      <nav className="nav-stack" aria-label="주요 메뉴">
        <Link
          href={base}
          onClick={handleItemClick}
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
          aria-current={pathname.startsWith(`${base}/ask`) ? "page" : undefined}
          className={`nav-item ${pathname.startsWith(`${base}/ask`) ? "active" : ""}`}
        >
          <HelpCircle className="nav-icon" aria-hidden="true" />
          <span>질문하기</span>
        </Link>

        <Link
          href={`${base}/wiki`}
          onClick={handleItemClick}
          aria-current={
            pathname.startsWith(`${base}/wiki`) ? "page" : undefined
          }
          className={`nav-item ${pathname.startsWith(`${base}/wiki`) ? "active" : ""}`}
        >
          <FileText className="nav-icon" aria-hidden="true" />
          <span>위키 문서</span>
        </Link>

        <Link
          href={`${base}/backlog`}
          onClick={handleItemClick}
          aria-current={
            pathname.startsWith(`${base}/backlog`) ? "page" : undefined
          }
          className={`nav-item ${pathname.startsWith(`${base}/backlog`) ? "active" : ""}`}
        >
          <CircleAlert className="nav-icon" aria-hidden="true" />
          <span>미완성 백로그</span>
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
          aria-current={
            pathname.startsWith(`${base}/settings`) ? "page" : undefined
          }
          className={`nav-item ${pathname.startsWith(`${base}/settings`) ? "active" : ""}`}
        >
          <Users className="nav-icon" aria-hidden="true" />
          <span>팀원 &amp; 역할 관리</span>
        </Link>
      </nav>

      <div className="profile" data-od-id="user-profile">
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
