"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

import { createClient } from "@/lib/supabase/client";
import { PublicSharingSettings } from "@/components/PublicSharingSettings";

export type WorkspaceGeneralSettingsProps = {
  workspaceId: string;
  initialName: string;
  initialSlug: string;
  isOwner: boolean;
};

const SLUG_REGEX = /^[0-9a-z가-힣][0-9a-z가-힣-]*$/;

export function WorkspaceGeneralSettings({
  workspaceId,
  initialName,
  initialSlug,
  isOwner,
}: WorkspaceGeneralSettingsProps) {
  const [name, setName] = useState(initialName);
  const [slug, setSlug] = useState(initialSlug);
  const [saving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!isOwner || saving) return;

    const trimmedName = name.trim();
    const trimmedSlug = slug.trim();

    if (!trimmedName || trimmedName.length > 100) {
      setErrorMessage("워크스페이스 이름은 1자 이상 100자 이하이어야 합니다.");
      return;
    }

    if (
      !trimmedSlug ||
      trimmedSlug.length > 80 ||
      !SLUG_REGEX.test(trimmedSlug)
    ) {
      setErrorMessage(
        "슬러그는 1자 이상 80자 이하의 영문 소문자, 숫자, 한글, 하이픈(-)만 사용할 수 있습니다.",
      );
      return;
    }

    setSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    const supabase = createClient();
    const { data, error } = await supabase
      .from("workspaces")
      .update({ name: trimmedName, slug: trimmedSlug })
      .eq("id", workspaceId)
      .select();

    setSaving(false);

    if (error || !data || data.length === 0) {
      setErrorMessage(
        error?.message || "워크스페이스 설정을 저장하지 못했습니다.",
      );
      return;
    }

    setSuccessMessage("워크스페이스 정보가 저장되었습니다.");
  }

  return (
    <section className="flex flex-col gap-base" aria-label="기본 설정">
      <div>
        <h2 className="text-ink" style={{ font: "var(--font-title-md)" }}>
          기본 정보
        </h2>
        <p className="text-sm text-[var(--muted)]">
          워크스페이스 이름과 식별용 슬러그를 관리합니다.
        </p>
      </div>

      {!isOwner && (
        <div
          role="note"
          className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-3 text-xs text-[var(--muted)]"
        >
          소유자(Owner)만 워크스페이스 설정을 변경할 수 있습니다.
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-base">
        <div className="flex flex-col gap-xs">
          <label
            htmlFor="workspace-name-input"
            className="text-xs font-semibold text-[var(--fg)]"
          >
            워크스페이스 이름
          </label>
          <input
            id="workspace-name-input"
            type="text"
            value={name}
            disabled={!isOwner || saving}
            onChange={(e) => {
              setName(e.target.value);
              setErrorMessage(null);
              setSuccessMessage(null);
            }}
            placeholder="워크스페이스 이름"
            className="h-10 rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 text-sm text-[var(--fg)] outline-none focus:border-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-60"
            required
            maxLength={100}
          />
        </div>

        <div className="flex flex-col gap-xs">
          <label
            htmlFor="workspace-slug-input"
            className="text-xs font-semibold text-[var(--fg)]"
          >
            워크스페이스 슬러그
          </label>
          <input
            id="workspace-slug-input"
            type="text"
            value={slug}
            disabled={!isOwner || saving}
            onChange={(e) => {
              setSlug(e.target.value);
              setErrorMessage(null);
              setSuccessMessage(null);
            }}
            placeholder="workspace-slug"
            className="h-10 rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 font-mono text-sm text-[var(--fg)] outline-none focus:border-[var(--accent)] disabled:cursor-not-allowed disabled:opacity-60"
            required
            maxLength={80}
          />
          <span className="text-[11px] text-[var(--muted)]">
            URL 및 공유 식별자로 사용됩니다 (영문 소문자, 숫자, 한글, 하이픈).
          </span>
        </div>

        {errorMessage && (
          <div
            role="alert"
            className="rounded-md border border-[var(--danger)]/30 bg-[var(--danger)]/10 p-2.5 text-xs text-[var(--danger)]"
          >
            {errorMessage}
          </div>
        )}

        {successMessage && (
          <div
            role="status"
            className="rounded-md border border-[var(--accent)]/30 bg-[var(--accent)]/10 p-2.5 text-xs text-[var(--accent)]"
          >
            {successMessage}
          </div>
        )}

        {isOwner && (
          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex h-9 items-center justify-center gap-1.5 rounded-md bg-[var(--accent)] px-4 text-xs font-semibold text-white shadow-sm transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving && <Loader2 size={13} className="animate-spin" />}
              <span>저장</span>
            </button>
          </div>
        )}
      </form>

      <PublicSharingSettings
        workspaceId={workspaceId}
        workspaceSlug={slug || initialSlug}
        isOwner={isOwner}
      />
    </section>
  );
}
