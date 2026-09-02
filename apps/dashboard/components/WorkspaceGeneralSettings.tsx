"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  AlertTriangle,
  ExternalLink,
  KeyRound,
  Loader2,
  Trash2,
  User,
  Users,
  X,
  Zap,
} from "lucide-react";

import { createClient } from "@/lib/supabase/client";
import { PublicSharingSettings } from "@/components/PublicSharingSettings";

export type WorkspaceGeneralSettingsProps = {
  workspaceId: string;
  initialName: string;
  initialSlug: string;
  initialKind?: "personal" | "team";
  initialCustomApiKey?: string | null;
  onKindChange?: (kind: "personal" | "team") => void;
  isOwner: boolean;
  allowPublicSharing?: boolean;
  publicDisplayName?: string;
  publicDescription?: string;
};

const SLUG_REGEX = /^[0-9a-z가-힣][0-9a-z가-힣-]*$/;

function maskApiKey(key: string): string {
  if (!key) return "";
  if (key.length <= 10) return "••••••••";
  const prefix = key.slice(0, 8);
  const suffix = key.slice(-4);
  return `${prefix}••••••••${suffix}`;
}

export function WorkspaceGeneralSettings({
  workspaceId,
  initialName,
  initialSlug,
  initialKind = "personal",
  initialCustomApiKey = null,
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

  // BYOK (Bring Your Own Key) 상태
  const [customApiKey, setCustomApiKey] = useState(initialCustomApiKey ?? "");
  const [isEditingKey, setIsEditingKey] = useState(false);
  const [inputKey, setInputKey] = useState("");
  const [keySaving, setKeySaving] = useState(false);
  const [keyError, setKeyError] = useState<string | null>(null);
  const [keySuccess, setKeySuccess] = useState<string | null>(null);

  // 워크스페이스 삭제 상태
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [confirmInput, setConfirmInput] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

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

  async function handleDeleteWorkspace() {
    if (!isOwner || deleting || confirmInput !== initialName) return;

    setDeleting(true);
    setDeleteError(null);

    const supabase = createClient();

    // 1. DELETE 호출
    const { data, error } = await supabase
      .from("workspaces")
      .delete()
      .eq("id", workspaceId)
      .select();

    if (error || !data || data.length === 0) {
      setDeleting(false);
      setDeleteError(error?.message || "워크스페이스를 삭제하지 못했습니다.");
      return;
    }

    // 2. 삭제 성공 후 남아 있는 다른 워크스페이스 조회
    const { data: remainingMemberships } = await supabase
      .from("workspace_members")
      .select("workspace_id")
      .neq("workspace_id", workspaceId)
      .limit(1);

    setDeleting(false);
    setDeleteModalOpen(false);

    if (remainingMemberships && remainingMemberships.length > 0) {
      const nextWorkspaceId = remainingMemberships[0].workspace_id;
      router.push(`/w/${nextWorkspaceId}`);
    } else {
      router.push("/onboarding");
    }
  }

  async function handleSaveApiKey() {
    if (!isOwner || keySaving) return;
    const trimmed = inputKey.trim();
    if (!trimmed) {
      setKeyError("API 키를 입력해주세요.");
      return;
    }
    if (trimmed.length < 20 || trimmed.length > 500) {
      setKeyError("올바른 API 키 형식이 아닙니다 (20자 이상 500자 이하).");
      return;
    }

    setKeySaving(true);
    setKeyError(null);
    setKeySuccess(null);

    const supabase = createClient();
    const { data, error } = await supabase
      .from("workspaces")
      .update({ custom_api_key: trimmed })
      .eq("id", workspaceId)
      .select();

    setKeySaving(false);
    if (error || !data || data.length === 0) {
      setKeyError(error?.message || "API 키를 저장하지 못했습니다.");
      return;
    }

    setCustomApiKey(trimmed);
    setInputKey("");
    setIsEditingKey(false);
    setKeySuccess(
      "내 API 키가 등록되었습니다! 이제 크레딧 차감 없이 무제한으로 이용할 수 있습니다.",
    );
    router.refresh();
  }

  async function handleDeleteApiKey() {
    if (!isOwner || keySaving) return;
    setKeySaving(true);
    setKeyError(null);
    setKeySuccess(null);

    const supabase = createClient();
    const { data, error } = await supabase
      .from("workspaces")
      .update({ custom_api_key: null })
      .eq("id", workspaceId)
      .select();

    setKeySaving(false);
    if (error || !data || data.length === 0) {
      setKeyError(error?.message || "API 키를 삭제하지 못했습니다.");
      return;
    }

    setCustomApiKey("");
    setIsEditingKey(false);
    setKeySuccess(
      "API 키가 삭제되었습니다. 기본 무료 크레딧 쿼터로 전환되었습니다.",
    );
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

      {/* AI 모델 및 커스텀 API 키 (BYOK) */}
      <section
        className="settings-card mt-6"
        aria-label="AI 모델 및 API 키 설정"
        data-od-id="byok-settings-card"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent)]/10 text-[var(--accent)] flex-none">
              <KeyRound size={20} aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[var(--fg)]">
                AI 모델 및 커스텀 API 키 (BYOK)
              </h3>
              <p className="text-xs text-[var(--muted)] mt-0.5">
                개인 OpenRouter / OpenAI API 키를 등록하면 월간 크레딧 차감 없이
                무제한으로 이용할 수 있습니다.
              </p>
            </div>
          </div>
          {customApiKey && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-[var(--accent)]/15 text-[var(--accent)] border border-[var(--accent)]/30 flex-none">
              <Zap size={12} aria-hidden="true" />
              <span>무제한 활성화됨</span>
            </span>
          )}
        </div>

        <div className="mt-4 pt-4 border-t border-[var(--border)]">
          {customApiKey && !isEditingKey ? (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl bg-[var(--surface-subtle)]/60 border border-[var(--border)]">
              <div>
                <span className="block text-[11px] font-semibold text-[var(--muted)]">
                  연결된 OpenRouter API 키
                </span>
                <span className="block font-mono text-xs text-[var(--fg)] mt-0.5 font-medium">
                  {maskApiKey(customApiKey)}
                </span>
              </div>
              {isOwner && (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    aria-label="API 키 변경"
                    onClick={() => {
                      setInputKey("");
                      setKeyError(null);
                      setKeySuccess(null);
                      setIsEditingKey(true);
                    }}
                    className="button compact"
                  >
                    키 변경
                  </button>
                  <button
                    type="button"
                    aria-label="API 키 삭제"
                    disabled={keySaving}
                    onClick={handleDeleteApiKey}
                    className="button compact danger"
                  >
                    {keySaving ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      "삭제"
                    )}
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label
                  htmlFor="custom-api-key-input"
                  className="block text-xs font-semibold text-[var(--fg)] mb-1.5"
                >
                  OpenRouter API 키 등록
                </label>
                <div className="flex gap-2">
                  <input
                    id="custom-api-key-input"
                    type="password"
                    disabled={!isOwner || keySaving}
                    value={inputKey}
                    onChange={(e) => setInputKey(e.target.value)}
                    placeholder="sk-or-v1-..."
                    className="field flex-1 font-mono text-xs"
                    autoComplete="off"
                  />
                  {isEditingKey && (
                    <button
                      type="button"
                      disabled={keySaving}
                      onClick={() => {
                        setIsEditingKey(false);
                        setInputKey("");
                        setKeyError(null);
                      }}
                      className="button compact"
                    >
                      취소
                    </button>
                  )}
                  <button
                    type="button"
                    aria-label="API 키 저장"
                    disabled={!isOwner || keySaving || !inputKey.trim()}
                    onClick={handleSaveApiKey}
                    className="button compact primary disabled:opacity-50"
                  >
                    {keySaving && (
                      <Loader2 size={13} className="animate-spin" />
                    )}
                    <span>API 키 저장</span>
                  </button>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[11px] text-[var(--muted)]">
                <span>
                  {!isOwner
                    ? "소유자(Owner)만 API 키를 등록하거나 수정할 수 있습니다."
                    : "입력된 키는 안전하게 암호화되어 해당 워크스페이스에서만 사용됩니다."}
                </span>
                <a
                  href="https://openrouter.ai/keys"
                  target="_blank"
                  rel="noreferrer"
                  className="text-[var(--accent)] hover:underline inline-flex items-center gap-1 font-medium"
                >
                  <span>OpenRouter 키 발급받기</span>
                  <ExternalLink size={11} aria-hidden="true" />
                </a>
              </div>
            </div>
          )}

          {keyError && (
            <p
              role="alert"
              className="invite-feedback error show mt-3 text-xs text-[var(--danger)]"
            >
              {keyError}
            </p>
          )}
          {keySuccess && (
            <p
              role="status"
              className="invite-feedback success show mt-3 text-xs text-[var(--success)]"
            >
              {keySuccess}
            </p>
          )}
        </div>
      </section>

      <PublicSharingSettings
        workspaceId={workspaceId}
        workspaceSlug={slug || initialSlug}
        isOwner={isOwner}
        initialAllowPublicSharing={allowPublicSharing}
        initialDisplayName={publicDisplayName}
        initialDescription={publicDescription}
      />

      {/* 위험 구역 (Danger Zone) */}
      <section
        className="settings-card border-[var(--danger)]/30 bg-[var(--danger)]/5 mt-8"
        aria-label="위험 구역"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-sm font-bold text-[var(--danger)] flex items-center gap-1.5">
              <AlertTriangle size={16} aria-hidden="true" />
              <span>위험 구역</span>
            </h3>
            <p className="mt-1 text-xs text-[var(--muted)]">
              워크스페이스를 삭제하면 등록된 모든 원문 소스, 위키 문서, 인덱싱
              청크 및 질문 내역이 영구적으로 제거됩니다.
            </p>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-[var(--danger)]/15 flex items-center justify-between gap-4">
          <div>
            <b className="block text-xs font-semibold text-[var(--fg)]">
              워크스페이스 삭제
            </b>
            <span className="block text-[11px] text-[var(--muted)] mt-0.5">
              {!isOwner
                ? "소유자(Owner)만 워크스페이스를 삭제할 수 있습니다."
                : "이 작업은 되돌릴 수 없습니다."}
            </span>
          </div>

          <button
            type="button"
            disabled={!isOwner}
            onClick={() => {
              setConfirmInput("");
              setDeleteError(null);
              setDeleteModalOpen(true);
            }}
            className="button compact danger whitespace-nowrap cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Trash2 size={13} aria-hidden="true" />
            <span>워크스페이스 삭제</span>
          </button>
        </div>
      </section>

      {/* 워크스페이스 삭제 확인 모달 */}
      <Dialog.Root open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md transition-all duration-200" />
          <Dialog.Content className="fixed top-1/2 left-1/2 z-50 w-[min(480px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-6 shadow-2xl outline-none">
            <div className="modal-head mb-4 flex items-start justify-between gap-4">
              <div>
                <Dialog.Title className="text-base font-bold text-[var(--danger)] flex items-center gap-1.5">
                  <AlertTriangle size={18} aria-hidden="true" />
                  <span>워크스페이스 삭제 확인</span>
                </Dialog.Title>
                <Dialog.Description className="mt-1.5 text-xs text-[var(--muted)] leading-relaxed">
                  이 작업은 절대 되돌릴 수 없습니다.{" "}
                  <b>&lsquo;{initialName}&rsquo;</b> 워크스페이스와 연관된 모든
                  원문 자료, 위키 문서, 대화 기록이 즉시 영구 삭제됩니다.
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="icon-btn rounded-lg p-1 text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--fg)] transition-colors cursor-pointer"
                  aria-label="닫기"
                >
                  <X size={16} aria-hidden="true" />
                </button>
              </Dialog.Close>
            </div>

            <div className="space-y-3 mt-4">
              <label
                htmlFor="confirm-workspace-name-input"
                className="block text-xs font-semibold text-[var(--fg)]"
              >
                확인을 위해 워크스페이스 이름(<b>{initialName}</b>)을 정확히
                입력하세요:
              </label>
              <input
                id="confirm-workspace-name-input"
                type="text"
                value={confirmInput}
                onChange={(e) => setConfirmInput(e.target.value)}
                placeholder={initialName}
                disabled={deleting}
                className="field"
                autoComplete="off"
              />
            </div>

            {deleteError && (
              <p role="alert" className="invite-feedback error show mt-3">
                {deleteError}
              </p>
            )}

            <div className="modal-foot flex items-center justify-end gap-2 mt-6">
              <Dialog.Close asChild>
                <button
                  type="button"
                  disabled={deleting}
                  className="button compact"
                >
                  취소
                </button>
              </Dialog.Close>
              <button
                type="button"
                disabled={deleting || confirmInput !== initialName}
                onClick={handleDeleteWorkspace}
                className="button compact danger disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {deleting && <Loader2 size={13} className="animate-spin" />}
                <span>영구 삭제</span>
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
