"use client";

import * as Tabs from "@radix-ui/react-tabs";
import {
  AlertCircle,
  AlignLeft,
  FileText,
  Globe,
  Loader2,
  Upload,
  X,
} from "lucide-react";
import { useId, useRef, useState } from "react";

import { CreditLimitModal } from "@/components/CreditLimitModal";
import { ApiError, apiFetch } from "@/lib/api-client";

export type DropzoneProps = {
  workspaceId: string;
  onIngested?: (jobId: string, rawSourceId: string) => void;
  prefillTitle?: string;
  initialTab?: TabValue;
};

type IngestResponse = { job_id: string; raw_source_id: string };

type TabValue = "file" | "url" | "text";
type FileUploadStatus =
  "queued" | "uploading" | "duplicate" | "processing" | "completed" | "failed";

type FileUploadItem = {
  id: string;
  file: File;
  title: string;
  status: FileUploadStatus;
  errorMessage?: string;
};

// UI-SPEC Copywriting Contract(Dropzone(UI-03)) + D-07 — 문구를 한 글자도 바꾸지 않는다.
const ALREADY_INGESTED_MESSAGE = "이미 수집됨 — 건너뜀";
const BUDGET_EXCEEDED_MESSAGE =
  "이번 달 워크스페이스 사용량 한도를 초과했습니다. 관리자에게 문의하거나 다음 달까지 기다려주세요.";
const UNSUPPORTED_MIME_MESSAGE =
  "지원하지 않는 파일 형식입니다. 다른 파일로 다시 시도해주세요.";
const INVALID_URL_SCHEME_MESSAGE =
  "http:// 또는 https://로 시작하는 URL만 등록할 수 있습니다.";
const GENERIC_ERROR_MESSAGE =
  "소스 등록에 실패했습니다. 잠시 후 다시 시도해주세요.";

const FETCHABLE_SCHEMES = new Set(["http:", "https:"]);
const FILE_UPLOAD_CONCURRENCY = 3;

const FILE_STATUS_LABEL: Record<FileUploadStatus, string> = {
  queued: "대기 중",
  uploading: "업로드 중",
  duplicate: "이미 수집됨 — 건너뜀",
  processing: "처리 중",
  completed: "등록 완료",
  failed: "등록 실패",
};

function formatBytes(bytes?: number | null): string {
  if (bytes === null || bytes === undefined || bytes === 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function deriveFileTitle(filename: string): string {
  const extensionStart = filename.lastIndexOf(".");
  if (extensionStart <= 0) return filename;
  return filename.slice(0, extensionStart);
}

function createFileUploadItems(
  files: FileList | File[],
  nextId: () => number,
): FileUploadItem[] {
  return Array.from(files).map((file) => ({
    id: `${file.name}-${file.size}-${file.lastModified}-${nextId()}`,
    file,
    title: deriveFileTitle(file.name),
    status: "queued",
  }));
}

function mapIngestError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409 && error.detail === "already_ingested") {
      return ALREADY_INGESTED_MESSAGE;
    }
    if (error.status === 402 && error.detail === "budget_exceeded") {
      return BUDGET_EXCEEDED_MESSAGE;
    }
    if (
      error.status === 422 &&
      error.detail === "invalid_source" &&
      error.extra?.reason === "unsupported_mime"
    ) {
      return UNSUPPORTED_MIME_MESSAGE;
    }
  }
  return GENERIC_ERROR_MESSAGE;
}

export function Dropzone({
  workspaceId,
  onIngested,
  prefillTitle,
  initialTab,
}: DropzoneProps) {
  const [tab, setTab] = useState<TabValue>(initialTab ?? "file");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [creditLimitOpen, setCreditLimitOpen] = useState(false);

  const fileInputId = useId();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const nextFileId = useRef(0);
  const urlInputId = useId();
  const urlTitleId = useId();
  const textTitleId = useId();
  const textInputId = useId();

  const [fileUploadItems, setFileUploadItems] = useState<FileUploadItem[]>([]);
  const [url, setUrl] = useState("");
  const [urlTitle, setUrlTitle] = useState("");
  const [textTitle, setTextTitle] = useState(prefillTitle ?? "");
  const [text, setText] = useState("");

  function switchTab(value: string) {
    setTab(value as TabValue);
    setErrorMessage(null);
  }

  function addFiles(files: FileList | File[]) {
    setFileUploadItems((items) => [
      ...items,
      ...createFileUploadItems(files, () => nextFileId.current++),
    ]);
    setErrorMessage(null);
  }

  function updateFileUploadItem(
    id: string,
    update: Partial<Omit<FileUploadItem, "id" | "file">>,
  ) {
    setFileUploadItems((items) =>
      items.map((item) => (item.id === id ? { ...item, ...update } : item)),
    );
  }

  async function registerFile(item: FileUploadItem) {
    updateFileUploadItem(item.id, {
      status: "uploading",
      errorMessage: undefined,
    });

    try {
      const params = new URLSearchParams({
        filename: item.file.name,
        title: item.title,
      });
      const result = await apiFetch<IngestResponse>(
        `/workspaces/${workspaceId}/sources/file?${params.toString()}`,
        { method: "POST", body: item.file, contentType: item.file.type },
      );
      updateFileUploadItem(item.id, { status: "processing" });
      onIngested?.(result.job_id, result.raw_source_id);
      updateFileUploadItem(item.id, { status: "completed" });
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.status === 402 &&
        error.detail === "budget_exceeded"
      ) {
        setCreditLimitOpen(true);
      }
      const errorMessage = mapIngestError(error);
      updateFileUploadItem(item.id, {
        status:
          error instanceof ApiError &&
          error.status === 409 &&
          error.detail === "already_ingested"
            ? "duplicate"
            : "failed",
        errorMessage,
      });
    }
  }

  async function handleFileSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const queuedItems = fileUploadItems.filter(
      (item) => item.status === "queued",
    );
    if (queuedItems.length === 0 || submitting) return;

    setSubmitting(true);
    setErrorMessage(null);

    try {
      for (
        let index = 0;
        index < queuedItems.length;
        index += FILE_UPLOAD_CONCURRENCY
      ) {
        await Promise.all(
          queuedItems
            .slice(index, index + FILE_UPLOAD_CONCURRENCY)
            .map((item) => registerFile(item)),
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUrlSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedUrl = url.trim();
    if (trimmedUrl.length === 0 || submitting) return;

    setErrorMessage(null);

    let scheme: string | null = null;
    try {
      scheme = new URL(trimmedUrl).protocol;
    } catch {
      scheme = null;
    }
    if (scheme === null || !FETCHABLE_SCHEMES.has(scheme)) {
      setErrorMessage(INVALID_URL_SCHEME_MESSAGE);
      return;
    }

    setSubmitting(true);

    try {
      const trimmedTitle = urlTitle.trim();
      const result = await apiFetch<IngestResponse>(
        `/workspaces/${workspaceId}/sources/url`,
        {
          method: "POST",
          body: {
            url: trimmedUrl,
            title: trimmedTitle.length > 0 ? trimmedTitle : undefined,
          },
        },
      );
      onIngested?.(result.job_id, result.raw_source_id);
      setUrl("");
      setUrlTitle("");
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.status === 402 &&
        error.detail === "budget_exceeded"
      ) {
        setCreditLimitOpen(true);
      }
      setErrorMessage(mapIngestError(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTextSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      textTitle.trim().length === 0 ||
      text.trim().length === 0 ||
      submitting
    ) {
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);

    try {
      const result = await apiFetch<IngestResponse>(
        `/workspaces/${workspaceId}/sources/text`,
        { method: "POST", body: { title: textTitle.trim(), text } },
      );
      onIngested?.(result.job_id, result.raw_source_id);
      setTextTitle("");
      setText("");
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.status === 402 &&
        error.detail === "budget_exceeded"
      ) {
        setCreditLimitOpen(true);
      }
      setErrorMessage(mapIngestError(error));
    } finally {
      setSubmitting(false);
    }
  }

  const canSubmitFile = fileUploadItems.some(
    (item) => item.status === "queued",
  );
  const canSubmitUrl = url.trim().length > 0 && !submitting;
  const canSubmitText =
    textTitle.trim().length > 0 && text.trim().length > 0 && !submitting;

  return (
    <div className="flex flex-col gap-4">
      <Tabs.Root
        value={tab}
        onValueChange={switchTab}
        className="flex flex-col gap-4"
      >
        {/* 세그먼트 탭 헤더 */}
        <Tabs.List
          className="grid grid-cols-3 gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-1.5"
          aria-label="소스 등록 방식"
        >
          <Tabs.Trigger
            value="file"
            className="nw-focus-ring flex items-center justify-center gap-2 rounded-lg py-2.5 text-xs md:text-sm font-semibold transition-all data-[state=active]:bg-[var(--bg)] data-[state=active]:text-[var(--fg)] data-[state=active]:shadow-xs text-[var(--muted)] hover:text-[var(--fg)] cursor-pointer"
          >
            <FileText size={15} aria-hidden="true" />
            <span>파일</span>
          </Tabs.Trigger>
          <Tabs.Trigger
            value="url"
            className="nw-focus-ring flex items-center justify-center gap-2 rounded-lg py-2.5 text-xs md:text-sm font-semibold transition-all data-[state=active]:bg-[var(--bg)] data-[state=active]:text-[var(--fg)] data-[state=active]:shadow-xs text-[var(--muted)] hover:text-[var(--fg)] cursor-pointer"
          >
            <Globe size={15} aria-hidden="true" />
            <span>URL</span>
          </Tabs.Trigger>
          <Tabs.Trigger
            value="text"
            className="nw-focus-ring flex items-center justify-center gap-2 rounded-lg py-2.5 text-xs md:text-sm font-semibold transition-all data-[state=active]:bg-[var(--bg)] data-[state=active]:text-[var(--fg)] data-[state=active]:shadow-xs text-[var(--muted)] hover:text-[var(--fg)] cursor-pointer"
          >
            <AlignLeft size={15} aria-hidden="true" />
            <span>텍스트</span>
          </Tabs.Trigger>
        </Tabs.List>

        {/* 1. 파일 탭 */}
        <Tabs.Content
          value="file"
          className="flex flex-col gap-4 pt-1 outline-none"
        >
          <form onSubmit={handleFileSubmit} className="flex flex-col gap-4">
            <label
              htmlFor={fileInputId}
              tabIndex={0}
              onDragEnter={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                setIsDragging(false);
              }}
              onDragOver={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDrop={(event) => {
                event.preventDefault();
                setIsDragging(false);
                if (event.dataTransfer.files.length > 0) {
                  addFiles(event.dataTransfer.files);
                }
              }}
              onClick={(event) => {
                if (event.target === fileInputRef.current) return;
                event.preventDefault();
                fileInputRef.current?.click();
              }}
              onKeyDown={(event) => {
                if (event.key !== "Enter" && event.key !== " ") return;
                event.preventDefault();
                fileInputRef.current?.click();
              }}
              className={`group nw-focus-ring flex cursor-pointer flex-col items-center justify-center gap-3.5 rounded-2xl border-2 border-dashed p-8 md:p-12 text-center transition-all ${
                isDragging
                  ? "border-[var(--accent)] bg-[var(--soft)] ring-4 ring-[var(--accent)]/10 scale-[1.01]"
                  : "border-[var(--border)] bg-[var(--surface)]/30 hover:border-[var(--accent)]/70 hover:bg-[var(--soft)]/30"
              }`}
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--bg)] text-[var(--accent)] shadow-xs transition-transform group-hover:scale-105">
                <Upload size={24} aria-hidden="true" />
              </div>
              <div>
                <span className="block text-sm md:text-base font-semibold text-[var(--fg)]">
                  파일을 드래그하거나 클릭해서 선택하세요
                </span>
                <span className="mt-1.5 block text-xs text-[var(--muted)]">
                  PDF, Markdown (.md), TXT 파일 지원 (다중 선택 가능)
                </span>
              </div>
              <input
                id={fileInputId}
                ref={fileInputRef}
                type="file"
                multiple
                aria-label="파일 선택"
                onChange={(event) => {
                  if (event.target.files) addFiles(event.target.files);
                  event.target.value = "";
                }}
                className="sr-only"
              />
            </label>

            {fileUploadItems.length > 0 ? (
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between px-1 text-xs font-semibold text-[var(--muted)]">
                  <span>선택된 파일 ({fileUploadItems.length})</span>
                  {fileUploadItems.some((item) => item.status === "queued") && (
                    <button
                      type="button"
                      onClick={() => setFileUploadItems([])}
                      className="text-[11px] text-[var(--muted)] hover:text-[var(--danger)] transition-colors cursor-pointer"
                    >
                      전체 비우기
                    </button>
                  )}
                </div>
                <ul
                  aria-label="선택한 파일"
                  className="max-h-44 overflow-y-auto space-y-1.5 rounded-xl border border-[var(--border)] bg-[var(--surface)]/50 p-2"
                >
                  {fileUploadItems.map((item) => {
                    const ext = item.file.name.split(".").pop()?.toLowerCase();
                    const formatBadgeClass =
                      ext === "pdf"
                        ? "format pdf"
                        : ext === "md"
                          ? "format md"
                          : "format txt";
                    const formatLabel =
                      ext === "pdf" ? "PDF" : ext === "md" ? "MD" : "TXT";

                    return (
                      <li
                        key={item.id}
                        className="flex items-center justify-between gap-3 rounded-lg border border-[var(--border)] bg-[var(--bg)] p-2.5 shadow-2xs"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span
                            className={`${formatBadgeClass} scale-90 origin-left`}
                          >
                            {formatLabel}
                          </span>
                          <div className="min-w-0">
                            <span className="block truncate text-xs font-medium text-[var(--fg)]">
                              {item.file.name}
                            </span>
                            <span className="block text-[10px] text-[var(--muted)] font-mono">
                              {formatBytes(item.file.size)}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <span
                            className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold ${
                              item.status === "completed"
                                ? "bg-[var(--good)]/10 text-[var(--good)]"
                                : item.status === "uploading" ||
                                    item.status === "processing"
                                  ? "bg-[var(--accent)]/10 text-[var(--accent)] animate-pulse"
                                  : item.status === "failed" ||
                                      item.status === "duplicate"
                                    ? "bg-[var(--danger)]/10 text-[var(--danger)]"
                                    : "bg-[var(--surface)] text-[var(--muted)] border border-[var(--border)]"
                            }`}
                          >
                            {item.errorMessage ??
                              FILE_STATUS_LABEL[item.status]}
                          </span>
                          {item.status === "queued" && (
                            <button
                              type="button"
                              onClick={() =>
                                setFileUploadItems((items) =>
                                  items.filter((i) => i.id !== item.id),
                                )
                              }
                              className="rounded p-1 text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--danger)] transition-colors cursor-pointer"
                              aria-label={`${item.file.name} 제외`}
                            >
                              <X size={13} aria-hidden="true" />
                            </button>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : null}

            <button
              type="submit"
              disabled={!canSubmitFile || submitting}
              className={`nw-action nw-focus-ring flex h-11 w-full items-center justify-center gap-2 rounded-xl text-sm font-semibold transition-all cursor-pointer ${
                canSubmitFile && !submitting
                  ? "bg-[var(--accent)] text-white shadow-xs hover:brightness-105 active:scale-[0.99]"
                  : "bg-[var(--surface)] text-[var(--muted)] border border-[var(--border)] opacity-60 cursor-not-allowed"
              }`}
            >
              {submitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>등록 처리 중…</span>
                </>
              ) : (
                <span>소스 등록</span>
              )}
            </button>
          </form>
        </Tabs.Content>

        {/* 2. URL 탭 */}
        <Tabs.Content
          value="url"
          className="flex flex-col gap-4 pt-1 outline-none"
        >
          <form onSubmit={handleUrlSubmit} className="flex flex-col gap-3.5">
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor={urlInputId}
                className="text-xs font-semibold text-[var(--fg)]"
              >
                URL 주소
              </label>
              <input
                id={urlInputId}
                type="url"
                placeholder="https://example.com/docs/spec"
                value={url}
                onChange={(event) => {
                  setUrl(event.target.value);
                  setErrorMessage(null);
                }}
                className="nw-input h-10 w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3.5 text-xs text-[var(--fg)] placeholder:text-[var(--muted)]/60 outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/15 transition-all"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor={urlTitleId}
                className="text-xs font-semibold text-[var(--fg)]"
              >
                제목 (선택)
              </label>
              <input
                id={urlTitleId}
                placeholder="문서 제목을 직접 입력 (미입력 시 웹페이지 타이틀 자동 추출)"
                value={urlTitle}
                onChange={(event) => setUrlTitle(event.target.value)}
                className="nw-input h-10 w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3.5 text-xs text-[var(--fg)] placeholder:text-[var(--muted)]/60 outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/15 transition-all"
              />
            </div>
            <button
              type="submit"
              disabled={!canSubmitUrl}
              className={`nw-action nw-focus-ring mt-1 flex h-11 w-full items-center justify-center gap-2 rounded-xl text-sm font-semibold transition-all cursor-pointer ${
                canSubmitUrl
                  ? "bg-[var(--accent)] text-white shadow-xs hover:brightness-105 active:scale-[0.99]"
                  : "bg-[var(--surface)] text-[var(--muted)] border border-[var(--border)] opacity-60 cursor-not-allowed"
              }`}
            >
              {submitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>등록 처리 중…</span>
                </>
              ) : (
                <span>소스 등록</span>
              )}
            </button>
          </form>
        </Tabs.Content>

        {/* 3. 텍스트 탭 */}
        <Tabs.Content
          value="text"
          className="flex flex-col gap-4 pt-1 outline-none"
        >
          <form onSubmit={handleTextSubmit} className="flex flex-col gap-3.5">
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor={textTitleId}
                className="text-xs font-semibold text-[var(--fg)]"
              >
                제목
              </label>
              <input
                id={textTitleId}
                placeholder="문서 또는 메모 제목"
                value={textTitle}
                onChange={(event) => setTextTitle(event.target.value)}
                className="nw-input h-10 w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3.5 text-xs text-[var(--fg)] placeholder:text-[var(--muted)]/60 outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/15 transition-all"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <label
                  htmlFor={textInputId}
                  className="text-xs font-semibold text-[var(--fg)]"
                >
                  내용
                </label>
                <span className="text-[11px] font-mono text-[var(--muted)]">
                  {text.length.toLocaleString("ko-KR")}자
                </span>
              </div>
              <textarea
                id={textInputId}
                placeholder="본문 내용을 입력하거나 마크다운을 붙여넣으세요…"
                value={text}
                onChange={(event) => setText(event.target.value)}
                rows={6}
                className="nw-input w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3 text-xs leading-relaxed text-[var(--fg)] placeholder:text-[var(--muted)]/60 outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/15 transition-all font-mono resize-y"
              />
            </div>
            <button
              type="submit"
              disabled={!canSubmitText}
              className={`nw-action nw-focus-ring mt-1 flex h-11 w-full items-center justify-center gap-2 rounded-xl text-sm font-semibold transition-all cursor-pointer ${
                canSubmitText
                  ? "bg-[var(--accent)] text-white shadow-xs hover:brightness-105 active:scale-[0.99]"
                  : "bg-[var(--surface)] text-[var(--muted)] border border-[var(--border)] opacity-60 cursor-not-allowed"
              }`}
            >
              {submitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>등록 처리 중…</span>
                </>
              ) : (
                <span>소스 등록</span>
              )}
            </button>
          </form>
        </Tabs.Content>
      </Tabs.Root>

      {/* 에러 피드백 배너 */}
      {errorMessage !== null ? (
        <div
          role="alert"
          data-testid="dropzone-error-banner"
          className="flex items-start justify-between gap-2.5 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/5 p-3 text-xs font-medium text-[var(--danger)] leading-snug"
        >
          <div className="flex items-start gap-2.5">
            <AlertCircle
              size={15}
              className="shrink-0 mt-0.5"
              aria-hidden="true"
            />
            <span>{errorMessage}</span>
          </div>
          {errorMessage === BUDGET_EXCEEDED_MESSAGE && (
            <button
              type="button"
              onClick={() => setCreditLimitOpen(true)}
              className="underline font-semibold shrink-0 cursor-pointer hover:opacity-80 ml-2"
            >
              사용량 확인
            </button>
          )}
        </div>
      ) : null}

      <CreditLimitModal
        open={creditLimitOpen}
        onOpenChange={setCreditLimitOpen}
        workspaceId={workspaceId}
      />
    </div>
  );
}
