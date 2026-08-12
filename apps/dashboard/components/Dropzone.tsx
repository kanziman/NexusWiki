"use client";

import * as Tabs from "@radix-ui/react-tabs";
import { Upload } from "lucide-react";
import { useId, useState } from "react";

import { ApiError, apiFetch } from "@/lib/api-client";

export type DropzoneProps = {
  workspaceId: string;
  onIngested?: (jobId: string, rawSourceId: string) => void;
  // RedLinkCta.handleCreate → sources/page.tsx → SourcesList가 이어 넘기는
  // prefill 값 — 06-REVIEW.md CR-01: 이전에는 이 두 prop이 없어 빨간 링크
  // CTA의 "지금 생성" 클릭이 빈 File 탭으로만 이동했다. 마운트 시 텍스트
  // 탭의 제목 필드와 활성 탭을 시드한다.
  prefillTitle?: string;
  initialTab?: TabValue;
};

type IngestResponse = { job_id: string; raw_source_id: string };

type TabValue = "file" | "url" | "text";

// UI-SPEC Copywriting Contract(Dropzone(UI-03)) + D-07 — 문구를 한 글자도 바꾸지 않는다.
const ALREADY_INGESTED_MESSAGE = "이미 수집됨 — 건너뜀";
const BUDGET_EXCEEDED_MESSAGE =
  "이번 달 워크스페이스 사용량 한도를 초과했습니다. 관리자에게 문의하거나 다음 달까지 기다려주세요.";
// sources.py의 unsupported_mime은 받은 Content-Type을 응답에 되비추지 않는다
// (T-03-34 반사형 노출 회피) — 여기서도 원본 MIME 문자열을 화면에 노출하지 않는다.
const UNSUPPORTED_MIME_MESSAGE =
  "지원하지 않는 파일 형식입니다. 다른 파일로 다시 시도해주세요.";
const INVALID_URL_SCHEME_MESSAGE =
  "http:// 또는 https://로 시작하는 URL만 등록할 수 있습니다.";
const GENERIC_ERROR_MESSAGE =
  "소스 등록에 실패했습니다. 잠시 후 다시 시도해주세요.";

// sources.py의 _assert_fetchable_url과 같은 허용 스킴 — 서버가 최종 판정자이고
// 이 사전 검사는 요청을 아예 보내지 않기 위한 UX 편의일 뿐이다 (T-03-* SSRF는
// 워커 접속 시점 판정, 여기서는 재현하지 않는다).
const FETCHABLE_SCHEMES = new Set(["http:", "https:"]);

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
  // 문서화되지 않은 나머지(네트워크 실패, 5xx 등)는 일반 재시도 안내로 뭉갠다 —
  // Task 1 <action> "anything else ... renders a generic retry-later message".
  return GENERIC_ERROR_MESSAGE;
}

/**
 * 소스 드롭존 — 파일/URL/텍스트 3개 탭을 하나의 컴포넌트로 통합한다 (D-06).
 *
 * 관련 태스크: 06-05-PLAN.md Task 1
 * 설계 근거: apps/api/src/api/routers/sources.py (세 경로의 정확한 요청 형태),
 *            06-UI-SPEC.md Copywriting Contract "Dropzone (UI-03)"
 *
 * ⚠️ 파일 탭은 FormData/multipart를 절대 쓰지 않는다 — sources.py의 파일 엔드포인트는
 * 원시 바이트 본문을 받는다(D-P11). apiFetch의 `contentType` 이스케이프 해치로 파일
 * 자신의 MIME을 Content-Type으로 실어 보낸다.
 */
export function Dropzone({
  workspaceId,
  onIngested,
  prefillTitle,
  initialTab,
}: DropzoneProps) {
  const [tab, setTab] = useState<TabValue>(initialTab ?? "file");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fileTitleId = useId();
  const fileInputId = useId();
  const urlInputId = useId();
  const urlTitleId = useId();
  const textTitleId = useId();
  const textInputId = useId();

  const [fileTitle, setFileTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [url, setUrl] = useState("");
  const [urlTitle, setUrlTitle] = useState("");

  const [textTitle, setTextTitle] = useState(prefillTitle ?? "");
  const [text, setText] = useState("");

  function switchTab(value: string) {
    setTab(value as TabValue);
    setErrorMessage(null);
  }

  async function handleFileSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile || fileTitle.trim().length === 0 || submitting) return;

    setSubmitting(true);
    setErrorMessage(null);

    try {
      // 파일 자신의 바이트를 그대로 본문으로 보낸다 — FormData로 감싸지 않는다.
      const params = new URLSearchParams({
        filename: selectedFile.name,
        title: fileTitle,
      });
      const result = await apiFetch<IngestResponse>(
        `/workspaces/${workspaceId}/sources/file?${params.toString()}`,
        { method: "POST", body: selectedFile, contentType: selectedFile.type },
      );
      onIngested?.(result.job_id, result.raw_source_id);
      setSelectedFile(null);
      setFileTitle("");
    } catch (error) {
      setErrorMessage(mapIngestError(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUrlSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedUrl = url.trim();
    if (trimmedUrl.length === 0 || submitting) return;

    setErrorMessage(null);

    // D-06 URL 탭의 클라이언트 사전 검사 — http(s) 외 스킴은 요청을 보내기 전에
    // 인라인 에러로 거부한다 (요청 자체를 만들지 않는다).
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
      setErrorMessage(mapIngestError(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTextSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // 백엔드 TextSourceRequest의 min_length=1과 맞춘다 — 빈 본문은 제출 자체가
    // 비활성화된다 (요청을 보내지 않는다).
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
      setErrorMessage(mapIngestError(error));
    } finally {
      setSubmitting(false);
    }
  }

  const canSubmitFile = selectedFile !== null && fileTitle.trim().length > 0;
  const canSubmitUrl = url.trim().length > 0 && !submitting;
  const canSubmitText =
    textTitle.trim().length > 0 && text.trim().length > 0 && !submitting;

  return (
    <div className="flex flex-col gap-base rounded-md bg-surface-soft p-lg">
      <Tabs.Root value={tab} onValueChange={switchTab}>
        <Tabs.List
          className="flex gap-sm border-b border-hairline"
          aria-label="소스 등록 방식"
        >
          <Tabs.Trigger
            value="file"
            className="px-base py-sm text-ink data-[state=active]:text-primary"
            style={{ font: "var(--font-caption)" }}
          >
            파일
          </Tabs.Trigger>
          <Tabs.Trigger
            value="url"
            className="px-base py-sm text-ink data-[state=active]:text-primary"
            style={{ font: "var(--font-caption)" }}
          >
            URL
          </Tabs.Trigger>
          <Tabs.Trigger
            value="text"
            className="px-base py-sm text-ink data-[state=active]:text-primary"
            style={{ font: "var(--font-caption)" }}
          >
            텍스트
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="file" className="flex flex-col gap-base pt-base">
          <form onSubmit={handleFileSubmit} className="flex flex-col gap-base">
            <div className="flex flex-col gap-xs">
              <label
                htmlFor={fileTitleId}
                className="text-ink"
                style={{ font: "var(--font-caption)" }}
              >
                제목
              </label>
              <input
                id={fileTitleId}
                value={fileTitle}
                onChange={(event) => setFileTitle(event.target.value)}
                className="h-12 rounded-sm border border-border-strong bg-canvas px-base text-ink outline-none focus:border-2 focus:border-ink"
                style={{ font: "var(--font-body-md)" }}
              />
            </div>

            <div
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                const file = event.dataTransfer.files?.[0];
                if (file) setSelectedFile(file);
              }}
              className="flex flex-col items-center gap-xs rounded-sm border border-dashed border-border-strong p-lg text-center"
            >
              <Upload size={24} aria-hidden="true" className="text-muted" />
              <span
                className="text-ink"
                style={{ font: "var(--font-body-md)" }}
              >
                {selectedFile
                  ? selectedFile.name
                  : "파일을 드래그하거나 클릭해서 선택하세요"}
              </span>
              <label htmlFor={fileInputId} className="sr-only">
                파일 선택
              </label>
              <input
                id={fileInputId}
                type="file"
                onChange={(event) =>
                  setSelectedFile(event.target.files?.[0] ?? null)
                }
                className="sr-only"
              />
            </div>

            {/* UI-SPEC Primary Visual Anchor(Dropzone, pre-submit): 이 버튼만
                accent(--color-primary)를 쓴다. */}
            <button
              type="submit"
              disabled={!canSubmitFile || submitting}
              className="h-12 self-start rounded-sm bg-primary px-lg text-on-primary transition-colors active:bg-primary-active disabled:cursor-not-allowed disabled:bg-primary-disabled"
              style={{ font: "var(--font-button-md)" }}
            >
              소스 등록
            </button>
          </form>
        </Tabs.Content>

        <Tabs.Content value="url" className="flex flex-col gap-base pt-base">
          <form onSubmit={handleUrlSubmit} className="flex flex-col gap-base">
            <div className="flex flex-col gap-xs">
              <label
                htmlFor={urlInputId}
                className="text-ink"
                style={{ font: "var(--font-caption)" }}
              >
                URL 주소
              </label>
              <input
                id={urlInputId}
                value={url}
                onChange={(event) => {
                  setUrl(event.target.value);
                  setErrorMessage(null);
                }}
                className="h-12 rounded-sm border border-border-strong bg-canvas px-base text-ink outline-none focus:border-2 focus:border-ink"
                style={{ font: "var(--font-body-md)" }}
              />
            </div>
            <div className="flex flex-col gap-xs">
              <label
                htmlFor={urlTitleId}
                className="text-ink"
                style={{ font: "var(--font-caption)" }}
              >
                제목 (선택)
              </label>
              <input
                id={urlTitleId}
                value={urlTitle}
                onChange={(event) => setUrlTitle(event.target.value)}
                className="h-12 rounded-sm border border-border-strong bg-canvas px-base text-ink outline-none focus:border-2 focus:border-ink"
                style={{ font: "var(--font-body-md)" }}
              />
            </div>
            <button
              type="submit"
              disabled={!canSubmitUrl}
              className="h-12 self-start rounded-sm bg-primary px-lg text-on-primary transition-colors active:bg-primary-active disabled:cursor-not-allowed disabled:bg-primary-disabled"
              style={{ font: "var(--font-button-md)" }}
            >
              소스 등록
            </button>
          </form>
        </Tabs.Content>

        <Tabs.Content value="text" className="flex flex-col gap-base pt-base">
          <form onSubmit={handleTextSubmit} className="flex flex-col gap-base">
            <div className="flex flex-col gap-xs">
              <label
                htmlFor={textTitleId}
                className="text-ink"
                style={{ font: "var(--font-caption)" }}
              >
                제목
              </label>
              <input
                id={textTitleId}
                value={textTitle}
                onChange={(event) => setTextTitle(event.target.value)}
                className="h-12 rounded-sm border border-border-strong bg-canvas px-base text-ink outline-none focus:border-2 focus:border-ink"
                style={{ font: "var(--font-body-md)" }}
              />
            </div>
            <div className="flex flex-col gap-xs">
              <label
                htmlFor={textInputId}
                className="text-ink"
                style={{ font: "var(--font-caption)" }}
              >
                내용
              </label>
              <textarea
                id={textInputId}
                value={text}
                onChange={(event) => setText(event.target.value)}
                rows={6}
                className="rounded-sm border border-border-strong bg-canvas p-base text-ink outline-none focus:border-2 focus:border-ink"
                style={{ font: "var(--font-body-md)" }}
              />
            </div>
            <button
              type="submit"
              disabled={!canSubmitText}
              className="h-12 self-start rounded-sm bg-primary px-lg text-on-primary transition-colors active:bg-primary-active disabled:cursor-not-allowed disabled:bg-primary-disabled"
              style={{ font: "var(--font-button-md)" }}
            >
              소스 등록
            </button>
          </form>
        </Tabs.Content>
      </Tabs.Root>

      {errorMessage !== null ? (
        // D-07: 조용한 성공/실패가 아니라 눈에 띄는 배너 — role="alert"로 스크린
        // 리더에도 즉시 통지된다.
        <p
          role="alert"
          data-testid="dropzone-error-banner"
          className="rounded-sm border border-primary-error-text bg-canvas px-base py-sm text-primary-error-text"
          style={{ font: "var(--font-caption)" }}
        >
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
