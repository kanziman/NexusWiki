"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { LogOut, UserRound } from "lucide-react";
import { useState } from "react";

import { createClient } from "@/lib/supabase/client";

type AccountMenuProps = {
  email: string;
};

export function AccountMenu({ email }: AccountMenuProps) {
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <DropdownMenu.Root open={open} onOpenChange={setOpen}>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          aria-label="계정 메뉴"
          className="nw-focus-ring ml-auto flex h-11 min-w-11 items-center justify-center text-[var(--nw-ink)] sm:ml-0"
        >
          <UserRound size={19} aria-hidden="true" />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="w-64 rounded-md border border-[var(--nw-rule)] bg-[var(--nw-surface)] p-xs shadow-[0_12px_28px_rgba(0,0,0,0.08)]"
        >
          <p
            className="truncate px-sm py-xs text-[var(--nw-muted)]"
            style={{ font: "var(--font-caption)" }}
          >
            {email}
          </p>
          <DropdownMenu.Separator className="my-xs h-px bg-[var(--nw-rule)]" />
          <DropdownMenu.Item
            disabled={signingOut}
            onSelect={(event) => {
              event.preventDefault();
              void handleSignOut();
            }}
            className="nw-focus-ring flex cursor-pointer items-center gap-sm px-sm py-sm text-[var(--nw-ink)] outline-none data-[highlighted]:bg-[var(--nw-canvas)] data-[disabled]:cursor-wait data-[disabled]:opacity-60"
            style={{ font: "var(--font-caption)", fontWeight: 600 }}
          >
            <LogOut size={16} aria-hidden="true" />
            {signingOut ? "로그아웃 중" : "로그아웃"}
          </DropdownMenu.Item>
          {error ? (
            <p
              role="alert"
              className="px-sm py-xs text-[var(--color-primary-error-text)]"
              style={{ font: "var(--font-caption-sm)" }}
            >
              {error}
            </p>
          ) : null}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
