"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Loader2, Plus, Sparkles, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { createPersonalWorkspace } from "@/app/onboarding-actions";
import { workspacePath } from "@/lib/workspace-path";

type CreateWorkspaceModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  maxReached?: boolean;
};

export function CreateWorkspaceModal({
  open,
  onOpenChange,
  maxReached = false,
}: CreateWorkspaceModalProps) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmedName = name.trim();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!trimmedName || creating || maxReached) return;

    setCreating(true);
    setError(null);

    const result = await createPersonalWorkspace(trimmedName);

    if ("error" in result) {
      setCreating(false);
      setError(result.error);
      return;
    }

    setCreating(false);
    setName("");
    onOpenChange(false);
    router.push(workspacePath(result.workspaceId));
  }

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(next) => {
        if (!creating) {
          if (!next) {
            setName("");
            setError(null);
          }
          onOpenChange(next);
        }
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md transition-all duration-200" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-50 w-[min(480px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-6 shadow-2xl outline-none">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--accent)] text-white shadow-xs flex-none">
                <Sparkles size={18} aria-hidden="true" />
              </div>
              <div>
                <Dialog.Title className="text-base font-bold text-[var(--fg)]">
                  새 워크스페이스 만들기
                </Dialog.Title>
                <Dialog.Description className="text-xs text-[var(--muted)] mt-0.5">
                  새로운 지식 베이스를 시작할 워크스페이스 이름을 입력하세요.
                </Dialog.Description>
              </div>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                disabled={creating}
                className="icon-btn rounded-lg p-1 text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--fg)] transition-colors cursor-pointer"
                aria-label="닫기"
              >
                <X size={16} aria-hidden="true" />
              </button>
            </Dialog.Close>
          </div>

          {maxReached ? (
            <div className="rounded-xl border border-[var(--warning)]/30 bg-[var(--warning)]/5 p-4 my-3 text-xs leading-relaxed text-[var(--fg)]">
              <b className="block text-[var(--warning)] font-bold mb-1">
                워크스페이스 최대 개수(3개)에 도달했습니다
              </b>
              <span>
                새 워크스페이스를 생성하려면 기존 워크스페이스의 [설정 &gt; 위험
                구역]에서 사용하지 않는 워크스페이스를 먼저 삭제해 주세요.
              </span>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4 mt-2">
              <div>
                <label
                  htmlFor="new-workspace-name-modal-input"
                  className="block text-xs font-semibold text-[var(--fg)] mb-1.5"
                >
                  워크스페이스 이름
                </label>
                <input
                  id="new-workspace-name-modal-input"
                  type="text"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    if (error) setError(null);
                  }}
                  maxLength={100}
                  placeholder="예: 마케팅 전략 위키"
                  disabled={creating}
                  autoFocus
                  required
                  className="field"
                />
              </div>

              {error && (
                <p role="alert" className="invite-feedback error show">
                  {error}
                </p>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <Dialog.Close asChild>
                  <button
                    type="button"
                    disabled={creating}
                    className="button compact"
                  >
                    취소
                  </button>
                </Dialog.Close>
                <button
                  type="submit"
                  disabled={!trimmedName || creating}
                  className="button compact primary disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {creating ? (
                    <Loader2 size={13} className="animate-spin" />
                  ) : (
                    <Plus size={13} aria-hidden="true" />
                  )}
                  <span>생성하기</span>
                </button>
              </div>
            </form>
          )}

          {maxReached && (
            <div className="flex items-center justify-end gap-2 mt-4 pt-2 border-t border-[var(--border)]">
              <Dialog.Close asChild>
                <button type="button" className="button compact">
                  닫기
                </button>
              </Dialog.Close>
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
