"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { LogOut, Plus, Settings, UserRound, Zap } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";

import { CreateWorkspaceModal } from "@/components/CreateWorkspaceModal";

type WorkspaceBudget = {
  cap_micros: number;
  spent_micros: number;
  remaining_micros: number;
  month_start: string;
  truncated: boolean;
  authoritative: boolean;
};

function formatMicros(micros: number): string {
  return new Intl.NumberFormat("ko-KR", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(micros / 1_000_000);
}

type AccountMenuProps = {
  email: string;
  workspaceId?: string;
  workspaceCount?: number;
};

export function AccountMenu({
  email,
  workspaceId,
  workspaceCount,
}: AccountMenuProps) {
  const [open, setOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [budget, setBudget] = useState<WorkspaceBudget | null>(null);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const maxReached = typeof workspaceCount === "number" && workspaceCount >= 3;

  useEffect(() => {
    if (!open || !workspaceId) return;
    let cancelled = false;
    apiFetch<WorkspaceBudget>(`/workspaces/${workspaceId}/budget`)
      .then((res) => {
        if (!cancelled && res && typeof res.cap_micros === "number") {
          setBudget(res);
        }
      })
      .catch(() => {
        // 오류 시 조용히 무시
      });
    return () => {
      cancelled = true;
    };
  }, [open, workspaceId]);

  async function handleSignOut() {
    if (signingOut) return;

    setSigningOut(true);
    setError(null);
    const { error: signOutError } = await createClient().auth.signOut();

    if (signOutError) {
      setSigningOut(false);
      setError("로그아웃하지 못했습니다. 다시 시도해주세요.");
      return;
    }

    // 로그인 직후와 마찬가지로 전체 네비게이션을 사용한다. 새 요청이 middleware를
    // 통과해, 막 종료한 세션으로 RSC를 렌더링하는 경쟁 조건을 피한다.
    window.location.assign("/login");
  }

  const initial = email ? email[0].toUpperCase() : "U";
  const username = email ? email.split("@")[0] : "사용자";

  const percent =
    budget && budget.cap_micros > 0
      ? Math.min(
          100,
          Math.max(0, (budget.spent_micros / budget.cap_micros) * 100),
        )
      : 0;

  return (
    <>
      <DropdownMenu.Root open={open} onOpenChange={setOpen}>
        <DropdownMenu.Trigger asChild>
          <button
            type="button"
            aria-label="계정 메뉴"
            className="nw-focus-ring ml-auto flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--fg)] hover:bg-[var(--soft)] hover:border-[var(--accent)] transition-all cursor-pointer sm:ml-0"
          >
            <UserRound size={18} aria-hidden="true" />
          </button>
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content
            align="end"
            sideOffset={8}
            className="w-72 rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-2 shadow-2xl outline-none duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95"
          >
            {/* 사용자 프로필 헤더 */}
            <div className="flex items-center gap-3 p-2.5 rounded-xl bg-[var(--surface)]/50 border border-[var(--border)]/60">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--accent)] text-white font-bold text-sm shadow-2xs flex-none">
                {initial}
              </div>
              <div className="min-w-0 flex-1">
                <span className="block truncate text-xs font-bold text-[var(--fg)]">
                  {username}
                </span>
                <span className="block truncate text-[11px] text-[var(--muted)]">
                  {email}
                </span>
              </div>
            </div>

            {/* 무료 크레딧 현황 카드 */}
            {workspaceId && budget && budget.cap_micros > 0 && (
              <Link
                href={`/w/${workspaceId}/settings?tab=operations`}
                className="block mx-0.5 my-2 rounded-xl border border-[var(--border)] bg-[var(--surface)]/60 p-2.5 space-y-2 hover:border-[var(--accent)]/60 hover:bg-[var(--soft)]/40 transition-all group"
                title="운영 현황 및 크레딧 확인"
              >
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1.5 font-bold text-[var(--fg)]">
                    <Zap
                      size={13}
                      className="text-[var(--accent)]"
                      aria-hidden="true"
                    />
                    <span>무료 크레딧</span>
                  </div>
                  <span className="font-bold text-[var(--accent)] text-[11px]">
                    {formatMicros(budget.remaining_micros)} 남음
                  </span>
                </div>
                <div
                  className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--border)]"
                  role="progressbar"
                  aria-valuenow={Math.round(percent)}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="크레딧 사용률"
                >
                  <div
                    className="h-full bg-[var(--accent)] transition-all duration-300 rounded-full"
                    style={{ width: `${percent}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-[10.5px] text-[var(--muted)]">
                  <span>사용 {formatMicros(budget.spent_micros)}</span>
                  <span>한도 {formatMicros(budget.cap_micros)}</span>
                </div>
              </Link>
            )}

            <DropdownMenu.Separator className="my-1.5 h-px bg-[var(--border)]" />

            {/* 워크스페이스 빠른 바로가기 */}
            {workspaceId && (
              <DropdownMenu.Item asChild>
                <Link
                  href={`/w/${workspaceId}/settings`}
                  className="nw-focus-ring flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium text-[var(--fg)] outline-none hover:bg-[var(--surface)] data-[highlighted]:bg-[var(--surface)] transition-colors"
                >
                  <Settings
                    size={15}
                    className="text-[var(--muted)] flex-none"
                    aria-hidden="true"
                  />
                  <span>워크스페이스 설정</span>
                </Link>
              </DropdownMenu.Item>
            )}

            <DropdownMenu.Item
              onSelect={() => {
                setCreateModalOpen(true);
              }}
              className="nw-focus-ring flex cursor-pointer items-center justify-between gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium text-[var(--fg)] outline-none hover:bg-[var(--surface)] data-[highlighted]:bg-[var(--surface)] transition-colors"
            >
              <div className="flex items-center gap-2.5">
                <Plus
                  size={15}
                  className="text-[var(--muted)] flex-none"
                  aria-hidden="true"
                />
                <span>새 워크스페이스 만들기</span>
              </div>
              {maxReached && (
                <span className="text-[10px] font-semibold bg-[var(--surface)] text-[var(--muted)] px-1.5 py-0.5 rounded border border-[var(--border)]">
                  최대 3개
                </span>
              )}
            </DropdownMenu.Item>

            <DropdownMenu.Separator className="my-1.5 h-px bg-[var(--border)]" />

            {/* 로그아웃 버튼 */}
            <DropdownMenu.Item
              disabled={signingOut}
              onSelect={(event) => {
                event.preventDefault();
                void handleSignOut();
              }}
              className="nw-focus-ring flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-semibold text-[var(--danger)] outline-none hover:bg-[var(--danger)]/10 data-[highlighted]:bg-[var(--danger)]/10 transition-colors data-[disabled]:cursor-wait data-[disabled]:opacity-60"
            >
              <LogOut size={15} aria-hidden="true" />
              <span>{signingOut ? "로그아웃 중…" : "로그아웃"}</span>
            </DropdownMenu.Item>

            {error ? (
              <p
                role="alert"
                className="mt-1 px-2.5 py-1 text-[11px] text-[var(--danger)]"
              >
                {error}
              </p>
            ) : null}
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>

      {/* 새 워크스페이스 생성 모달 */}
      <CreateWorkspaceModal
        open={createModalOpen}
        onOpenChange={setCreateModalOpen}
        maxReached={maxReached}
      />
    </>
  );
}
