"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Loader2, User, Users } from "lucide-react";

import { createClient } from "@/lib/supabase/client";
import { PublicSharingSettings } from "@/components/PublicSharingSettings";

export type WorkspaceGeneralSettingsProps = {
  workspaceId: string;
  initialName: string;
  initialSlug: string;
  initialKind?: "personal" | "team";
  onKindChange?: (kind: "personal" | "team") => void;
  isOwner: boolean;
  allowPublicSharing?: boolean;
  publicDisplayName?: string;
  publicDescription?: string;
};

const SLUG_REGEX = /^[0-9a-z가-힣][0-9a-z가-힣-]*$/;

export function WorkspaceGeneralSettings({
  workspaceId,
  initialName,
  initialSlug,
  initialKind = "personal",
  onKindChange,
  isOwner,
  allowPublicSharing = false,
  publicDisplayName = "",
  publicDescription = "",
}: WorkspaceGeneralSettingsProps) {
  const router = useRouter();
  const [name, setName] = useState(initialName);
  const [slug, setSlug] = useState(initialSlug);
  const [kind, setKind] = useState<"personal" | "team">(initialKind);
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

    // 팀 -> 개인 전환 시 다른 멤버가 참여 중인지 검증 (멤버가 있으면 전환 불가)
    if (kind === "personal") {
      const { count, error: countError } = await supabase
        .from("workspace_members")
        .select("*", { count: "exact", head: true })
        .eq("workspace_id", workspaceId);

      if (!countError && typeof count === "number" && count > 1) {
        setSaving(false);
        setErrorMessage(
          `다른 멤버(${count - 1}명)가 참여 중인 워크스페이스는 개인 워크스페이스로 전환할 수 없습니다. 먼저 [멤버] 탭에서 다른 멤버를 모두 내보낸 후 다시 시도하세요.`,
        );
        return;
      }
    }

    // RLS USING 에 막힌 UPDATE 는 예외가 아니라 0행이다 — .select() 로 되받은
    // 행 수를 확인해야 "차단됨"과 "성공"이 구분된다(CLAUDE.md 불변 규칙).
    const { data, error } = await supabase
      .from("workspaces")
      .update({ name: trimmedName, slug: trimmedSlug, kind })
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
    onKindChange?.(kind);
    router.refresh();
  }

  return (
    <>
      <div className="section-head">
        <div>
          <h2>기본 정보</h2>
          <p>워크스페이스 이름과 식별용 슬러그, 협업 유형을 관리합니다.</p>
        </div>
      </div>

      {!isOwner && (
        <div role="note" className="role-note">
          소유자(Owner)만 워크스페이스 설정을 변경할 수 있습니다.
        </div>
      )}

      <section className="settings-card" aria-label="기본 설정">
        <h3>워크스페이스 식별 및 유형</h3>
        <p>
          슬러그는 공개 URL 과 공유 링크의 식별자로 쓰이며, 유형에 따라 멤버
          초대 기능이 활성화됩니다.
        </p>

        <form onSubmit={handleSubmit} className="settings-form">
          {/* 워크스페이스 유형 선택 (개인 / 팀) */}
          <div className="settings-field">
            <label id="workspace-kind-label">워크스페이스 유형</label>
            <div
              role="radiogroup"
              aria-labelledby="workspace-kind-label"
              className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-1.5"
            >
              {/* 개인 카드 */}
              <button
                type="button"
                role="radio"
                aria-checked={kind === "personal"}
                disabled={!isOwner || saving}
                onClick={() => {
                  if (!isOwner || saving) return;
                  setKind("personal");
                  setErrorMessage(null);
                  setSuccessMessage(null);
                }}
                className={`flex items-start gap-3 p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                  kind === "personal"
                    ? "border-[var(--accent)] bg-[var(--accent)]/5 ring-1 ring-[var(--accent)]"
                    : "border-[var(--border)] bg-[var(--bg)] hover:bg-[var(--surface)]/60 hover:border-[var(--border-strong)]"
                } ${!isOwner ? "opacity-60 cursor-not-allowed" : ""}`}
              >
                <div
                  className={`p-2 rounded-lg flex-none mt-0.5 ${
                    kind === "personal"
                      ? "bg-[var(--accent)] text-white"
                      : "bg-[var(--surface)] text-[var(--muted)]"
                  }`}
                >
                  <User size={16} aria-hidden="true" />
                </div>
                <div className="min-w-0 flex-1">
                  <span className="block text-xs font-bold text-[var(--fg)]">
                    개인 워크스페이스
                  </span>
                  <span className="block text-[11px] text-[var(--muted)] leading-relaxed mt-0.5">
                    혼자 지식을 정리하는 프라이빗 공간입니다. (멤버 초대
                    비활성화)
                  </span>
                </div>
              </button>

              {/* 팀 카드 */}
              <button
                type="button"
                role="radio"
                aria-checked={kind === "team"}
                disabled={!isOwner || saving}
                onClick={() => {
                  if (!isOwner || saving) return;
                  setKind("team");
                  setErrorMessage(null);
                  setSuccessMessage(null);
                }}
                className={`flex items-start gap-3 p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                  kind === "team"
                    ? "border-[var(--accent)] bg-[var(--accent)]/5 ring-1 ring-[var(--accent)]"
                    : "border-[var(--border)] bg-[var(--bg)] hover:bg-[var(--surface)]/60 hover:border-[var(--border-strong)]"
                } ${!isOwner ? "opacity-60 cursor-not-allowed" : ""}`}
              >
                <div
                  className={`p-2 rounded-lg flex-none mt-0.5 ${
                    kind === "team"
                      ? "bg-[var(--accent)] text-white"
                      : "bg-[var(--surface)] text-[var(--muted)]"
                  }`}
                >
                  <Users size={16} aria-hidden="true" />
                </div>
                <div className="min-w-0 flex-1">
                  <span className="block text-xs font-bold text-[var(--fg)]">
                    팀 워크스페이스
                  </span>
                  <span className="block text-[11px] text-[var(--muted)] leading-relaxed mt-0.5">
                    동료들과 소스를 공유하고 위키를 함께 구축하는 협업
                    공간입니다. (멤버 초대 지원)
                  </span>
                </div>
              </button>
            </div>
          </div>

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
        initialAllowPublicSharing={allowPublicSharing}
        initialDisplayName={publicDisplayName}
        initialDescription={publicDescription}
      />
    </>
  );
}
