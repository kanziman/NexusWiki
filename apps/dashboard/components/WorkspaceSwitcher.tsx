"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as Tooltip from "@radix-ui/react-tooltip";
import { ChevronDown, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import { workspacePath } from "@/lib/workspace-path";

export type WorkspaceSwitcherProps = {
  workspaces: { id: string; name: string }[];
  currentWorkspaceId: string;
};

// D-03: 워크스페이스 전환은 URL이 소유한다 — 이 컴포넌트는 어떤 워크스페이스가
// "현재"인지 자체 상태로 들고 있지 않고, currentWorkspaceId prop과
// router.push(workspacePath(id))만으로 동작한다. React state에 남은 낡은 id가
// 조용히 빈 결과를 내는 것을 구조적으로 방지한다.
export function WorkspaceSwitcher({
  workspaces,
  currentWorkspaceId,
}: WorkspaceSwitcherProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [navigatingId, setNavigatingId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  // UI-SPEC UI Considerations (workspace-switcher/loading, backstop): /w/[id]
  // 라우트 재검증이 진행되는 동안 선택한 항목을 비활성화하고 인라인 스피너를
  // 보여준다. isPending이 꺼지면(네비게이션 완료) 드롭다운을 닫는다.
  useEffect(() => {
    if (!isPending && navigatingId !== null) {
      setNavigatingId(null);
      setOpen(false);
    }
  }, [isPending, navigatingId]);

  const current =
    workspaces.find((workspace) => workspace.id === currentWorkspaceId) ?? null;

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
            className="nw-focus-ring flex h-9 max-w-64 min-w-0 items-center gap-xs border-0 bg-transparent px-0 text-[var(--nw-ink)]"
          >
            <span
              className="min-w-0 truncate"
              style={{ font: "var(--font-caption)", fontWeight: 600 }}
            >
              {current?.name ?? "워크스페이스 선택"}
            </span>
            <span
              role="img"
              aria-label="워크스페이스 전환"
              className="flex h-11 w-11 shrink-0 items-center justify-center"
            >
              <ChevronDown size={20} aria-hidden="true" />
            </span>
          </button>
        </DropdownMenu.Trigger>

        <DropdownMenu.Portal>
          <DropdownMenu.Content
            align="start"
            sideOffset={4}
            // overflow backstop: 워크스페이스가 8개를 넘으면 Content 자체가
            // 무한정 자라는 대신 스크롤한다.
            className="max-h-64 overflow-y-auto rounded-md border border-[var(--nw-rule)] bg-[var(--nw-surface)] py-xs shadow-[0_12px_28px_rgba(0,0,0,0.08)]"
          >
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
                      className={`nw-focus-ring flex cursor-pointer items-center justify-between gap-xs px-base py-sm outline-none data-[highlighted]:bg-[var(--nw-canvas)] data-[disabled]:cursor-default data-[disabled]:opacity-60 ${
                        isActive
                          ? "text-[var(--nw-ink)]"
                          : "text-[var(--nw-body)]"
                      }`}
                      style={{ font: "var(--font-caption)", fontWeight: 600 }}
                    >
                      <span className="min-w-0 truncate">{workspace.name}</span>
                      {isNavigating ? (
                        <Loader2
                          size={14}
                          className="shrink-0 animate-spin"
                          aria-hidden="true"
                        />
                      ) : null}
                    </DropdownMenu.Item>
                  </Tooltip.Trigger>
                  {/* long-text backstop: 트리거에서 truncate된 긴 이름은
                      hover/focus 시 Tooltip으로 전체 텍스트를 노출한다. */}
                  <Tooltip.Portal>
                    <Tooltip.Content
                      side="right"
                      sideOffset={4}
                      className="z-50 rounded-sm bg-ink px-sm py-xs text-on-primary"
                      style={{ font: "var(--font-caption-sm)" }}
                    >
                      {workspace.name}
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              );
            })}
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
    </Tooltip.Provider>
  );
}
