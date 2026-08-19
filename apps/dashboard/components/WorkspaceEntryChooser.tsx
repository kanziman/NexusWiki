import Link from "next/link";

import { workspacePath } from "@/lib/workspace-path";

type WorkspaceEntryChooserProps = {
  workspaces: { id: string; name: string }[];
};

// 루트 route가 요청자 JWT와 RLS로 좁힌 목록만 이 컴포넌트에 전달한다. 이 컴포넌트는
// 별도 조회나 React 상태를 갖지 않아 선택 가능한 테넌트 범위를 넓히지 않는다.
export function WorkspaceEntryChooser({
  workspaces,
}: WorkspaceEntryChooserProps) {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col justify-center px-base py-xl sm:px-xl">
      <div className="border-y border-[var(--border)] py-xl sm:py-xxl">
        <p
          className="text-[var(--muted)]"
          style={{ font: "var(--font-caption)", fontWeight: 600 }}
        >
          NEXUSWIKI
        </p>
        <h1
          className="mt-sm text-[var(--fg)]"
          style={{ font: "var(--font-display-lg)" }}
        >
          워크스페이스 선택
        </h1>
        <p
          className="mt-base text-[var(--muted)]"
          style={{ font: "var(--font-body-md)" }}
        >
          계속할 워크스페이스를 선택하세요.
        </p>

        <ul className="mt-xl border-y border-[var(--border)]">
          {workspaces.map((workspace) => (
            <li
              key={workspace.id}
              className="border-b border-[var(--border)] last:border-b-0"
            >
              <Link
                href={workspacePath(workspace.id)}
                className="nw-focus-ring flex min-h-14 items-center justify-between gap-base px-base py-sm text-[var(--fg)] transition-colors hover:bg-[var(--surface)]"
                style={{ font: "var(--font-body-md)", fontWeight: 600 }}
              >
                <span className="min-w-0 truncate">{workspace.name}</span>
                <span aria-hidden="true" className="text-[var(--muted)]">
                  →
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}
