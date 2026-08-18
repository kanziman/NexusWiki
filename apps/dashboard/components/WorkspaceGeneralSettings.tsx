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
    // RLS USING 에 막힌 UPDATE 는 예외가 아니라 0행이다 — .select() 로 되받은
    // 행 수를 확인해야 "차단됨"과 "성공"이 구분된다(CLAUDE.md 불변 규칙).
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
    <>
      <div className="section-head">
        <div>
          <h2>기본 정보</h2>
          <p>워크스페이스 이름과 식별용 슬러그를 관리합니다.</p>
        </div>
      </div>

      {!isOwner && (
        <div role="note" className="role-note">
          소유자(Owner)만 워크스페이스 설정을 변경할 수 있습니다.
        </div>
      )}

      <section className="settings-card" aria-label="기본 설정">
        <h3>워크스페이스 식별</h3>
        <p>슬러그는 공개 URL 과 공유 링크의 식별자로 쓰입니다.</p>

        <form onSubmit={handleSubmit} className="settings-form">
          <div className="settings-field">
            <label htmlFor="workspace-name-input">워크스페이스 이름</label>
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
              className="field"
              required
              maxLength={100}
            />
          </div>

          <div className="settings-field">
            <label htmlFor="workspace-slug-input">워크스페이스 슬러그</label>
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
              className="field mono"
              required
              maxLength={80}
            />
            <span className="hint">
              URL 및 공유 식별자로 사용됩니다 (영문 소문자, 숫자, 한글, 하이픈).
            </span>
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
            <div className="settings-actions">
              <button type="submit" disabled={saving} className="button">
                {saving && <Loader2 size={13} className="animate-spin" />}
                <span>저장</span>
              </button>
            </div>
          )}
        </form>
      </section>

      <PublicSharingSettings
        workspaceId={workspaceId}
        workspaceSlug={slug || initialSlug}
        isOwner={isOwner}
      />
    </>
  );
}
