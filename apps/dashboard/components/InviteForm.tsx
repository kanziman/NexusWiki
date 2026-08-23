"use client";

import * as Select from "@radix-ui/react-select";
import { Check, ChevronDown, Lock } from "lucide-react";
import { useId, useState } from "react";

import { createClient } from "@/lib/supabase/client";

export type InviteFormProps = {
  workspaceId: string;
  isPersonal?: boolean;
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

export function InviteForm({
  workspaceId,
  isPersonal = false,
  onInvited,
}: InviteFormProps) {
  const emailId = useId();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>(DEFAULT_ROLE);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // UI-SPEC: "submit stays disabled only on invalid email format, not on role
  // choice" — role 유효성은 Select가 3값만 노출하므로 여기서 별도 검사하지 않는다.
  const isValidEmail = EMAIL_PATTERN.test(email.trim());
  const canSubmit = !isPersonal && isValidEmail && !submitting;

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
    <section className="invite" data-od-id="invite-member">
      <h3>새 멤버 초대</h3>
      <p>가입된 계정만 초대할 수 있습니다. 기본 역할은 뷰어입니다.</p>

      {isPersonal && (
        <div
          role="note"
          className="mb-4 mt-2 rounded-xl border border-[var(--border)] bg-[var(--surface)]/50 p-3.5 text-xs text-[var(--muted)] flex items-start gap-2.5"
        >
          <Lock
            size={15}
            className="flex-none mt-0.5 text-[var(--muted)]"
            aria-hidden="true"
          />
          <div>
            <strong className="block text-[var(--fg)] font-semibold mb-0.5">
              개인 워크스페이스는 멤버 초대가 비활성화되어 있습니다
            </strong>
            <span>
              팀원을 초대하여 함께 지식을 관리하려면 <strong>[일반]</strong>{" "}
              설정 탭에서 워크스페이스 유형을{" "}
              <strong>&apos;팀 워크스페이스&apos;</strong>로 변경하세요.
            </span>
          </div>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className={`invite-form ${isPersonal ? "opacity-60 pointer-events-none" : ""}`}
      >
        {/* 프로토타입은 라벨을 그리지 않지만, 라벨 없는 입력은 스크린 리더에
            "편집 텍스트"로만 읽힌다 — 시각적으로만 감춘다. */}
        <label htmlFor={emailId} className="sr-only">
          이메일
        </label>
        <input
          id={emailId}
          name="email"
          type="email"
          required
          disabled={isPersonal}
          autoComplete="email"
          placeholder="초대할 사람의 이메일"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
            setError(null);
            setSuccess(false);
          }}
          className="field"
        />

        <Select.Root
          value={role}
          disabled={isPersonal}
          onValueChange={(value) => setRole(value as Role)}
        >
          <Select.Trigger
            aria-label="역할 선택"
            disabled={isPersonal}
            className="field flex items-center justify-between"
          >
            <Select.Value />
            <Select.Icon>
              <ChevronDown size={14} aria-hidden="true" />
            </Select.Icon>
          </Select.Trigger>
          <Select.Portal>
            {/* Radix 가 위치를 인라인 style 로 잡는다 — .menu 는 자체
                position/right 를 갖고 있어 그 계산과 싸운다. 생김새만 맞춘다. */}
            <Select.Content className="z-20 min-w-[154px] rounded-[9px] border border-[var(--border)] bg-[var(--bg)] p-[5px] shadow-[var(--shadow)]">
              <Select.Viewport>
                {ROLE_OPTIONS.map((option) => (
                  <Select.Item
                    key={option.value}
                    value={option.value}
                    className="flex cursor-pointer items-center gap-1 rounded-md px-2 py-2 text-[11px] font-bold outline-none data-[highlighted]:bg-[var(--surface)]"
                  >
                    <Select.ItemText>{option.label}</Select.ItemText>
                    <Select.ItemIndicator>
                      <Check size={13} aria-hidden="true" />
                    </Select.ItemIndicator>
                  </Select.Item>
                ))}
              </Select.Viewport>
            </Select.Content>
          </Select.Portal>
        </Select.Root>

        {/* 명세 §버튼: primary 는 화면당 1개 — 설정 화면의 그 하나가 이 버튼이다. */}
        <button type="submit" disabled={!canSubmit} className="button primary">
          초대 보내기
        </button>
      </form>

      {error !== null ? (
        <p
          role="alert"
          data-state="error"
          className="invite-feedback error show"
        >
          {error}
        </p>
      ) : null}

      {success ? (
        <p role="status" className="invite-feedback show">
          초대를 보냈습니다.
        </p>
      ) : null}
    </section>
  );
}
