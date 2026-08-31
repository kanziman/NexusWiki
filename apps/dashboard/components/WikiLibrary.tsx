"use client";

import * as Dialog from "@radix-ui/react-dialog";
import {
  AlertTriangle,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronRight,
  FileText,
  Globe,
  HelpCircle,
  Loader2,
  Map as MapIcon,
  Search,
  Trash2,
  X,
} from "lucide-react";
import Link from "next/link";
import React, { useMemo, useState } from "react";

import { Pagination } from "@/components/Pagination";
import { isVerified, verificationLabel } from "@/lib/verification-label";
import {
  bulkPublishWikiPages,
  bulkVerifyWikiPages,
  deleteWikiPage,
} from "@/lib/wiki-publication";
import { workspacePath } from "@/lib/workspace-path";

export type WikiLibraryPage = {
  id: string;
  slug: string;
  title: string;
  category: string;
  content: string;
  verification_status: string;
  disputed: boolean;
  expires_at?: string | null;
};

// UI-SPEC Copywriting Contract "Empty wiki (no pages yet)" — 문구를 한 글자도 바꾸지 않는다.
const EMPTY_HEADING = "아직 컴파일된 위키 페이지가 없습니다";
const EMPTY_BODY = "소스를 추가하면 자동으로 위키 페이지가 생성됩니다.";
const NO_MATCH_BODY = "조건에 맞는 위키 문서가 없습니다.";

const categories = ["concepts", "entities", "guides", "maps"];
const labels: Record<string, string> = {
  concepts: "개념",
  entities: "항목",
  guides: "가이드",
  maps: "맵",
};

// 라벨 매핑은 lib/verification-label.ts 가 소유한다
const stateLabel = verificationLabel;

/**
 * 마크다운 문법(헤딩, 볼드, 코드, 테이블 등)과 브래킷([[...]])을 제거하여
 * 순수하고 깔끔한 평문 발췌문을 만든다.
 */
function cleanExcerpt(content: string): string {
  if (!content) return "";
  return content
    .replace(/\[\[(?:[^\]|]+\|)?([^\]]+)\]\]/g, "$1") // [[slug|title]] -> title
    .replace(/```[\s\S]*?```/g, "") // 코드 블록 제거
    .replace(/`([^`]+)`/g, "$1") // 인라인 코드
    .replace(/#{1,6}\s+/g, "") // 헤딩 제거
    .replace(/(\*\*|__)(.*?)\1/g, "$2") // 볼드 제거
    .replace(/(\*|_)(.*?)\1/g, "$2") // 이탤릭 제거
    .replace(/~~(.*?)~~/g, "$1") // 취소선 제거
    .replace(/^>\s?/gm, "") // 인용구 기호 제거
    .replace(/^[*-]\s+/gm, "") // 리스트 기호 제거
    .replace(/^\d+\.\s+/gm, "") // 번호 리스트 기호 제거
    .replace(/\|/g, " ") // 테이블 파이프 제거
    .replace(/\s+/g, " ") // 연속 공백/줄바꿈 축약
    .trim()
    .slice(0, 160);
}

function getCategoryIcon(category: string) {
  switch (category) {
    case "concepts":
      return <BookOpen size={13} className="opacity-75 flex-none" />;
    case "entities":
      return <FileText size={13} className="opacity-75 flex-none" />;
    case "guides":
      return <HelpCircle size={13} className="opacity-75 flex-none" />;
    case "maps":
      return <MapIcon size={13} className="opacity-75 flex-none" />;
    default:
      return <FileText size={13} className="opacity-75 flex-none" />;
  }
}

/**
 * 위키 라이브러리 — 컴파일된 문서의 전체 목록이자 리더로 들어가는 진입점이다.
 */
export function WikiLibrary({
  pages: initialPages,
  workspaceId,
  canVerify = false,
  isOwner = false,
}: {
  pages: WikiLibraryPage[];
  workspaceId: string;
  canVerify?: boolean;
  isOwner?: boolean;
}) {
  const [pages, setPages] = useState<WikiLibraryPage[]>(initialPages);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkLoading, setBulkLoading] = useState<"verify" | "publish" | null>(
    null,
  );
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  // 개별 위키 삭제 상태
  const [deleteTarget, setDeleteTarget] = useState<WikiLibraryPage | null>(
    null,
  );
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDeleteWiki() {
    if (!deleteTarget || deleting || !isOwner) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteWikiPage(workspaceId, deleteTarget.id);
      setPages((prev) => prev.filter((p) => p.id !== deleteTarget.id));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(deleteTarget.id);
        return next;
      });
      setDeleteTarget(null);
      setFeedback({
        type: "success",
        text: `'${deleteTarget.title}' 문서가 영구 삭제되었습니다.`,
      });
    } catch (err: unknown) {
      setDeleteError(
        (err as { message?: string })?.message ||
          "위키 문서를 삭제하지 못했습니다. 다시 시도해주세요.",
      );
    } finally {
      setDeleting(false);
    }
  }

  const PAGE_SIZE = 8;

  const visible = useMemo(
    () =>
      pages.filter(
        (page) =>
          (!category || page.category === category) &&
          `${page.title} ${cleanExcerpt(page.content)}`
            .toLocaleLowerCase()
            .includes(query.toLocaleLowerCase()),
      ),
    [category, pages, query],
  );

  const paginatedPages = visible.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE,
  );

  const isEmpty = pages.length === 0;
  const verifiedCount = pages.filter((p) => isVerified(p)).length;

  const allPaginatedSelected =
    paginatedPages.length > 0 &&
    paginatedPages.every((p) => selectedIds.has(p.id));

  function handleToggleSelect(id: string, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function handleToggleSelectAll() {
    if (allPaginatedSelected) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        for (const p of paginatedPages) {
          next.delete(p.id);
        }
        return next;
      });
    } else {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        for (const p of paginatedPages) {
          next.add(p.id);
        }
        return next;
      });
    }
  }

  async function handleBulkVerify() {
    if (!canVerify || bulkLoading || selectedIds.size === 0) return;
    setBulkLoading("verify");
    setFeedback(null);
    try {
      const result = await bulkVerifyWikiPages(
        workspaceId,
        Array.from(selectedIds),
      );
      const verifiedMap = new Map(result.verified_pages.map((p) => [p.id, p]));
      setPages((prev) =>
        prev.map((p) => {
          const updated = verifiedMap.get(p.id);
          if (!updated) return p;
          return {
            ...p,
            verification_status: updated.verification_status,
            disputed: updated.disputed,
            expires_at: updated.expires_at,
          };
        }),
      );
      setSelectedIds(new Set());
      setFeedback({
        type: "success",
        text: `${result.verified_count}개의 문서가 검증 완료되었습니다.`,
      });
    } catch (err: unknown) {
      setFeedback({
        type: "error",
        text:
          (err as { message?: string })?.message ||
          "일괄 검증 처리에 실패했습니다. 다시 시도해주세요.",
      });
    } finally {
      setBulkLoading(null);
    }
  }

  async function handleBulkPublish() {
    if (!canVerify || bulkLoading || selectedIds.size === 0) return;
    setBulkLoading("publish");
    setFeedback(null);
    try {
      const result = await bulkPublishWikiPages(
        workspaceId,
        Array.from(selectedIds),
      );
      setSelectedIds(new Set());
      if (result.published_count > 0) {
        setFeedback({
          type: "success",
          text: `${result.published_count}개의 문서가 공개 발행되었습니다.`,
        });
      } else {
        setFeedback({
          type: "error",
          text: "선택한 문서 중 발행 가능한(검증 완료 및 충돌/만료 없음) 문서가 없습니다.",
        });
      }
    } catch (err: unknown) {
      setFeedback({
        type: "error",
        text:
          (err as { message?: string })?.message ||
          "일괄 공개 발행 처리에 실패했습니다. 다시 시도해주세요.",
      });
    } finally {
      setBulkLoading(null);
    }
  }

  return (
    <div className="content library">
      {/* 헤더 영역 */}
      <section className="hero" data-od-id="wiki-library-header">
        <div>
          <h1>위키</h1>
          <p>팀의 소스에서 컴파일된 지식 문서입니다.</p>
        </div>
      </section>

      {/* 요약 지표 */}
      <section className="stats" aria-label="위키 요약">
        <div className="stat">
          <b>{pages.length}</b>
          <span>전체 문서</span>
        </div>
        <div className="stat">
          <b>{verifiedCount}</b>
          <span>검증됨</span>
        </div>
      </section>

      {/* 피드백 메시지 알림 */}
      {feedback && (
        <div
          role="status"
          className={`flex items-center justify-between gap-2 p-3 rounded-lg text-xs font-medium border ${
            feedback.type === "success"
              ? "bg-[var(--good-soft)] border-[var(--good)]/30 text-[var(--good)]"
              : "bg-[var(--danger-soft)] border-[var(--danger)]/30 text-[var(--danger)]"
          }`}
        >
          <span>{feedback.text}</span>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="p-1 hover:opacity-80 transition-opacity"
            aria-label="알림 닫기"
          >
            <X size={13} />
          </button>
        </div>
      )}

      <section data-od-id="wiki-library-list">
        {isEmpty ? null : (
          <div className="toolbar flex items-center justify-between gap-4">
            {/* 카테고리 필터 */}
            <div
              className="chips flex items-center gap-1.5 flex-wrap"
              role="group"
              aria-label="카테고리 필터"
            >
              <button
                type="button"
                aria-pressed={category === null}
                className="chip transition-colors"
                onClick={() => {
                  setCategory(null);
                  setPage(1);
                }}
              >
                전체
              </button>
              {categories.map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={category === item}
                  className="chip transition-colors"
                  onClick={() => {
                    setCategory(category === item ? null : item);
                    setPage(1);
                  }}
                >
                  {labels[item]}
                </button>
              ))}
            </div>

            {/* 검색창 */}
            <div className="relative w-full max-w-[280px] flex-none">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none"
              />
              <input
                aria-label="위키 문서 검색"
                className="field search"
                placeholder="제목이나 내용으로 검색"
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setPage(1);
                }}
              />
            </div>
          </div>
        )}

        {/* 일괄 액션 바 (선택 항목이 있을 때 표시) */}
        {canVerify && selectedIds.size > 0 && (
          <div
            className="bulk-action-bar flex flex-wrap items-center justify-between gap-3 p-3 my-3 rounded-xl border border-[var(--accent)]/30 bg-[var(--surface)] shadow-xs animate-in fade-in slide-in-from-top-1 duration-150"
            data-testid="bulk-action-bar"
          >
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-[var(--fg)]">
                {selectedIds.size}개 문서 선택됨
              </span>
              <button
                type="button"
                onClick={() => setSelectedIds(new Set())}
                className="text-xs text-[var(--muted)] hover:text-[var(--fg)] underline cursor-pointer ml-1"
              >
                선택 해제
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleBulkVerify}
                disabled={bulkLoading !== null}
                className="nw-focus-ring inline-flex items-center gap-1.5 rounded-lg border border-[var(--good)]/40 bg-[var(--good-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--good)] hover:bg-[var(--good)] hover:text-white transition-all cursor-pointer shadow-2xs disabled:opacity-50"
                data-testid="bulk-verify-btn"
              >
                {bulkLoading === "verify" ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <Check size={13} />
                )}
                <span>선택 일괄 검증</span>
              </button>

              <button
                type="button"
                onClick={handleBulkPublish}
                disabled={bulkLoading !== null}
                className="nw-focus-ring inline-flex items-center gap-1.5 rounded-lg border border-[var(--accent)]/40 bg-[var(--accent-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--accent)] hover:bg-[var(--accent)] hover:text-white transition-all cursor-pointer shadow-2xs disabled:opacity-50"
                data-testid="bulk-publish-btn"
              >
                {bulkLoading === "publish" ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <Globe size={13} />
                )}
                <span>선택 일괄 발행</span>
              </button>
            </div>
          </div>
        )}

        {/* 문서 목록 */}
        {visible.length ? (
          <>
            {canVerify && paginatedPages.length > 0 && (
              <div className="flex items-center justify-between py-2 px-3 border-t border-[var(--border)] text-xs text-[var(--muted)]">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={allPaginatedSelected}
                    onChange={handleToggleSelectAll}
                    className="rounded border-[var(--border)] text-[var(--accent)] focus:ring-[var(--accent)] cursor-pointer"
                    aria-label="현재 페이지 전체 선택"
                    data-testid="select-all-checkbox"
                  />
                  <span>현재 페이지 전체 선택 ({paginatedPages.length}개)</span>
                </label>
              </div>
            )}

            <div className="doc-list divide-y divide-[var(--border)] border-t border-b border-[var(--border)]">
              {paginatedPages.map((page) => {
                const verified = isVerified(page);
                const label = stateLabel(page);
                const isSelected = selectedIds.has(page.id);

                return (
                  <div
                    key={page.id}
                    className={`group flex items-center justify-between py-3.5 px-3 hover:bg-[var(--surface)] transition-colors ${
                      isSelected ? "bg-[var(--surface)]/80" : ""
                    }`}
                  >
                    {canVerify && (
                      <div className="flex-none pr-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) =>
                            handleToggleSelect(
                              page.id,
                              e as unknown as React.MouseEvent,
                            )
                          }
                          className="rounded border-[var(--border)] text-[var(--accent)] focus:ring-[var(--accent)] cursor-pointer"
                          aria-label={`${page.title} 선택`}
                          data-testid={`select-wiki-${page.id}`}
                        />
                      </div>
                    )}

                    <Link
                      className="doc-body flex-1 min-w-0 pr-4 block"
                      href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
                      data-od-id={`wiki-document-${page.slug}`}
                    >
                      {/* 상단 메타 뱃지 */}
                      <div className="flex flex-wrap items-center gap-2 mb-1.5">
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-semibold bg-[var(--surface)] text-[var(--muted)] border border-[var(--border)]">
                          {getCategoryIcon(page.category)}
                          <span>{labels[page.category] ?? page.category}</span>
                        </span>

                        <span
                          className={`inline-flex items-center gap-1 text-[11px] font-medium ${
                            page.disputed
                              ? "text-[var(--danger)]"
                              : verified
                                ? "text-[var(--good)]"
                                : "text-[var(--muted)]"
                          }`}
                        >
                          {verified && <CheckCircle2 size={11} />}
                          <span>{label}</span>
                        </span>
                      </div>

                      {/* 문서 제목 */}
                      <span className="doc-title text-[16px] font-bold text-[var(--fg)] group-hover:text-[var(--accent)] transition-colors block truncate leading-snug">
                        {page.title}
                      </span>

                      {/* 발췌문 */}
                      <p className="doc-excerpt text-xs text-[var(--muted)] leading-relaxed mt-1.5 line-clamp-2">
                        {cleanExcerpt(page.content)}
                      </p>
                    </Link>

                    <div className="flex items-center gap-1 flex-none">
                      {isOwner && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setDeleteError(null);
                            setDeleteTarget(page);
                          }}
                          className="p-1.5 rounded-md text-[var(--muted)] hover:text-[var(--danger)] hover:bg-[var(--danger-soft)] transition-colors cursor-pointer mr-1"
                          title="문서 삭제"
                          aria-label={`${page.title} 삭제`}
                          data-testid={`delete-wiki-item-${page.id}`}
                        >
                          <Trash2 size={14} aria-hidden="true" />
                        </button>
                      )}

                      <Link
                        href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
                        aria-hidden="true"
                        tabIndex={-1}
                      >
                        <ChevronRight
                          className="nav-icon text-[var(--muted)] group-hover:text-[var(--fg)] group-hover:translate-x-0.5 transition-all flex-none opacity-60 group-hover:opacity-100"
                          size={16}
                        />
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>

            <Pagination
              currentPage={page}
              totalItems={visible.length}
              pageSize={PAGE_SIZE}
              onPageChange={setPage}
            />
          </>
        ) : (
          <div className="library-empty mt-6" role="status">
            {isEmpty ? (
              <>
                <b>{EMPTY_HEADING}</b>
                <span>{EMPTY_BODY}</span>
              </>
            ) : (
              NO_MATCH_BODY
            )}
          </div>
        )}
      </section>

      {/* 개별 위키 문서 삭제 확인 모달 */}
      <Dialog.Root
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      >
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
                  <b className="text-[var(--fg)]">
                    &lsquo;{deleteTarget?.title}&rsquo;
                  </b>{" "}
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
                data-testid="confirm-delete-wiki-item-btn"
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
