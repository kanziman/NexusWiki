"use client";

import { useState } from "react";
import { Globe, Loader2, ShieldAlert } from "lucide-react";

import { createClient } from "@/lib/supabase/client";

export type PublicSharingSettingsProps = {
  workspaceId: string;
  workspaceSlug: string;
  isOwner: boolean;
  initialAllowPublicSharing?: boolean;
  initialDisplayName?: string;
  initialDescription?: string;
};

export function PublicSharingSettings({
  workspaceId,
  workspaceSlug,
  isOwner,
  initialAllowPublicSharing = false,
  initialDisplayName = "",
  initialDescription = "",
}: PublicSharingSettingsProps) {
  const [allowPublicSharing, setAllowPublicSharing] = useState(
    initialAllowPublicSharing,
  );
  const [displayName, setDisplayName] = useState(initialDisplayName);
  const [description, setDescription] = useState(initialDescription);
  const [saving, setSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!isOwner || saving) return;

    setSaving(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    const supabase = createClient();
    const { error } = await supabase.from("workspace_public_settings").upsert({
      workspace_id: workspaceId,
      workspace_slug: workspaceSlug,
      allow_public_sharing: allowPublicSharing,
      public_display_name: displayName.trim() || null,
      public_description: description.trim() || null,
      updated_at: new Date().toISOString(),
    });

    setSaving(false);

    if (error) {
      setErrorMessage(error.message || "공개 설정을 저장하지 못했습니다.");
      return;
    }

    setSuccessMessage("공개 설정이 성공적으로 저장되었습니다.");
  }

  return (
    <section
      className="flex flex-col gap-base border-t border-[var(--border)] pt-xl"
      aria-label="공개 공유 설정"
    >
      <div>
        <h2
          className="flex items-center gap-xs text-ink"
          style={{ font: "var(--font-title-md)" }}
        >
          <Globe size={18} className="text-[var(--accent)]" />
          <span>공개 공유 (Public Sharing)</span>
        </h2>
        <p className="text-sm text-[var(--muted)]">
          검증 및 승인된 위키 문서를 비로그인 사용자에게 공개할 수 있는 마스터
          킬스위치를 관리합니다.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-base">
        {/* 마스터 킬스위치 토글 */}
        <div className="flex items-start justify-between gap-base rounded-lg border border-[var(--border)] bg-[var(--surface)] p-base">
          <div className="flex flex-col gap-xs">
            <span className="text-sm font-semibold text-[var(--fg)]">
              공개 공유 마스터 킬스위치
            </span>
            <p className="text-xs text-[var(--muted)]">
              {allowPublicSharing
                ? "공개 공유가 활성화되어 있습니다. 승인된 위키 문서가 외부 URL로 공개됩니다."
                : "공개 공유가 꺼져 있습니다. 모든 외부 공개 URL(/p/...)이 즉시 404로 차단됩니다."}
            </p>
          </div>

          <label className="relative inline-flex cursor-pointer items-center">
            <input
              type="checkbox"
              checked={allowPublicSharing}
              disabled={!isOwner || saving}
              onChange={(e) => setAllowPublicSharing(e.target.checked)}
              aria-label="공개 공유 마스터 킬스위치 토글"
              className="peer sr-only"
            />
            <div className="peer h-6 w-11 rounded-full bg-[var(--surface-soft)] after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-[var(--accent)] peer-checked:after:translate-x-full peer-checked:after:border-white peer-disabled:cursor-not-allowed peer-disabled:opacity-50"></div>
          </label>
        </div>

        {/* 공개 표시명 */}
        <div className="flex flex-col gap-xs">
          <label
            htmlFor="public-display-name-input"
            className="text-xs font-semibold text-[var(--fg)]"
          >
            공개 워크스페이스 표시명 (선택)
          </label>
          <input
            id="public-display-name-input"
            type="text"
            value={displayName}
            disabled={!isOwner || saving}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder={workspaceSlug}
            maxLength={100}
            className="h-10 rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-sm text-[var(--fg)] placeholder-[var(--muted)] outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)] disabled:cursor-not-allowed disabled:bg-[var(--surface-soft)]"
          />
        </div>

        {/* 공개 워크스페이스 설명 */}
        <div className="flex flex-col gap-xs">
          <label
            htmlFor="public-description-input"
            className="text-xs font-semibold text-[var(--fg)]"
          >
            공개 워크스페이스 설명 (선택)
          </label>
          <textarea
            id="public-description-input"
            value={description}
            disabled={!isOwner || saving}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="공개 문서 페이지 상단에 노출될 설명입니다."
            rows={3}
            maxLength={300}
            className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-3 text-sm text-[var(--fg)] placeholder-[var(--muted)] outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)] disabled:cursor-not-allowed disabled:bg-[var(--surface-soft)]"
          />
        </div>

        {/* 공개 URL 프리뷰 */}
        <div className="rounded-md border border-[var(--border)] bg-[var(--surface-soft)] p-base text-xs text-[var(--muted)]">
          <div className="font-semibold text-[var(--fg)] mb-1">
            공개 URL 형식
          </div>
          <code>/p/{workspaceSlug}/[페이지_슬러그]</code>
        </div>

        {errorMessage && (
          <div
            role="alert"
            className="flex items-center gap-xs rounded-md bg-[var(--danger)]/10 p-3 text-xs font-medium text-[var(--danger)]"
          >
            <ShieldAlert size={14} />
            <span>{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div
            role="status"
            className="rounded-md bg-[var(--good)]/10 p-3 text-xs font-medium text-[var(--good)]"
          >
            {successMessage}
          </div>
        )}

        {isOwner && (
          <button
            type="submit"
            disabled={saving}
            className="flex h-10 w-fit items-center justify-center gap-xs rounded-md bg-[var(--accent)] px-lg text-xs font-semibold text-[var(--accent-fg)] hover:opacity-90 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 transition-all"
          >
            {saving ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                <span>저장 중...</span>
              </>
            ) : (
              <span>공개 설정 저장</span>
            )}
          </button>
        )}
      </form>
    </section>
  );
}
