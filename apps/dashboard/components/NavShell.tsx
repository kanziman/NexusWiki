"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { WorkspaceSwitcher } from "@/components/WorkspaceSwitcher";
import { workspacePath } from "@/lib/workspace-path";

export type NavShellProps = {
  workspaces: { id: string; name: string }[];
  currentWorkspaceId: string;
};

const ROUTES: { segment: string; label: string }[] = [
  { segment: "/sources", label: "소스" },
  { segment: "/ask", label: "질문하기" },
  { segment: "/wiki", label: "위키" },
  { segment: "/graph", label: "그래프" },
  { segment: "/settings", label: "설정" },
];

// UI-01: 06-01 트레이서가 남긴 bare header를 대체한다 — 워크스페이스 전환
// 드롭다운(D-03, WorkspaceSwitcher 재사용) + Phase 6 나머지 표면(소스/질문하기/
// 위키/그래프/설정)으로의 실제 내비게이션. 활성 라우트는 usePathname()으로
// 판정한다 — currentWorkspaceId prop과 마찬가지로 URL이 유일한 진실 소스다.
export function NavShell({ workspaces, currentWorkspaceId }: NavShellProps) {
  const pathname = usePathname();
  const base = workspacePath(currentWorkspaceId);

  return (
    <header className="border-b border-[var(--nw-rule)] bg-[var(--nw-canvas)]">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-x-xl gap-y-sm px-base py-base sm:px-xl">
        <Link
          href={base}
          className="nw-focus-ring shrink-0 text-[15px] font-semibold tracking-[-0.04em] text-[var(--nw-ink)]"
        >
          Nexus
        </Link>
        <WorkspaceSwitcher
          workspaces={workspaces}
          currentWorkspaceId={currentWorkspaceId}
        />
        <nav
          aria-label="워크스페이스 탐색"
          className="order-3 flex w-full overflow-x-auto sm:order-none sm:w-auto sm:flex-1"
        >
          {ROUTES.map((route) => {
            const href = `${base}${route.segment}`;
            const isActive =
              pathname === href || pathname?.startsWith(`${href}/`);

            return (
              <Link
                key={route.segment}
                href={href}
                aria-current={isActive ? "page" : undefined}
                data-active={isActive ? "true" : undefined}
                className="nw-focus-ring shrink-0 border-b-2 border-transparent px-sm py-sm text-sm font-semibold text-[var(--nw-muted)] data-[active=true]:border-[var(--nw-ink)] data-[active=true]:text-[var(--nw-ink)]"
              >
                {route.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
