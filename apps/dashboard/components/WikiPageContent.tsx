"use client";

import * as Dialog from "@radix-ui/react-dialog";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowUpRight,
  Check,
  FileText,
  Globe,
  GlobeOff,
  Layers,
  Link2,
  Loader2,
  Trash2,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";

import { FavoriteButton } from "@/components/FavoriteButton";
import { WikiDocumentBody } from "@/components/WikiDocumentBody";
import { apiFetch } from "@/lib/api-client";
import { createClient } from "@/lib/supabase/client";
import { cleanWikiContent, extractHeadings } from "@/lib/wiki-document";
import { verificationLabel } from "@/lib/verification-label";
import { workspacePath } from "@/lib/workspace-path";
import {
  deleteWikiPage,
  publishWikiPage,
  unpublishWikiPage,
} from "@/lib/wiki-publication";

// UI-SPEC Copywriting Contract "Wiki viewer (UI-05)" — 문구를 한 글자도 바꾸지 않는다.
const READ_ONLY_BANNER =
  "이 페이지는 컴파일됩니다 — 직접 편집할 수 없으며, 소스가 갱신되면 다시 컴파일됩니다.";
// ⚠️ 상태 이름은 lib/verification-label.ts 에서 파생한다.
const DISPUTED_CALLOUT = `${verificationLabel({ disputed: true })} — 상충하는 정보가 있습니다. 원문을 확인하세요.`;
const VERIFY_ACTION_LABEL = "검증됨으로 표시";
const VERIFIED_STATUS_LABEL = "검증 완료";
const VERIFY_FAILURE_MESSAGE = "검증 처리에 실패했습니다. 다시 시도해주세요.";
const PUBLISH_ACTION_LABEL = "공개 발행";
const COPY_LINK_ACTION_LABEL = "공개 링크 복사";
const UNPUBLISH_ACTION_LABEL = "발행 취소";
const PUBLISH_FAILURE_MESSAGE = "공개 발행에 실패했습니다. 다시 시도해주세요.";
const UNPUBLISH_FAILURE_MESSAGE =
  "발행 취소에 실패했습니다. 다시 시도해주세요.";
const COPY_SUCCESS_MESSAGE = "공개 링크를 복사했습니다.";
const COPY_FAILURE_MESSAGE = "링크를 복사하지 못했습니다. 다시 시도해주세요.";

// workspace-home-prd.md 카테고리 표시명 매핑 — wiki_pages.category CHECK 4종 고정.
const CATEGORY_LABELS: Record<string, string> = {
  concepts: "개념",
  entities: "엔티티",
  guides: "가이드",
  maps: "맵",
};

type WikiPage = {
  id: string;
  slug: string;
  title: string;
  content: string;
  category: string;
  verification_status: string;
  verified_by: string | null;
  verified_at: string | null;
  expires_at: string | null;
  disputed: boolean;
};

export type WikiPageContentProps = {
  page: WikiPage;
  links: { target_slug: string; resolved: boolean }[];
  workspaceId: string;
  workspaceSlug: string;
  canVerify: boolean;
  isOwner?: boolean;
  initialBookmarked: boolean;
  initialPublishedSlug: string | null;
};

type VerifyResponse = {
  id: string;
  slug: string;
  verification_status: string;
  verified_by: string | null;
  verified_at: string | null;
  expires_at: string | null;
  disputed: boolean;
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/**
 * 위키 문서 뷰어 본체 — 미니멀 & 클린 에디토리얼 조판
 */
export function WikiPageContent({
  page,
  links,
  workspaceId,
  workspaceSlug,
  canVerify,
  isOwner = false,
  initialBookmarked,
  initialPublishedSlug,
}: WikiPageContentProps) {
  const router = useRouter();
  const [status, setStatus] = useState(page.verification_status);
  const [verifiedAt, setVerifiedAt] = useState(page.verified_at);
  const [expiresAt, setExpiresAt] = useState(page.expires_at);
  const [disputed, setDisputed] = useState(page.disputed);
  const [submitting, setSubmitting] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [publishedSlug, setPublishedSlug] = useState<string | null>(
    initialPublishedSlug,
  );
  const [publishing, setPublishing] = useState(false);
  const [unpublishing, setUnpublishing] = useState(false);
  const [publishError, setPublishError] = useState<string | null>(null);
  const [copyStatus, setCopyStatus] = useState<string | null>(null);
  const [activeHeadingId, setActiveHeadingId] = useState<string | null>(null);

  // 개별 위키 삭제 상태
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDeleteWiki() {
    if (deleting || !isOwner) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteWikiPage(workspaceId, page.id);
      setDeleteOpen(false);
      router.push(`${workspacePath(workspaceId)}/wiki?deleted=true`);
    } catch (err: unknown) {
      setDeleteError(
        (err as { message?: string })?.message ||
          "위키 문서를 삭제하지 못했습니다. 다시 시도해주세요.",
      );
    } finally {
      setDeleting(false);
    }
  }

  async function handleVerify() {
    if (submitting) return;
    setSubmitting(true);
    setVerifyError(null);

    try {
      const result = await apiFetch<VerifyResponse>(
        `/workspaces/${workspaceId}/wiki/${page.id}/verify`,
        { method: "PATCH", body: { verification_status: "verified" } },
      );
      setStatus(result.verification_status);
      setVerifiedAt(result.verified_at);
      setExpiresAt(result.expires_at);
      setDisputed(result.disputed);
    } catch {
      setVerifyError(VERIFY_FAILURE_MESSAGE);
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePublish() {
    if (publishing || unpublishing) return;
    setPublishing(true);
    setPublishError(null);
    setCopyStatus(null);

    try {
      const supabase = createClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) {
        setPublishError(PUBLISH_FAILURE_MESSAGE);
        return;
      }
      const result = await publishWikiPage(supabase, {
        workspaceId,
        wikiId: page.id,
        userId: user.id,
      });
      setPublishedSlug(result.published_slug);
    } catch {
      setPublishError(PUBLISH_FAILURE_MESSAGE);
    } finally {
      setPublishing(false);
    }
  }

  async function handleUnpublish() {
    if (publishing || unpublishing) return;
    setUnpublishing(true);
    setPublishError(null);
    setCopyStatus(null);

    try {
      await unpublishWikiPage(createClient(), {
        workspaceId,
        wikiId: page.id,
      });
      setPublishedSlug(null);
    } catch {
      setPublishError(UNPUBLISH_FAILURE_MESSAGE);
    } finally {
      setUnpublishing(false);
    }
  }

  async function handleCopyPublicLink() {
    if (publishedSlug === null || !workspaceSlug) return;
    setCopyStatus(null);
    const url = `${window.location.origin}${publicWikiPath(workspaceSlug, publishedSlug)}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopyStatus(COPY_SUCCESS_MESSAGE);
    } catch {
      setCopyStatus(COPY_FAILURE_MESSAGE);
    }
  }

  const isExpired =
    expiresAt !== null && new Date(expiresAt).getTime() < Date.now();

  const sanitizedContent = cleanWikiContent(page.content);
  const headings = extractHeadings(sanitizedContent);
  const relatedLinks = [
    ...new Map(
      links
        .filter((link) => link.resolved)
        .map((link) => [link.target_slug, link]),
    ).values(),
  ];

  // ScrollSpy: 목차 활성 섹션 감지
  useEffect(() => {
    if (headings.length === 0) return;

    function handleScroll() {
      const scrollPosition = window.scrollY + 100;
      let currentActive: string | null = null;

      for (const h of headings) {
        const el = document.getElementById(h.id);
        if (el) {
          const top = el.getBoundingClientRect().top + window.scrollY;
          if (scrollPosition >= top) {
            currentActive = h.id;
          }
        }
      }

      if (currentActive) {
        setActiveHeadingId(currentActive);
      } else if (headings[0]) {
        setActiveHeadingId(headings[0].id);
      }
    }

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, [headings]);

  const categoryLabel = CATEGORY_LABELS[page.category] ?? page.category;
  const isPageVerified = status === "verified" && !disputed && !isExpired;
  const canPublish = canVerify && isPageVerified && publishedSlug === null;
  const publicationBusy = publishing || unpublishing;

  return (
    <div className="reader-layout">
      <article className="reader">
        {/* 상단 브레드크럼 네비게이션: 뒤로가기 + 현재 카테고리 경로 */}
        <nav
          aria-label="위키 탐색 경로"
          className="flex items-center gap-1.5 mb-3 text-xs text-[var(--muted)]"
        >
          <Link
            href={`${workspacePath(workspaceId)}/wiki`}
            className="inline-flex items-center gap-1.5 py-1 px-2 -ml-2 rounded-md hover:bg-[var(--surface)] hover:text-[var(--fg)] transition-colors font-medium text-xs leading-none text-[var(--muted)]"
            aria-label="위키 목록으로 돌아가기"
          >
            <ArrowLeft size={13} className="shrink-0" aria-hidden="true" />
            <span>위키 목록</span>
          </Link>
          <span
            className="text-[var(--border-strong)] opacity-60 select-none text-[11px] leading-none"
            aria-hidden="true"
          >
            /
          </span>
          <span className="font-semibold text-[var(--fg)] text-xs leading-none">
            {categoryLabel}
          </span>
        </nav>

        {/* 문서 타이틀 + 즐겨찾기 */}
        <div className="title-row">
          <h1>{page.title}</h1>
          <FavoriteButton
            key={page.id}
            wikiId={page.id}
            workspaceId={workspaceId}
            initialBookmarked={initialBookmarked}
          />
        </div>

        {/* 거버넌스 메타데이터 바 */}
        <div className="governance">
          <span className="tag">{categoryLabel}</span>
          {disputed ? (
            <span className="badge" style={{ color: "var(--danger)" }}>
              {DISPUTED_CALLOUT}
            </span>
          ) : (
            <VerificationCallout
              status={status}
              verifiedAt={verifiedAt}
              expiresAt={expiresAt}
              isExpired={isExpired}
            />
          )}
        </div>

        {/* 컴파일 안내 캡션 (담백하고 미니멀한 텍스트) */}
        <p className="mt-2.5 mb-0 text-[11px] text-[var(--muted)] leading-relaxed">
          {READ_ONLY_BANNER}
        </p>

        {/* 검증 · 공개 발행 · 삭제 액션 */}
        {canVerify || isOwner ? (
          <div className="mt-3.5 flex flex-col gap-1">
            <div className="flex flex-wrap items-center gap-2">
              {canVerify ? (
                <>
                  <button
                    type="button"
                    onClick={handleVerify}
                    disabled={submitting || isPageVerified}
                    className="button primary self-start inline-flex items-center gap-1.5 disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    {isPageVerified ? (
                      <Check size={13} aria-hidden="true" />
                    ) : null}
                    {submitting
                      ? "검증 처리 중..."
                      : isPageVerified
                        ? VERIFIED_STATUS_LABEL
                        : VERIFY_ACTION_LABEL}
                  </button>
                  {canPublish ? (
                    <button
                      type="button"
                      onClick={handlePublish}
                      disabled={publicationBusy}
                      className="button self-start inline-flex items-center gap-1.5"
                    >
                      <Globe size={13} aria-hidden="true" />
                      {publishing ? "발행 중..." : PUBLISH_ACTION_LABEL}
                    </button>
                  ) : null}
                  {publishedSlug !== null ? (
                    <>
                      <button
                        type="button"
                        onClick={handleCopyPublicLink}
                        disabled={!workspaceSlug}
                        className="button self-start inline-flex items-center gap-1.5"
                      >
                        <Link2 size={13} aria-hidden="true" />
                        {COPY_LINK_ACTION_LABEL}
                      </button>
                      <button
                        type="button"
                        onClick={handleUnpublish}
                        disabled={publicationBusy}
                        className="button self-start inline-flex items-center gap-1.5"
                      >
                        <GlobeOff size={13} aria-hidden="true" />
                        {unpublishing ? "취소 중..." : UNPUBLISH_ACTION_LABEL}
                      </button>
                    </>
                  ) : null}
                </>
              ) : null}

              {isOwner ? (
                <button
                  type="button"
                  onClick={() => setDeleteOpen(true)}
                  disabled={deleting}
                  className="button compact danger self-start inline-flex items-center gap-1.5 cursor-pointer ml-auto"
                  data-testid="delete-wiki-btn"
                >
                  <Trash2 size={13} aria-hidden="true" />
                  <span>문서 삭제</span>
                </button>
              ) : null}
            </div>
            {verifyError !== null ? (
              <p role="alert" className="invite-feedback error show mt-1">
                {verifyError}
              </p>
            ) : null}
            {publishError !== null ? (
              <p role="alert" className="invite-feedback error show mt-1">
                {publishError}
              </p>
            ) : null}
            {copyStatus !== null ? (
              <p
                role={copyStatus === COPY_FAILURE_MESSAGE ? "alert" : "status"}
                className={`invite-feedback show mt-1${
                  copyStatus === COPY_FAILURE_MESSAGE ? " error" : ""
                }`}
              >
                {copyStatus}
              </p>
            ) : null}
          </div>
        ) : null}

        {/* 본문 렌더링 */}
        <div className="article mt-7" spellCheck={false}>
          <WikiDocumentBody
            content={sanitizedContent}
            linkMode="internal"
            links={links}
            workspaceId={workspaceId}
          />
        </div>

        {/* 하단 관련 문서 섹션 */}
        {relatedLinks.length ? (
          <section
            className="mt-12 border-t border-[var(--border)] pt-8"
            aria-labelledby="related-wiki-heading"
          >
            <div className="flex items-center justify-between gap-2 mb-4">
              <div className="flex items-center gap-2">
                <Layers
                  size={16}
                  className="text-[var(--accent)]"
                  aria-hidden="true"
                />
                <h2
                  id="related-wiki-heading"
                  className="m-0 text-sm font-semibold text-[var(--fg)] tracking-tight"
                >
                  관련 문서
                </h2>
                <span className="rounded-full bg-[var(--surface)] border border-[var(--border)] px-2 py-0.5 text-[10px] font-mono font-medium text-[var(--muted)]">
                  {relatedLinks.length}
                </span>
              </div>
              <p className="m-0 text-xs text-[var(--muted)] hidden sm:block">
                이 문서와 연결된 지식 문서입니다
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {relatedLinks.map((link) => (
                <Link
                  key={link.target_slug}
                  href={`${workspacePath(workspaceId)}/wiki/${link.target_slug}`}
                  className="group relative flex items-center justify-between p-3.5 rounded-xl border border-[var(--border)] bg-[var(--bg)] hover:bg-[var(--surface)]/50 hover:border-[var(--accent)]/50 transition-all duration-150 shadow-[var(--shadow-sm)] hover:shadow"
                >
                  <div className="flex items-center gap-3 min-w-0 pr-2">
                    <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-lg bg-[var(--surface)] border border-[var(--border)] group-hover:border-[var(--accent)]/30 group-hover:text-[var(--accent)] text-[var(--muted)] transition-colors">
                      <FileText size={15} aria-hidden="true" />
                    </div>
                    <div className="min-w-0 flex flex-col">
                      <span className="text-xs font-semibold text-[var(--fg)] group-hover:text-[var(--accent)] truncate transition-colors">
                        {link.target_slug.replace(/-/g, " ")}
                      </span>
                      <span className="text-[10px] font-mono text-[var(--muted)]">
                        위키 문서 보기
                      </span>
                    </div>
                  </div>
                  <ArrowUpRight
                    size={14}
                    className="shrink-0 text-[var(--muted)] group-hover:text-[var(--accent)] group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all duration-150"
                    aria-hidden="true"
                  />
                </Link>
              ))}
            </div>
          </section>
        ) : null}
      </article>

      {/* 우측 목차 (TOC) 패널 */}
      <aside className="toc">
        <div className="toc-heading">
          <h2>목차</h2>
        </div>
        {headings.length ? (
          <nav aria-label="이 문서에서" className="toc-list">
            {headings.map((heading) => {
              const isActive = activeHeadingId === heading.id;
              const indentClass =
                heading.level === 3
                  ? "pl-4"
                  : heading.level >= 4
                    ? "pl-6"
                    : "pl-2";

              return (
                <a
                  key={heading.id}
                  href={`#${heading.id}`}
                  className={`${isActive ? "active" : ""} ${indentClass} transition-colors block text-[11px] leading-snug py-1`}
                  onClick={(e) => {
                    e.preventDefault();
                    const target = document.getElementById(heading.id);
                    if (target) {
                      target.scrollIntoView({ behavior: "smooth" });
                      window.history.pushState(null, "", `#${heading.id}`);
                      setActiveHeadingId(heading.id);
                    }
                  }}
                >
                  {heading.title}
                </a>
              );
            })}
          </nav>
        ) : (
          <p className="m-0 text-[11px] text-[var(--muted)]">
            제목이 없는 문서입니다.
          </p>
        )}
      </aside>

      {/* 개별 위키 문서 삭제 확인 모달 */}
      <Dialog.Root open={deleteOpen} onOpenChange={setDeleteOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md transition-all duration-200" />
          <Dialog.Content className="fixed top-1/2 left-1/2 z-50 w-[min(480px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-6 shadow-2xl outline-none">
            <div className="modal-head mb-4 flex items-start justify-between gap-4">
              <div>
                <Dialog.Title className="text-base font-bold text-[var(--danger)] flex items-center gap-1.5">
                  <AlertTriangle size={18} aria-hidden="true" />
                  <span>위키 문서 영구 삭제</span>
                </Dialog.Title>
                <Dialog.Description className="mt-1.5 text-xs text-[var(--muted)] leading-relaxed">
                  이 작업은 절대 되돌릴 수 없습니다.{" "}
                  <b className="text-[var(--fg)]">&lsquo;{page.title}&rsquo;</b>{" "}
                  문서와 연관된 모든 청크, 임베딩, 공개 발행 및 북마크가 즉시
                  영구 삭제됩니다.
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

            {deleteError && (
              <p
                role="alert"
                className="invite-feedback error show mb-3 text-xs text-[var(--danger)]"
              >
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
                disabled={deleting}
                onClick={handleDeleteWiki}
                className="button compact danger"
                data-testid="confirm-delete-wiki-btn"
              >
                {deleting && <Loader2 size={13} className="animate-spin" />}
                <span>영구 삭제</span>
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

function publicWikiPath(workspaceSlug: string, pageSlug: string): string {
  return `/p/${encodeURIComponent(workspaceSlug)}/${encodeURIComponent(pageSlug)}`;
}

type VerificationCalloutProps = {
  status: string;
  verifiedAt: string | null;
  expiresAt: string | null;
  isExpired: boolean;
};

// ⚠️ verifiedBy(계정 UUID)는 의도적으로 prop에서 받지 않는다. 이 컴포넌트에는
// UUID를 표시명으로 바꿀 조회 경로가 없어, 넘겨받아도 화면에는 못 쓴다 — 안
// 쓰는 prop을 시그니처에 남겨 두면 다음 사람이 "표시할 수 있는데 안 하나?"로
// 헷갈린다.
function VerificationCallout({
  status,
  verifiedAt,
  expiresAt,
  isExpired,
}: VerificationCalloutProps) {
  if (status === "verified" && !isExpired) {
    // ⚠️ 검증자를 표시하지 않는다. `verified_by`는 auth 사용자 UUID이고 이
    // 라우트에는 그것을 이름으로 바꿀 조회 경로가 없다 — 그대로 찍으면 화면에
    // 36자짜리 식별자가 남아 정작 읽어야 할 검증 날짜를 밀어낸다. 사람이 읽을
    // 이름을 붙이려면 표시명 조회가 먼저 필요하고, 그건 이 화면 밖의 일이다.
    const dateLabel = verifiedAt !== null ? formatDate(verifiedAt) : "";
    return (
      <span className="badge verified">
        {`${verificationLabel({ verification_status: "verified" })}${dateLabel ? ` · ${dateLabel}` : ""}`}
      </span>
    );
  }

  if (status === "verified" && isExpired) {
    // isExpired가 true인 분기이므로 expiresAt는 사실상 항상 non-null이지만,
    // prop 시그니처가 string | null이라 렌더 시점에 한 번 더 널가드한다.
    // ⚠️ 상태 이름은 모듈에서 파생한다 — 목록 화면이 같은 문서를 부르는 말과
    // 갈리면 안 된다. 뒤의 날짜·안내는 이 화면 고유의 확장이다.
    const dateLabel = expiresAt !== null ? formatDate(expiresAt) : "";
    const stateName = verificationLabel({
      verification_status: "verified",
      expires_at: expiresAt ?? "1970-01-01T00:00:00Z",
    });
    return (
      <span className="badge" style={{ color: "var(--danger)" }}>
        {`${stateName}${dateLabel ? ` · ${dateLabel} 이후 재검증 필요` : " · 재검증 필요"}`}
      </span>
    );
  }

  if (status === "partial") {
    // UI-SPEC에 partial 전용 문구가 없다 — expired-style(warning-text) 처리를
    // 이 컴포넌트의 합리적 확장으로 채택한다(06-07-PLAN.md Task 2 <action>).
    // ⚠️ 상태 이름 자체는 lib/verification-label.ts 에서 파생한다. 예전에는
    // 여기만 "부분 검증됨"이라 홈·라이브러리의 "부분 검증"과 갈렸다. 뒤에
    // 붙는 안내 문구는 이 화면 고유의 확장이라 그대로 둔다.
    return (
      <span className="badge">
        {verificationLabel({ verification_status: "partial" })} · 재검증이
        필요합니다
      </span>
    );
  }

  // "unverified" — UI-SPEC은 중립 기본 상태로 명시적 콜아웃을 요구하지 않는다.
  return null;
}
