"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

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
    <form
      onSubmit={handleSubmit}
      className="public-share"
      aria-label="공개 공유 설정"
    >
      <div className="public-share-head">
        <div>
          <h3>공개 공유 (Public Sharing)</h3>
          <p>
            검증 및 승인된 위키 문서를 비로그인 사용자에게 공개할 수 있는 마스터
            킬스위치를 관리합니다.
          </p>
          <p className="mt-[6px]">공개 공유 마스터 킬스위치</p>
        </div>

        <div className={`share-state ${allowPublicSharing ? "on" : ""}`}>
          <span>{allowPublicSharing ? "ON" : "OFF"}</span>
          <label className="inline-flex cursor-pointer items-center">
            <input
              type="checkbox"
              checked={allowPublicSharing}
              disabled={!isOwner || saving}
              onChange={(e) => setAllowPublicSharing(e.target.checked)}
              aria-label="공개 공유 마스터 킬스위치 토글"
              className="toggle-input sr-only"
            />
            <span className="toggle" aria-hidden="true" />
          </label>
        </div>
      </div>

      <div className="public-share-body">
        <p className="share-note" role="note">
          {allowPublicSharing
            ? "공개 공유가 활성화되어 있습니다. 승인된 위키 문서가 외부 URL로 공개됩니다."
            : "공개 공유가 꺼져 있습니다. 모든 외부 공개 URL(/p/...)이 즉시 404로 차단됩니다."}
        </p>

        <div className="public-field">
          <label htmlFor="public-display-name-input">
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
          />
        </div>

        <div className="public-field">
          <label htmlFor="public-description-input">
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
          />
        </div>

        <div className="public-field full">
          <div className="public-route">
            <code>/p/{workspaceSlug}/[페이지_슬러그]</code>
            <span>공개 URL 형식</span>
          </div>
        </div>

        {errorMessage && (
          <p role="alert" className="invite-feedback error show">
            {errorMessage}
          </p>
        )}

        {successMessage && (
          <p role="status" className="invite-feedback show">
            {successMessage}
          </p>
        )}

        {isOwner && (
          <div className="settings-actions public-field full">
            <button type="submit" disabled={saving} className="button">
              {saving ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  <span>저장 중...</span>
                </>
              ) : (
                <span>공개 설정 저장</span>
              )}
            </button>
          </div>
        )}
      </div>
    </form>
  );
}
