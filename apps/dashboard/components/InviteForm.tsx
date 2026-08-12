"use client";

import * as Select from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import { useId, useState } from "react";

import { createClient } from "@/lib/supabase/client";

export type InviteFormProps = {
  workspaceId: string;
  onInvited?: () => void;
};

type Role = "owner" | "editor" | "viewer";

const ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "owner", label: "소유자" },
  { value: "editor", label: "편집자" },
  { value: "viewer", label: "뷰어" },
];

// UI-SPEC "Invite form (UI-02) | Role field default": 명시적으로 건드리지
// 않으면 viewer(least privilege).
const DEFAULT_ROLE: Role = "viewer";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// UI-SPEC 카피 계약(Invite form(UI-02))의 세 상태 문구 — 문자 하나 바꾸지 않는다.
const DUPLICATE_MEMBER_ERROR = "이미 워크스페이스 멤버입니다.";
const UNREGISTERED_EMAIL_ERROR =
  "가입된 사용자를 찾을 수 없습니다 — 초대 대상이 먼저 NexusWiki 계정을 만들어야 합니다.";
const FORBIDDEN_ERROR = "권한이 없습니다.";
const GENERIC_ERROR = "초대를 보내지 못했습니다.";

export function InviteForm({ workspaceId, onInvited }: InviteFormProps) {
  const emailId = useId();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>(DEFAULT_ROLE);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // UI-SPEC: "submit stays disabled only on invalid email format, not on role
  // choice" — role 유효성은 Select가 3값만 노출하므로 여기서 별도 검사하지 않는다.
  const isValidEmail = EMAIL_PATTERN.test(email.trim());
  const canSubmit = isValidEmail && !submitting;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError(null);
    setSuccess(false);

    const supabase = createClient();
    const { error: rpcError } = await supabase.rpc("invite_workspace_member", {
      p_workspace_id: workspaceId,
      p_email: email.trim(),
      p_role: role,
    });

    setSubmitting(false);

    if (rpcError) {
      // 0014가 던지는 SQLSTATE를 그대로 분기한다 — Supabase JS의
      // PostgrestError.code에 실려 온다. 42501(비-owner)은 방어선일 뿐이다:
      // 정상 흐름에서는 owner가 아닌 사용자에게 이 폼 자체를 숨기는 것이
      // 우선이고(설정 페이지/멤버 목록의 owner 판정), 이 분기는 그 판정을
      // 우회해 직접 RPC를 호출한 경우에도 조용히 성공한 것처럼 보이지
      // 않도록 하는 마지막 방어선이다.
      if (rpcError.code === "NW409") {
        setError(DUPLICATE_MEMBER_ERROR);
      } else if (rpcError.code === "NW404") {
        setError(UNREGISTERED_EMAIL_ERROR);
      } else if (rpcError.code === "42501") {
        setError(FORBIDDEN_ERROR);
      } else {
        setError(GENERIC_ERROR);
      }
      // 실패 시 폼을 비우지 않는다 — 사용자가 같은 값을 다시 확인/수정할 수 있어야 한다.
      return;
    }

    setEmail("");
    setRole(DEFAULT_ROLE);
    setSuccess(true);
    onInvited?.();
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-base">
      <div className="flex flex-col gap-xs">
        <label
          htmlFor={emailId}
          className="text-ink"
          style={{ font: "var(--font-caption)" }}
        >
          이메일
        </label>
        <input
          id={emailId}
          name="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
            setError(null);
            setSuccess(false);
          }}
          className="h-12 w-full rounded-sm border border-border-strong bg-canvas px-base text-ink outline-none focus:border-2 focus:border-ink"
          style={{ font: "var(--font-body-md)" }}
        />
      </div>

      <div className="flex flex-col gap-xs">
        <span className="text-ink" style={{ font: "var(--font-caption)" }}>
          역할
        </span>
        <Select.Root
          value={role}
          onValueChange={(value) => setRole(value as Role)}
        >
          <Select.Trigger
            aria-label="역할 선택"
            className="flex h-12 items-center justify-between rounded-sm border border-border-strong bg-canvas px-base text-ink"
          >
            <Select.Value />
            <Select.Icon>
              <ChevronDown size={16} aria-hidden="true" />
            </Select.Icon>
          </Select.Trigger>
          <Select.Portal>
            <Select.Content className="rounded-sm border border-hairline bg-canvas shadow-[var(--shadow-dropdown)]">
              <Select.Viewport>
                {ROLE_OPTIONS.map((option) => (
                  <Select.Item
                    key={option.value}
                    value={option.value}
                    className="flex cursor-pointer items-center gap-xs px-base py-sm outline-none data-[highlighted]:bg-surface-soft"
                  >
                    <Select.ItemText>{option.label}</Select.ItemText>
                    <Select.ItemIndicator>
                      <Check size={14} aria-hidden="true" />
                    </Select.ItemIndicator>
                  </Select.Item>
                ))}
              </Select.Viewport>
            </Select.Content>
          </Select.Portal>
        </Select.Root>
      </div>

      {error !== null ? (
        <p
          role="alert"
          data-state="error"
          className="text-primary-error-text"
          style={{ font: "var(--font-caption)" }}
        >
          {error}
        </p>
      ) : null}

      {success ? (
        <p
          role="status"
          className="text-success-text"
          style={{ font: "var(--font-caption)" }}
        >
          초대를 보냈습니다.
        </p>
      ) : null}

      {/* UI-SPEC Primary Visual Anchor(UI-02): 이 버튼이 화면에서 유일한
          accent(--color-primary) 요소여야 한다. */}
      <button
        type="submit"
        disabled={!canSubmit}
        className="h-12 rounded-sm bg-primary px-lg text-on-primary transition-colors active:bg-primary-active disabled:cursor-not-allowed disabled:bg-primary-disabled"
        style={{ font: "var(--font-button-md)" }}
      >
        초대 보내기
      </button>
    </form>
  );
}
