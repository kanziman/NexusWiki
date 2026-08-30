"use client";

import * as Dialog from "@radix-ui/react-dialog";
import {
  BookOpen,
  CircleAlert,
  Compass,
  FileText,
  HelpCircle,
  Layers,
  Map,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Plus,
  Settings,
  Sparkles,
  Star,
  Trash2,
  Upload,
  Users,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import React, { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api-client";
import { formatCredits } from "@/lib/credits";
import {
  deleteAskThread,
  listAskThreads,
  renameAskThread,
  type AskThreadSummary,
} from "@/lib/ask-threads";
import {
  clearActiveAskThread,
  getActiveAskThread,
} from "@/lib/ask-active-thread";
import { workspacePath } from "@/lib/workspace-path";

type WorkspaceBudget = {
  cap_micros: number;
  spent_micros: number;
  remaining_micros: number;
  month_start: string;
  truncated: boolean;
  authoritative: boolean;
};
import {
  WorkspaceSwitcher,
  type WorkspaceSwitcherProps,
} from "./WorkspaceSwitcher";

export type WorkspaceSidebarProps = {
  workspaces: WorkspaceSwitcherProps["workspaces"];
  currentWorkspaceId: string;
  accountEmail?: string;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
};

const CATEGORIES = [
  { slug: "concepts", label: "개념", icon: Sparkles },
  { slug: "entities", label: "엔티티", icon: Layers },
  { slug: "guides", label: "가이드", icon: BookOpen },
  { slug: "maps", label: "맵", icon: Map },
] as const;

export function WorkspaceSidebar({
  workspaces,
  currentWorkspaceId,
  accountEmail = "developer@nexuswiki.com",
  isOpenMobile = false,
  onCloseMobile,
  collapsed = false,
  onToggleCollapsed,
}: WorkspaceSidebarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const base = workspacePath(currentWorkspaceId);
  const currentCategory = searchParams.get("category");
  const activeThreadId = searchParams.get("thread");
  const isBookmarkedFilterActive =
    pathname.startsWith(`${base}/wiki`) &&
    searchParams.get("bookmarked") === "true";

  const [recentThreads, setRecentThreads] = useState<AskThreadSummary[]>([]);
  const [budget, setBudget] = useState<WorkspaceBudget | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AskThreadSummary | null>(
    null,
  );
  const [renameTarget, setRenameTarget] = useState<AskThreadSummary | null>(
    null,
  );
  const [renameTitle, setRenameTitle] = useState("");
  const [renameError, setRenameError] = useState<string | null>(null);
  const [renameSubmitting, setRenameSubmitting] = useState(false);

  useEffect(() => {
    if (!currentWorkspaceId) return;
    let cancelled = false;
    listAskThreads(currentWorkspaceId)
      .then((rows) => {
        if (!cancelled && Array.isArray(rows)) {
          setRecentThreads(rows.slice(0, 5));
        }
      })
      .catch(() => {
        // 백엔드 오류 시 사이드바는 조용히 기본 네비게이션 유지
      });
    apiFetch<WorkspaceBudget>(`/workspaces/${currentWorkspaceId}/budget`)
      .then((res) => {
        if (!cancelled && res && typeof res.cap_micros === "number") {
          setBudget(res);
        }
      })
      .catch(() => {
        // 오류 시 조용히 무시
      });
    return () => {
      cancelled = true;
    };
  }, [currentWorkspaceId, pathname]);

  const initial = accountEmail ? accountEmail.charAt(0).toUpperCase() : "W";

  function handleItemClick() {
    if (onCloseMobile) {
      onCloseMobile();
    }
  }

  function handleAskNavigation(event: React.MouseEvent<HTMLAnchorElement>) {
    handleItemClick();
    const threadId = getActiveAskThread(currentWorkspaceId);
    if (!threadId) return;
    event.preventDefault();
    router.push(`${base}/ask?thread=${encodeURIComponent(threadId)}`);
  }

  const isAskSectionActive = pathname.startsWith(`${base}/ask`);

  return (
    <>
      <aside
        className={`sidebar ${isOpenMobile ? "mobile-open" : ""}${collapsed && !isOpenMobile ? " collapsed" : ""}`}
        data-od-id="primary-navigation"
      >
        <div className="w-full">
          <WorkspaceSwitcher
            workspaces={workspaces}
            currentWorkspaceId={currentWorkspaceId}
          />
        </div>

        {onToggleCollapsed && !isOpenMobile ? (
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="icon-btn"
            data-od-id="lnb-collapse-toggle"
            aria-label={collapsed ? "메뉴 펼치기" : "메뉴 접기"}
          >
            {collapsed ? (
              <PanelLeftOpen className="nav-icon" aria-hidden="true" />
            ) : (
              <PanelLeftClose className="nav-icon" aria-hidden="true" />
            )}
          </button>
        ) : null}

        <nav className="nav-stack" aria-label="주요 메뉴">
          <Link
            href={base}
            prefetch={true}
            onClick={handleItemClick}
            aria-label="홈 대시보드"
            aria-current={
              pathname === base && !currentCategory ? "page" : undefined
            }
            className={`nav-item ${pathname === base && !currentCategory ? "active" : ""}`}
          >
            <Compass className="nav-icon" aria-hidden="true" />
            <span>홈 대시보드</span>
          </Link>

          <Link
            href={`${base}/sources`}
            prefetch={true}
            onClick={handleItemClick}
            aria-label="원문 소스"
            aria-current={
              pathname.startsWith(`${base}/sources`) ? "page" : undefined
            }
            className={`nav-item ${pathname.startsWith(`${base}/sources`) ? "active" : ""}`}
          >
            <Upload className="nav-icon" aria-hidden="true" />
            <span>원문 소스</span>
          </Link>

          {/* 질문하기 + 새 대화 액션 */}
          <div className="group/ask flex items-center justify-between">
            <Link
              href={`${base}/ask`}
              prefetch={true}
              onClick={handleAskNavigation}
              aria-label="질문하기"
              aria-current={
                isAskSectionActive && !activeThreadId ? "page" : undefined
              }
              className={`nav-item flex-1 ${
                isAskSectionActive && !activeThreadId ? "active" : ""
              }`}
            >
              <HelpCircle className="nav-icon" aria-hidden="true" />
              <span>질문하기</span>
            </Link>
            {!collapsed && (
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  handleItemClick();
                  if (typeof window !== "undefined") {
                    clearActiveAskThread(currentWorkspaceId);
                    window.dispatchEvent(
                      new CustomEvent("nexuswiki:new-ask-thread"),
                    );
                  }
                  router.push(`${base}/ask`);
                }}
                className="opacity-0 group-hover/ask:opacity-100 hover:text-[var(--fg)] text-[var(--muted)] p-1 mr-2 rounded-md hover:bg-[var(--surface)] transition-all cursor-pointer"
                title="새 대화 시작"
                aria-label="새 대화 시작"
              >
                <Plus size={13} aria-hidden="true" />
              </button>
            )}
          </div>

          {/* ChatGPT 스타일: LNB 최근 대화 이력 목록 */}
          {!collapsed && recentThreads.length > 0 && (
            <div
              className="pl-3 pr-1 py-1 my-0.5 space-y-0.5 border-l border-[var(--border)] ml-4.5"
              data-testid="sidebar-recent-threads"
            >
              <div className="text-[10px] font-semibold text-[var(--muted)] uppercase tracking-wider px-2 py-0.5">
                최근 대화
              </div>
              {recentThreads.map((thread) => {
                const isThreadActive =
                  isAskSectionActive && activeThreadId === thread.id;
                return (
                  <div
                    key={thread.id}
                    className={`group/thread relative flex items-center justify-between gap-1 px-2 py-1 rounded-md text-[11.5px] transition-colors ${
                      isThreadActive
                        ? "bg-[var(--surface)] text-[var(--accent)] font-semibold shadow-2xs"
                        : "text-[var(--muted)] hover:text-[var(--fg)] hover:bg-[var(--surface)]/60 font-normal"
                    }`}
                  >
                    <Link
                      href={`${base}/ask?thread=${thread.id}`}
                      prefetch={true}
                      onClick={handleItemClick}
                      title={thread.title}
                      aria-current={isThreadActive ? "page" : undefined}
                      className="flex items-center gap-1.5 min-w-0 flex-1 truncate"
                    >
                      <MessageSquare
                        size={11.5}
                        className={`flex-none opacity-60 group-hover/thread:opacity-100 ${
                          isThreadActive
                            ? "text-[var(--accent)] opacity-100"
                            : ""
                        }`}
                        aria-hidden="true"
                      />
                      <span className="truncate flex-1">{thread.title}</span>
                    </Link>

                    <div className="flex items-center gap-0.5 opacity-0 group-hover/thread:opacity-100 transition-opacity">
                      <button
                        type="button"
                        className="p-0.5 rounded text-[var(--muted)] hover:text-[var(--fg)] hover:bg-[var(--bg)]"
                        title="이름 바꾸기"
                        aria-label={`${thread.title} 대화 이름 바꾸기`}
                        onClick={(e) => {
                          e.stopPropagation();
                          setRenameTarget(thread);
                          setRenameTitle(thread.title);
                          setRenameError(null);
                        }}
                      >
                        <Pencil size={10.5} aria-hidden="true" />
                        <span className="sr-only">이름 바꾸기</span>
                      </button>
                      <button
                        type="button"
                        className="p-0.5 rounded text-[var(--muted)] hover:text-[var(--danger)] hover:bg-[var(--bg)]"
                        title="삭제"
                        aria-label={`${thread.title} 대화 삭제`}
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteTarget(thread);
                        }}
                      >
                        <Trash2 size={10.5} aria-hidden="true" />
                        <span className="sr-only">삭제</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <Link
            href={`${base}/wiki`}
            prefetch={true}
            onClick={handleItemClick}
            aria-label="위키 문서"
            aria-current={
              pathname.startsWith(`${base}/wiki`) && !isBookmarkedFilterActive
                ? "page"
                : undefined
            }
            className={`nav-item ${pathname.startsWith(`${base}/wiki`) && !isBookmarkedFilterActive ? "active" : ""}`}
          >
            <FileText className="nav-icon" aria-hidden="true" />
            <span>위키 문서</span>
          </Link>

          <Link
            href={`${base}/backlog`}
            prefetch={true}
            onClick={handleItemClick}
            aria-label="미완성 백로그"
            aria-current={
              pathname.startsWith(`${base}/backlog`) ? "page" : undefined
            }
            className={`nav-item ${pathname.startsWith(`${base}/backlog`) ? "active" : ""}`}
          >
            <CircleAlert className="nav-icon" aria-hidden="true" />
            <span>미완성 백로그</span>
          </Link>

          <Link
            href={`${base}/wiki?bookmarked=true`}
            prefetch={true}
            onClick={handleItemClick}
            aria-label="즐겨찾기"
            aria-current={isBookmarkedFilterActive ? "page" : undefined}
            className={`nav-item ${isBookmarkedFilterActive ? "active" : ""}`}
          >
            <Star className="nav-icon" aria-hidden="true" />
            <span>즐겨찾기</span>
          </Link>

          <div className="nav-label" aria-hidden="true">
            <span>카테고리</span>
          </div>

          {CATEGORIES.map(({ slug, label, icon: Icon }) => {
            const isCategoryActive =
              pathname === base && currentCategory === slug;
            const href = `${base}?category=${slug}`;

            return (
              <Link
                key={slug}
                href={href}
                prefetch={true}
                onClick={handleItemClick}
                data-category={slug}
                aria-label={label}
                aria-current={isCategoryActive ? "page" : undefined}
                className={`nav-item ${isCategoryActive ? "active" : ""}`}
              >
                <Icon className="nav-icon" aria-hidden="true" />
                <span>{label}</span>
              </Link>
            );
          })}

          <div className="nav-label" aria-hidden="true">
            <span>팀 관리</span>
          </div>

          <Link
            href={`${base}/settings`}
            prefetch={true}
            onClick={handleItemClick}
            aria-label="팀원 & 역할 관리"
            aria-current={
              pathname.startsWith(`${base}/settings`) ? "page" : undefined
            }
            className={`nav-item ${pathname.startsWith(`${base}/settings`) ? "active" : ""}`}
          >
            <Users className="nav-icon" aria-hidden="true" />
            <span>팀원 &amp; 역할 관리</span>
          </Link>
        </nav>

        {/* 무료 크레딧 미니 위젯 */}
        {budget && budget.cap_micros > 0 && !collapsed && (
          <Link
            href={`${base}/settings?tab=operations`}
            prefetch={true}
            onClick={handleItemClick}
            className="mx-3 mb-2 flex items-center justify-between rounded-xl border border-[var(--border)]/70 bg-[var(--surface)]/40 p-2.5 text-xs text-[var(--fg)] hover:border-[var(--accent)] hover:bg-[var(--soft)]/50 transition-all group"
            title="운영 현황 및 무료 크레딧 관리"
          >
            <div className="flex items-center gap-2 min-w-0">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--accent)]/10 text-[var(--accent)] group-hover:bg-[var(--accent)] group-hover:text-white transition-colors flex-none">
                <Zap size={14} aria-hidden="true" />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-[10px] font-medium text-[var(--muted)] truncate">
                  무료 크레딧
                </span>
                <span className="text-[11px] font-bold text-[var(--fg)] truncate">
                  {formatCredits(budget.remaining_micros)} 남음
                </span>
              </div>
            </div>
            <span className="text-[11px] font-semibold text-[var(--muted)] group-hover:text-[var(--accent)] transition-colors flex-none">
              {Math.min(
                100,
                Math.max(
                  0,
                  Math.round((budget.spent_micros / budget.cap_micros) * 100),
                ),
              )}
              %
            </span>
          </Link>
        )}

        <div
          className="profile"
          data-od-id="user-profile"
          aria-label={accountEmail}
        >
          <div className="avatar">{initial}</div>
          <div className="profile-text">
            <strong className="truncate">{accountEmail.split("@")[0]}</strong>
            <span className="truncate">{accountEmail}</span>
          </div>
          <Link
            href={`${base}/settings`}
            onClick={handleItemClick}
            className="icon-btn"
            aria-label="설정"
          >
            <Settings className="nav-icon" aria-hidden="true" />
          </Link>
        </div>
      </aside>

      {/* LNB 최근 대화 삭제 모달 */}
      <Dialog.Root
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="modal-backdrop fixed inset-0" />
          <Dialog.Content className="modal fixed top-1/2 left-1/2 z-50 w-[min(480px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2">
            <div className="modal-head mb-4">
              <Dialog.Title className="text-base font-bold text-[var(--fg)]">
                대화 삭제
              </Dialog.Title>
            </div>
            <Dialog.Description className="text-xs text-[var(--muted)] mb-3">
              {deleteTarget
                ? `'${deleteTarget.title}' 대화를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`
                : ""}
            </Dialog.Description>
            <div className="modal-foot flex items-center justify-end gap-2 mt-4">
              <Dialog.Close asChild>
                <button type="button" className="button compact">
                  취소
                </button>
              </Dialog.Close>
              <button
                type="button"
                className="button compact danger"
                onClick={() => {
                  if (!deleteTarget) return;
                  const target = deleteTarget;
                  void deleteAskThread(currentWorkspaceId, target.id).then(
                    () => {
                      setRecentThreads((prev) =>
                        prev.filter((row) => row.id !== target.id),
                      );
                      if (activeThreadId === target.id) {
                        clearActiveAskThread(currentWorkspaceId);
                        router.push(`${base}/ask`);
                      }
                      setDeleteTarget(null);
                    },
                  );
                }}
              >
                삭제
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* LNB 최근 대화 이름 변경 모달 */}
      <Dialog.Root
        open={renameTarget !== null}
        onOpenChange={(open) => {
          if (!open) {
            setRenameTarget(null);
            setRenameTitle("");
            setRenameError(null);
          }
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="modal-backdrop fixed inset-0" />
          <Dialog.Content className="modal fixed top-1/2 left-1/2 z-50 w-[min(480px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2">
            <div className="modal-head mb-4">
              <Dialog.Title className="text-base font-bold text-[var(--fg)]">
                대화 이름 변경
              </Dialog.Title>
            </div>
            <Dialog.Description className="text-xs text-[var(--muted)] mb-3">
              대화의 새로운 제목을 입력하세요.
            </Dialog.Description>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!renameTarget || !renameTitle.trim() || renameSubmitting)
                  return;
                setRenameSubmitting(true);
                setRenameError(null);
                renameAskThread(
                  currentWorkspaceId,
                  renameTarget.id,
                  renameTitle.trim(),
                )
                  .then((row) => {
                    setRecentThreads((prev) =>
                      prev.map((item) => (item.id === row.id ? row : item)),
                    );
                    setRenameTarget(null);
                    setRenameTitle("");
                  })
                  .catch(() => {
                    setRenameError(
                      "이름을 변경하지 못했습니다. 다시 시도해주세요.",
                    );
                  })
                  .finally(() => {
                    setRenameSubmitting(false);
                  });
              }}
            >
              <input
                type="text"
                value={renameTitle}
                onChange={(e) => setRenameTitle(e.target.value)}
                placeholder="대화 제목"
                className="w-full px-3 py-2 text-xs rounded-md border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--fg)] outline-none focus:border-[var(--accent)] transition-all mb-2"
                autoFocus
              />
              {renameError && (
                <p className="text-xs text-[var(--danger)] mb-3">
                  {renameError}
                </p>
              )}
              <div className="modal-foot flex items-center justify-end gap-2 mt-4">
                <Dialog.Close asChild>
                  <button type="button" className="button compact">
                    취소
                  </button>
                </Dialog.Close>
                <button
                  type="submit"
                  className="button compact primary"
                  disabled={!renameTitle.trim() || renameSubmitting}
                >
                  {renameSubmitting ? "변경 중..." : "변경"}
                </button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
