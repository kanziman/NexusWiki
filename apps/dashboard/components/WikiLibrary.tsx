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
  Link2,
  Loader2,
  Map as MapIcon,
  Search,
  Trash2,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { Pagination } from "@/components/Pagination";
import {
  isVerified,
  verificationLabel,
  verificationToneClass,
} from "@/lib/verification-label";
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
  // wiki_page_publications 에 이 문서 id로 된 행이 있으면 발행된 것이다(1:1,
  // 별도 테이블 — wiki_pages 자체에는 발행 여부 컬럼이 없다). null이면 미발행.
  published_at?: string | null;
  // wiki_pages.sources jsonb. 길이가 인용 수다 — 조회수 컬럼은 스키마에 없다.
  sources?: unknown;
};

// UI-SPEC Copywriting Contract "Empty wiki (no pages yet)" — 문구를 한 글자도 바꾸지 않는다.
const EMPTY_HEADING = "아직 컴파일된 위키 페이지가 없습니다";
const EMPTY_BODY = "소스를 추가하면 자동으로 위키 페이지가 생성됩니다.";
const NO_MATCH_BODY = "조건에 맞는 위키 문서가 없습니다.";

const PAGE_SIZE = 8;

const categories = ["concepts", "entities", "guides", "maps"] as const;

// 홈 KnowledgeGrid.CATEGORY_LABELS 와 같아야 한다. 라이브러리만 "항목"이면
// 같은 카테고리가 화면마다 다른 한국어로 불린다.
const CATEGORY_LABELS: Record<string, string> = {
  concepts: "개념",
  entities: "엔티티",
  guides: "가이드",
  maps: "맵",
};

const CATEGORY_HINTS: Record<string, string> = {
  concepts: "핵심 이론",
  entities: "인물·개체",
  guides: "실전 적용",
  maps: "지식 맵",
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

function citationCount(sources: unknown): number {
  return Array.isArray(sources) ? sources.length : 0;
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
  const router = useRouter();
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
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("deleted") === "true") {
        setFeedback({
          type: "success",
          text: "위키 문서가 영구 삭제되었습니다.",
        });
        const url = new URL(window.location.href);
        url.searchParams.delete("deleted");
        window.history.replaceState(
          null,
          "",
          url.pathname + (url.search ? url.search : ""),
        );
      }
    }
  }, []);

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
      setPages((prev) => {
        const next = prev.filter((p) => p.id !== deleteTarget.id);
        const nextVisible = next.filter(
          (p) =>
            (!category || p.category === category) &&
            `${p.title} ${cleanExcerpt(p.content)}`
              .toLocaleLowerCase()
              .includes(query.toLocaleLowerCase()),
        );
        const maxPage = Math.max(1, Math.ceil(nextVisible.length / PAGE_SIZE));
        setPage((curr) => Math.min(curr, maxPage));
        return next;
      });
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
  // ⚠️ isVerified 만 쓴다. verification_status === "verified" 로 세면
  // 충돌·만료 문서가 이 화면에서만 검증된 것으로 집계되어, 목적지마다
  // 같은 상태를 다르게 부르는 문제가 재발한다.
  const verifiedCount = pages.filter((p) => isVerified(p)).length;
  const verificationRate =
    pages.length === 0 ? 0 : Math.round((verifiedCount / pages.length) * 100);

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {
      concepts: 0,
      entities: 0,
      guides: 0,
      maps: 0,
    };
    for (const item of pages) {
      if (item.category in counts) {
        counts[item.category] += 1;
      }
    }
    return counts;
  }, [pages]);

  const allPaginatedSelected =
    paginatedPages.length > 0 &&
    paginatedPages.every((p) => selectedIds.has(p.id));

  const somePaginatedSelected =
    paginatedPages.some((p) => selectedIds.has(p.id)) && !allPaginatedSelected;

  const selectAllRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = somePaginatedSelected;
    }
  }, [somePaginatedSelected]);

  function applyCategoryFilter(next: string | null) {
    setCategory(next);
    setPage(1);
  }

  function handleToggleSelect(id: string, e?: React.SyntheticEvent) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
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
      // ⚠️ 새로고침 없이 카드 배지에 반영한다 — 안 그러면 발행이 성공해도
      // 목록은 다음 새로고침 전까지 "미발행"으로 보여 방금 한 작업이
      // 사라진 것처럼 느껴진다.
      const publishedAtByPageId = new Map(
        result.published_pages.map((p) => [p.wiki_page_id, p.published_at]),
      );
      setPages((prev) =>
        prev.map((p) => {
          const publishedAt = publishedAtByPageId.get(p.id);
          if (!publishedAt) return p;
          return { ...p, published_at: publishedAt };
        }),
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

  const showFloatingBulk = canVerify && selectedIds.size > 0;

  return (
    <div
      className={`content library${showFloatingBulk ? " has-floating-bulk" : ""}`}
    >
      {/* 헤더 영역 */}
      <section className="hero" data-od-id="wiki-library-header">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1>위키 라이브러리</h1>
            <span className="inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 font-mono text-[11px] font-bold text-[var(--muted)]">
              {pages.length}
            </span>
          </div>
          <p>원문 소스에서 검증 및 컴파일된 상호 연결된 지식 문서입니다.</p>
        </div>
      </section>

      {/* 지식 건강 벤토. 카테고리 칸은 칩과 같은 category state 를 쓴다 —
          요약과 필터가 갈라지면 같은 카테고리를 두 번 고르는 화면이 된다. */}
      {!isEmpty && (
        <section
          className="mt-8 mb-2 grid grid-cols-2 gap-3.5 md:grid-cols-3 lg:grid-cols-5"
          aria-label="지식 건강"
        >
          <div className="flex flex-col gap-2.5 overflow-hidden rounded-[14px] border border-[var(--border)] bg-[var(--surface)] px-[18px] py-4">
            <div className="flex items-center justify-between text-[12px] font-semibold text-[var(--muted)]">
              <span>검증률</span>
              <CheckCircle2
                size={16}
                className="text-[var(--good)]"
                aria-hidden="true"
              />
            </div>
            <div className="flex flex-wrap items-baseline gap-2">
              <b className="font-mono text-[26px] font-extrabold tracking-tight text-[var(--fg)]">
                {`${verificationRate}%`}
              </b>
              <span className="rounded-md bg-[var(--good)]/12 px-1.5 py-0.5 text-[11px] font-bold text-[var(--good)]">
                {`${verifiedCount}/${pages.length} 검증됨`}
              </span>
            </div>
            <div className="mt-1 h-1 overflow-hidden rounded-full bg-[var(--border)]">
              <div
                className="h-full rounded-full bg-[var(--good)]"
                style={{
                  width: `${Math.min(100, Math.max(0, verificationRate))}%`,
                }}
              />
            </div>
          </div>

          {categories.map((item) => {
            const count = categoryCounts[item];
            const pressed = category === item;
            return (
              <button
                key={`health-${item}`}
                type="button"
                aria-pressed={pressed}
                aria-label={`${CATEGORY_LABELS[item]} ${count} ${CATEGORY_HINTS[item]}`}
                onClick={() =>
                  applyCategoryFilter(category === item ? null : item)
                }
                className={`flex flex-col gap-1.5 overflow-hidden rounded-[14px] border px-[18px] py-4 text-left transition-colors ${
                  pressed
                    ? "border-[var(--accent)] bg-[var(--soft)]"
                    : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-strong)]"
                }`}
              >
                <span className="text-[12px] font-semibold text-[var(--muted)]">
                  {CATEGORY_LABELS[item]}
                </span>
                <b className="font-mono text-[26px] font-extrabold tracking-tight text-[var(--fg)]">
                  {count}
                </b>
                <span className="text-[11px] text-[var(--muted)]">
                  {CATEGORY_HINTS[item]}
                </span>
              </button>
            );
          })}
        </section>
      )}

      {/* 피드백 메시지 알림 */}
      {feedback && (
        <div
          role="status"
          className={`flex items-center justify-between gap-2 p-3 rounded-lg text-xs font-medium border ${
            feedback.type === "success"
              ? "bg-[var(--good)]/12 border-[var(--good)]/30 text-[var(--good)]"
              : "bg-[var(--danger)]/12 border-[var(--danger)]/30 text-[var(--danger)]"
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
              className="chips flex items-center gap-1.5 flex-nowrap overflow-x-auto max-w-full pb-1 -mb-1 scrollbar-none sm:flex-wrap sm:overflow-visible sm:pb-0 sm:mb-0"
              role="group"
              aria-label="카테고리 필터"
            >
              <button
                type="button"
                aria-pressed={category === null}
                aria-label={`전체 ${pages.length}`}
                className="chip transition-colors flex-none whitespace-nowrap"
                onClick={() => applyCategoryFilter(null)}
              >
                전체
                <span className="font-mono text-[11px] opacity-80">
                  {pages.length}
                </span>
              </button>
              {categories.map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={category === item}
                  aria-label={`${CATEGORY_LABELS[item]} ${categoryCounts[item]}`}
                  className="chip transition-colors flex-none whitespace-nowrap"
                  onClick={() =>
                    applyCategoryFilter(category === item ? null : item)
                  }
                >
                  {CATEGORY_LABELS[item]}
                  <span className="font-mono text-[11px] opacity-80">
                    {categoryCounts[item]}
                  </span>
                </button>
              ))}
            </div>

            {/* 검색창. / 키 포커스 단축키는 신설하지 않는다. */}
            <div className="relative w-full sm:max-w-[280px] flex-none">
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
              {query ? (
                <button
                  type="button"
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-[var(--muted)] hover:text-[var(--fg)]"
                  aria-label="검색어 지우기"
                  onClick={() => {
                    setQuery("");
                    setPage(1);
                  }}
                >
                  <X size={13} aria-hidden="true" />
                </button>
              ) : null}
            </div>
          </div>
        )}

        {/* 문서 목록 */}
        {visible.length ? (
          <>
            {canVerify && paginatedPages.length > 0 && (
              <div className="flex items-center justify-between min-h-[42px] py-2 px-0.5 select-none">
                <div className="flex items-center gap-2.5">
                  <label
                    className={`group inline-flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all cursor-pointer shadow-2xs ${
                      allPaginatedSelected
                        ? "border-[var(--accent)]/40 bg-[var(--soft)] text-[var(--accent)] shadow-xs"
                        : selectedIds.size > 0
                          ? "border-[var(--border-strong)] bg-[var(--surface)] text-[var(--fg)]"
                          : "border-[var(--border)] bg-[var(--surface)]/70 hover:bg-[var(--surface)] hover:border-[var(--border-strong)] text-[var(--muted)] hover:text-[var(--fg)]"
                    }`}
                  >
                    <input
                      ref={selectAllRef}
                      type="checkbox"
                      checked={allPaginatedSelected}
                      onChange={handleToggleSelectAll}
                      className="w-3.5 h-3.5 rounded border-[var(--border)] text-[var(--accent)] focus:ring-0 focus:ring-offset-0 cursor-pointer accent-[var(--accent)]"
                      aria-label="현재 페이지 전체 선택"
                      data-testid="select-all-checkbox"
                    />
                    <span className="text-[11.5px] font-semibold tracking-tight">
                      {selectedIds.size > 0
                        ? `${selectedIds.size}개 문서 선택됨`
                        : "현재 페이지 전체 선택"}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded-full text-[10px] font-mono font-bold transition-colors ${
                        allPaginatedSelected
                          ? "bg-[var(--accent)] text-white"
                          : selectedIds.size > 0
                            ? "bg-[var(--surface-hover)] text-[var(--fg)] border border-[var(--border)]"
                            : "bg-[var(--bg)] text-[var(--muted)] border border-[var(--border)] group-hover:text-[var(--fg)]"
                      }`}
                    >
                      {paginatedPages.length}
                    </span>
                  </label>
                </div>

                {selectedIds.size > 0 && (
                  <span className="text-[11px] text-[var(--muted)] font-mono hidden sm:inline-block">
                    {`전체 ${visible.length}개 중 ${selectedIds.size}개 선택됨`}
                  </span>
                )}
              </div>
            )}

            <div className="wiki-cards grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {paginatedPages.map((item) => {
                const verified = isVerified(item);
                const label = stateLabel(item);
                const isSelected = selectedIds.has(item.id);
                const citations = citationCount(item.sources);

                return (
                  <div
                    key={item.id}
                    data-od-id={`wiki-document-${item.slug}`}
                    onClick={() => {
                      if (canVerify) {
                        handleToggleSelect(item.id);
                      } else {
                        router.push(
                          `${workspacePath(workspaceId)}/wiki/${item.slug}`,
                        );
                      }
                    }}
                    className={`wiki-card group relative flex flex-col justify-between p-4 sm:p-4.5 rounded-xl border transition-all min-w-0 cursor-pointer ${
                      canVerify ? "select-none" : ""
                    } ${
                      isSelected
                        ? "border-[var(--accent)] bg-[var(--soft)]/40 ring-1 ring-[var(--accent)]/40 shadow-xs"
                        : "border-[var(--border)] bg-[var(--bg)] hover:bg-[var(--surface)] hover:border-[var(--border-strong)] hover:shadow-xs"
                    }`}
                  >
                    {canVerify && (
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {}}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleSelect(item.id);
                        }}
                        className="sr-only"
                        aria-label={`${item.title} 선택`}
                        data-testid={`select-wiki-${item.id}`}
                      />
                    )}

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <div className="flex flex-wrap items-center gap-1.5 leading-none min-w-0">
                          <span className="inline-flex items-center gap-1 text-[10.5px] font-bold tracking-wider text-[var(--accent)]">
                            {getCategoryIcon(item.category)}
                            <span>
                              {CATEGORY_LABELS[item.category] ?? item.category}
                            </span>
                          </span>
                          <span
                            className="w-1 h-1 rounded-full bg-[var(--muted)] opacity-40"
                            aria-hidden="true"
                          />
                          <span
                            className={`inline-flex items-center gap-1 text-[10.5px] font-semibold ${verificationToneClass(item)}`}
                          >
                            {verified && <CheckCircle2 size={10} />}
                            <span>{label}</span>
                          </span>
                          {item.published_at && (
                            <>
                              <span
                                className="w-1 h-1 rounded-full bg-[var(--muted)] opacity-40"
                                aria-hidden="true"
                              />
                              <span className="inline-flex items-center gap-1 text-[10.5px] font-semibold text-[var(--accent)]">
                                <Globe size={10} aria-hidden="true" />
                                <span>발행됨</span>
                              </span>
                            </>
                          )}
                          {citations > 0 && (
                            <>
                              <span
                                className="w-1 h-1 rounded-full bg-[var(--muted)] opacity-40"
                                aria-hidden="true"
                              />
                              <span className="inline-flex items-center gap-1 text-[10.5px] font-mono text-[var(--muted)]">
                                <Link2 size={9} aria-hidden="true" />
                                <span>인용 {citations}개</span>
                              </span>
                            </>
                          )}
                        </div>

                        {canVerify && (
                          <div
                            className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all flex-none ${
                              isSelected
                                ? "bg-[var(--accent)] text-white shadow-2xs scale-100"
                                : "border border-[var(--border-strong)] bg-[var(--surface)] opacity-0 group-hover:opacity-70 scale-90"
                            }`}
                            aria-hidden="true"
                          >
                            {isSelected ? "✓" : ""}
                          </div>
                        )}
                      </div>

                      <h3
                        title={item.title}
                        className="text-[16px] font-bold tracking-tight text-[var(--fg)] group-hover:text-[var(--accent)] transition-colors mb-1 truncate block"
                      >
                        {item.title}
                      </h3>

                      <p className="text-xs text-[var(--muted)] leading-relaxed line-clamp-2 max-w-3xl overflow-hidden text-ellipsis mb-3.5">
                        {cleanExcerpt(item.content)}
                      </p>
                    </div>

                    <div className="flex items-center justify-between pt-2.5 border-t border-[var(--border)]/60 mt-auto gap-2">
                      <div className="flex items-center gap-1">
                        {isOwner && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              setDeleteError(null);
                              setDeleteTarget(item);
                            }}
                            className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 p-1 rounded-md text-[var(--muted)] hover:text-[var(--danger)] hover:bg-[var(--danger)]/12 transition-all cursor-pointer"
                            title="문서 삭제"
                            aria-label={`${item.title} 삭제`}
                            data-testid={`delete-wiki-item-${item.id}`}
                          >
                            <Trash2 size={13} aria-hidden="true" />
                          </button>
                        )}
                      </div>

                      <Link
                        href={`${workspacePath(workspaceId)}/wiki/${item.slug}`}
                        onClick={(e) => e.stopPropagation()}
                        aria-label={`${item.title} 상세 보기`}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] hover:border-[var(--border-strong)] text-xs font-semibold text-[var(--fg)] hover:text-[var(--accent)] transition-all flex-none shadow-2xs group/btn"
                      >
                        <span>상세 보기</span>
                        <ChevronRight
                          size={13}
                          className="text-[var(--muted)] group-hover/btn:text-[var(--accent)] group-hover/btn:translate-x-0.5 transition-all"
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

      {/* 일괄 검증·발행·선택 해제는 플로팅 바가 담당한다. 인라인에 두면
          목록 높이가 밀려 카드 리듬이 깨진다. 게이트는 위치가 바뀌어도
          canVerify 그대로다. */}
      {showFloatingBulk &&
        (() => {
          const floatingBar = (
            <div
              className="bulk-floating-bar flex items-center justify-between sm:justify-start gap-2 sm:gap-3 rounded-2xl border border-[var(--border)] bg-[var(--bg)]/95 backdrop-blur-md px-3.5 py-2.5 sm:px-5 sm:py-3 shadow-2xl"
              data-testid="bulk-action-bar"
              role="toolbar"
              aria-label="선택한 문서 일괄 작업"
            >
              <div className="flex items-center gap-2 flex-none min-w-0">
                <span className="text-xs font-bold text-[var(--fg)] whitespace-nowrap">
                  {selectedIds.size}개 문서 선택됨
                </span>
                <button
                  type="button"
                  onClick={() => setSelectedIds(new Set())}
                  className="text-xs text-[var(--muted)] hover:text-[var(--fg)] underline cursor-pointer whitespace-nowrap"
                >
                  선택 해제
                </button>
              </div>

              <span
                className="hidden sm:block h-4 w-px bg-[var(--border)] flex-none"
                aria-hidden="true"
              />

              <div className="flex items-center gap-1.5 sm:gap-2 flex-none">
                <button
                  type="button"
                  onClick={handleBulkVerify}
                  disabled={bulkLoading !== null}
                  className="nw-focus-ring inline-flex items-center gap-1 sm:gap-1.5 rounded-lg border border-[var(--good)]/40 bg-[var(--good)]/12 px-2.5 py-1.5 text-[11.5px] sm:text-xs font-semibold text-[var(--good)] hover:bg-[var(--good)] hover:text-[var(--bg)] transition-all cursor-pointer shadow-2xs disabled:opacity-50 whitespace-nowrap flex-none shrink-0"
                  data-testid="bulk-verify-btn"
                >
                  {bulkLoading === "verify" ? (
                    <Loader2 size={13} className="animate-spin flex-none" />
                  ) : (
                    <Check size={13} className="flex-none" />
                  )}
                  <span className="whitespace-nowrap">선택 일괄 검증</span>
                </button>
                <button
                  type="button"
                  onClick={handleBulkPublish}
                  disabled={bulkLoading !== null}
                  className="nw-focus-ring inline-flex items-center gap-1 sm:gap-1.5 rounded-lg border border-[var(--accent)]/40 bg-[var(--soft)] px-2.5 py-1.5 text-[11.5px] sm:text-xs font-semibold text-[var(--accent)] hover:bg-[var(--accent)] hover:text-[var(--bg)] transition-all cursor-pointer shadow-2xs disabled:opacity-50 whitespace-nowrap flex-none shrink-0"
                  data-testid="bulk-publish-btn"
                >
                  {bulkLoading === "publish" ? (
                    <Loader2 size={13} className="animate-spin flex-none" />
                  ) : (
                    <Globe size={13} className="flex-none" />
                  )}
                  <span className="whitespace-nowrap">선택 일괄 발행</span>
                </button>
              </div>
            </div>
          );

          return mounted
            ? createPortal(floatingBar, document.body)
            : floatingBar;
        })()}

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
