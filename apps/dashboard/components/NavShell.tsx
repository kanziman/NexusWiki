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
    <header className="flex h-16 items-center gap-lg border-b border-hairline bg-surface-soft px-lg">
      <WorkspaceSwitcher
        workspaces={workspaces}
        currentWorkspaceId={currentWorkspaceId}
      />

      <nav className="flex items-center gap-base">
        {ROUTES.map((route) => {
          const href = `${base}${route.segment}`;
          const isActive =
            pathname === href || pathname?.startsWith(`${href}/`);

          return (
            <Link
              key={route.segment}
              href={href}
              aria-current={isActive ? "page" : undefined}
              className={isActive ? "text-primary" : "text-ink"}
              // UI-SPEC Typography Label 행: --font-caption(500 14px/1.29)의
              // 크기/행간은 그대로 쓰되, weight만 06-UI-SPEC.md의 2-weight cap
              // 개정(600)으로 덮어쓴다.
              style={{ font: "600 14px/1.29 var(--font-family-base)" }}
            >
              {route.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
