"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as Tooltip from "@radix-ui/react-tooltip";
import { Check, ChevronDown, Loader2, Plus } from "lucide-react";

import { workspacePath } from "@/lib/workspace-path";

export type WorkspaceSwitcherProps = {
  workspaces: { id: string; name: string }[];
  currentWorkspaceId: string;
};

export function WorkspaceSwitcher({
  workspaces,
  currentWorkspaceId,
}: WorkspaceSwitcherProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [navigatingId, setNavigatingId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (!isPending && navigatingId !== null) {
      setNavigatingId(null);
      setOpen(false);
    }
  }, [isPending, navigatingId]);

  const current =
    workspaces.find((workspace) => workspace.id === currentWorkspaceId) ?? null;
  const initial = (current?.name || "W").charAt(0).toUpperCase();

  function handleSelect(workspaceId: string) {
    if (workspaceId === currentWorkspaceId || navigatingId !== null) return;

    setNavigatingId(workspaceId);
    startTransition(() => {
      router.push(workspacePath(workspaceId));
    });
  }

  return (
    <Tooltip.Provider delayDuration={300}>
      <DropdownMenu.Root open={open} onOpenChange={setOpen}>
        <DropdownMenu.Trigger asChild>
          <button
            type="button"
            className="switcher cursor-pointer"
            data-od-id="workspace-switcher"
          >
            <span className="switcher-mark">{initial}</span>
            <span className="switcher-name">
              {current?.name ?? "워크스페이스 선택"}
            </span>
            <ChevronDown className="chev" aria-hidden="true" />
          </button>
        </DropdownMenu.Trigger>

        <DropdownMenu.Portal>
          <DropdownMenu.Content
            align="start"
            sideOffset={4}
            className="z-50 min-w-56 max-h-64 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--bg)] p-1.5 shadow-[var(--shadow)]"
          >
            <div className="px-2 py-1 text-[10px] font-mono font-semibold tracking-wider text-[var(--muted)]">
              소속 워크스페이스
            </div>

            {workspaces.map((workspace) => {
              const isActive = workspace.id === currentWorkspaceId;
              const isNavigating = navigatingId === workspace.id && isPending;

              return (
                <Tooltip.Root key={workspace.id}>
                  <Tooltip.Trigger asChild>
                    <DropdownMenu.Item
                      data-active={isActive ? "true" : undefined}
                      disabled={isNavigating}
                      onSelect={(event) => {
                        event.preventDefault();
                        handleSelect(workspace.id);
                      }}
                      className={`flex cursor-pointer items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-xs font-semibold outline-none transition-colors data-[highlighted]:bg-[var(--surface)] ${
                        isActive
                          ? "bg-[var(--soft)] text-[var(--accent)]"
                          : "text-[var(--fg)]"
                      }`}
                    >
                      <span className="min-w-0 truncate">{workspace.name}</span>
                      {isNavigating ? (
                        <Loader2
                          size={13}
                          className="shrink-0 animate-spin"
                          aria-hidden="true"
                        />
                      ) : isActive ? (
                        <Check
                          size={13}
                          className="shrink-0 text-[var(--accent)]"
                        />
                      ) : null}
                    </DropdownMenu.Item>
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content
                      side="right"
                      sideOffset={4}
                      className="z-50 rounded-sm bg-[var(--fg)] px-2 py-1 text-[11px] font-semibold text-white shadow-md"
                    >
                      {workspace.name}
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              );
            })}

            <div className="my-1 border-t border-[var(--border)]" />

            {workspaces.length < 3 ? (
              <DropdownMenu.Item asChild>
                <Link
                  href="/w/new"
                  className="flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-1.5 text-xs font-semibold text-[var(--muted)] hover:text-[var(--fg)] outline-none hover:bg-[var(--surface)] transition-colors"
                >
                  <Plus size={13} aria-hidden="true" />
                  <span>새 워크스페이스 생성</span>
                </Link>
              </DropdownMenu.Item>
            ) : null}
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
    </Tooltip.Provider>
  );
}
