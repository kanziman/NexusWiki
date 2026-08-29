"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as Tooltip from "@radix-ui/react-tooltip";
import { Check, ChevronDown, Loader2, Plus } from "lucide-react";

import { createPersonalWorkspace } from "@/app/onboarding-actions";
import { workspacePath } from "@/lib/workspace-path";

export type WorkspaceSwitcherProps = {
  workspaces: { id: string; name: string; kind: "personal" | "team" }[];
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

  // 인라인 생성 폼 상태 — ADR-2: 이 컴포넌트 밖 어디에서도 필요 없다.
  const [creatingOpen, setCreatingOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

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

  function resetCreateForm() {
    setCreatingOpen(false);
    setNewName("");
    setCreateError(null);
  }

  async function handleCreateSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (creating) return;

    setCreating(true);
    setCreateError(null);

    const result = await createPersonalWorkspace(newName);
    if ("error" in result) {
      setCreateError(result.error);
      setCreating(false);
      return;
    }

    setOpen(false);
    resetCreateForm();
    setCreating(false);
    router.push(workspacePath(result.workspaceId));
  }

  return (
    <Tooltip.Provider delayDuration={300}>
      <DropdownMenu.Root
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          // 드롭다운이 닫히면(외부 클릭 등) 인라인 폼도 같이 리셋한다 — 다음에
          // 열었을 때 이전 입력이 남아있지 않도록(스펙: 인라인 폼 취소).
          if (!next) {
            resetCreateForm();
          }
        }}
      >
        <DropdownMenu.Trigger asChild>
          <button
            type="button"
            className="switcher cursor-pointer"
            data-od-id="workspace-switcher"
            aria-label={current?.name ?? "워크스페이스 선택"}
          >
            <span className="switcher-mark">{initial}</span>
            <span className="switcher-name">
              {current?.name ?? "워크스페이스 선택"}
            </span>
            {current?.kind ? (
              <span
                data-testid="current-workspace-kind-badge"
                className="switcher-kind"
              >
                {current.kind === "team" ? "팀" : "개인"}
              </span>
            ) : null}
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
                      <span className="flex min-w-0 items-center gap-1.5">
                        <span className="min-w-0 truncate">
                          {workspace.name}
                        </span>
                        <span className="shrink-0 rounded-full border border-[var(--border)] px-1.5 py-0.5 text-[9px] font-mono font-semibold text-[var(--muted)]">
                          {workspace.kind === "team" ? "팀" : "개인"}
                        </span>
                      </span>
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

            {/* ADR-1: DropdownMenu.Item이 아니라 평범한 div다 — Item은 선택
                시 메뉴를 자동으로 닫고, roving tabIndex가 안의 input과
                방향키 내비게이션을 두고 충돌한다. */}
            {workspaces.length < 3 ? (
              <div className="px-0.5 py-0.5">
                {!creatingOpen ? (
                  <button
                    type="button"
                    onClick={() => setCreatingOpen(true)}
                    className="flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-xs font-semibold text-[var(--muted)] outline-none transition-colors hover:bg-[var(--surface)] hover:text-[var(--fg)]"
                  >
                    <Plus size={13} aria-hidden="true" />
                    <span>새 워크스페이스 생성</span>
                  </button>
                ) : (
                  <form
                    onSubmit={handleCreateSubmit}
                    className="flex flex-col gap-1.5 px-2 py-1"
                  >
                    <input
                      autoFocus
                      type="text"
                      value={newName}
                      onChange={(event) => setNewName(event.target.value)}
                      onKeyDown={(event) => {
                        // Radix DropdownMenu.Content의 typeahead가 이 키
                        // 입력을 항목 검색으로 가로채지 않도록 전파를 막는다.
                        event.stopPropagation();
                        if (event.key === "Escape") {
                          event.preventDefault();
                          resetCreateForm();
                        }
                      }}
                      placeholder="워크스페이스 이름"
                      disabled={creating}
                      aria-label="새 워크스페이스 이름"
                      className="w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-xs outline-none focus:border-[var(--accent)] disabled:opacity-50"
                    />
                    {createError !== null ? (
                      <p
                        role="alert"
                        className="text-[11px] text-[var(--color-primary-error-text)]"
                      >
                        {createError}
                      </p>
                    ) : null}
                    <div className="flex items-center gap-1.5">
                      {/* 빈 문자열 제출을 클라이언트에서 막지 않는다 — 100자
                          초과와 마찬가지로 서버(createPersonalWorkspace)의
                          "이름은 1~100자여야 합니다." 오류를 그대로 타서
                          같은 경로로 폼 안에 표시한다(spec: 인라인 폼 제출
                          중 검증 오류). 여기서만 막으면 그 경로가 아예
                          발동하지 않는다. */}
                      <button
                        type="submit"
                        disabled={creating}
                        className="flex-1 rounded-md bg-[var(--fg)] px-2 py-1.5 text-xs font-semibold text-white transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {creating ? "생성 중…" : "생성"}
                      </button>
                      <button
                        type="button"
                        onClick={resetCreateForm}
                        disabled={creating}
                        className="flex-1 rounded-md border border-[var(--border)] px-2 py-1.5 text-xs font-semibold text-[var(--fg)] transition-colors hover:bg-[var(--surface)] disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        취소
                      </button>
                    </div>
                  </form>
                )}
              </div>
            ) : null}
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
    </Tooltip.Provider>
  );
}
