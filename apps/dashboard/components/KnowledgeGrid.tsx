"use client";

import Link from "next/link";
import {
  BookOpen,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Link2,
  Plus,
} from "lucide-react";
import React, { useState } from "react";

import {
  isVerified,
  verificationLabel,
  verificationToneClass,
} from "@/lib/verification-label";
import { workspacePath } from "@/lib/workspace-path";
import { BacklogDetailModal } from "./BacklogDetailModal";
import type { BacklogItem, BacklogReferencingPage } from "./BacklogList";

export type WikiPageSummary = {
  id: string;
  title: string;
  slug: string;
  category?: string | null;
  verification_status?: string | null;
  // ⚠️ verification_status 와 독립인 별도 컬럼이다. 이 필드를 빠뜨리면
  // verificationLabel 의 충돌 우선순위가 조용히 도달 불가능해진다.
  disputed?: boolean | null;
  expires_at?: string | null;
  updated_at?: string | null;
  citation_count?: number;
};

export type BacklogSummary = {
  target_slug: string;
  reference_count: number;
  display_title?: string;
  impact?: number;
  first_detected_at?: string;
  referencing_pages?: BacklogReferencingPage[];
};

export type KnowledgeGridProps = {
  workspaceId: string;
  wikiPages: WikiPageSummary[];
  backlogItems: BacklogSummary[];
  activeCategory?: string | null;
};

const CATEGORY_LABELS: Record<string, string> = {
  concepts: "개념",
  entities: "엔티티",
  guides: "가이드",
  maps: "맵",
};

const MAX_WIKI_PAGES = 5;
const MAX_BACKLOG_ITEMS = 4;

export function KnowledgeGrid({
  workspaceId,
  wikiPages,
  backlogItems,
  activeCategory,
}: KnowledgeGridProps) {
  const base = workspacePath(workspaceId);
  const [openTopic, setOpenTopic] = useState<BacklogItem | null>(null);

  const filteredPages = activeCategory
    ? wikiPages.filter((p) => p.category === activeCategory)
    : wikiPages;

  const visiblePages = filteredPages.slice(0, MAX_WIKI_PAGES);
  const visibleBacklog = backlogItems.slice(0, MAX_BACKLOG_ITEMS);

  return (
    <div className="sections" data-od-id="knowledge-grid">
      {/* 1. 컴파일된 위키 문서 섹션 카드 */}
      <section
        className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5 shadow-2xs flex flex-col gap-3.5"
        data-od-id="compiled-wiki-section"
      >
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]/80">
          <div className="flex items-center gap-2">
            <BookOpen size={17} className="text-[var(--accent)] flex-none" />
            <h2 className="text-base font-extrabold text-[var(--fg)] tracking-tight flex items-center gap-2 m-0">
              <span>컴파일된 위키 문서</span>
              <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-[var(--surface)] text-[var(--muted)] border border-[var(--border)]">
                <span>{String(filteredPages.length).padStart(2, "0")}</span>
              </span>
            </h2>
          </div>
          <Link
            href={`${base}/wiki`}
            className="text-xs font-bold text-[var(--accent)] hover:opacity-80 flex items-center gap-1 transition-opacity"
            data-od-id="view-all-documents"
          >
            <span>전체 보기</span>
            <span aria-hidden="true">→</span>
          </Link>
        </div>

        <div className="flex flex-col gap-2">
          {filteredPages.length === 0 ? (
            <div className="py-8 text-center text-sm text-[var(--muted)] border border-dashed border-[var(--border)] rounded-lg">
              {activeCategory
                ? `선택한 카테고리(${CATEGORY_LABELS[activeCategory] ?? activeCategory})에 해당하는 문서가 없습니다.`
                : "컴파일된 위키 문서가 아직 없습니다."}
            </div>
          ) : (
            visiblePages.map((page) => {
              const catLabel = page.category
                ? (CATEGORY_LABELS[page.category] ?? page.category)
                : "미분류";
              // 라벨·색 판정 모두 lib/verification-label.ts 에서 가져온다 —
              // 위키 라이브러리와 같은 말, 같은 색을 써야 한다. 여기서 삼항으로
              // 색을 다시 만들면 한쪽만 고쳤을 때 같은 충돌 문서가 화면마다
              // 다른 색으로 보인다.
              //
              // ⚠️ 검증을 무너뜨리는 상태(충돌·만료)도 표식을 남긴다. 검증만
              // 띄우면 그런 문서가 이 화면에서 아무 표식 없이 지나가고,
              // 라이브러리·리더에서만 경고가 보인다.
              const verified = isVerified(page);
              const citations = page.citation_count ?? 0;

              return (
                <Link
                  key={page.id}
                  href={`${base}/wiki/${page.slug}`}
                  className="group flex items-center justify-between p-3 sm:p-3.5 rounded-lg border border-[var(--border)] bg-[var(--bg)] hover:bg-[var(--surface)] hover:border-[var(--border-strong)] hover:shadow-2xs transition-all"
                  data-od-id={`wiki-document-${page.slug}`}
                >
                  <div className="flex-1 min-w-0 pr-3">
                    <div className="flex items-center gap-1.5 mb-1 leading-none flex-wrap">
                      <span className="text-[10.5px] font-bold tracking-wider uppercase text-[var(--accent)]">
                        {catLabel}
                      </span>
                      <span className="w-1 h-1 rounded-full bg-[var(--muted)] opacity-40"></span>
                      <span
                        className={`inline-flex items-center gap-1 text-[10.5px] font-semibold ${verificationToneClass(page)}`}
                      >
                        {verified && <CheckCircle2 size={10} />}
                        <span>{verificationLabel(page)}</span>
                      </span>
                      {citations > 0 && (
                        <>
                          <span className="w-1 h-1 rounded-full bg-[var(--muted)] opacity-40"></span>
                          <span className="inline-flex items-center gap-1 text-[10.5px] font-mono text-[var(--muted)]">
                            <Link2 size={9} />
                            <span>인용 원문 {citations}개</span>
                          </span>
                        </>
                      )}
                    </div>
                    <span className="text-[14.5px] sm:text-[15px] font-bold text-[var(--fg)] group-hover:text-[var(--accent)] transition-colors block truncate">
                      {page.title}
                    </span>
                  </div>
                  <ChevronRight
                    size={16}
                    className="text-[var(--muted)] group-hover:translate-x-0.5 group-hover:text-[var(--accent)] transition-all flex-none ml-2"
                    aria-hidden="true"
                  />
                </Link>
              );
            })
          )}
        </div>
      </section>

      {/* 2. 작성 대기 백로그 섹션 카드 */}
      <section
        className="backlog rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5 shadow-2xs flex flex-col gap-3.5"
        data-od-id="writing-backlog-section"
      >
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]/80">
          <div className="flex items-center gap-2">
            <CircleAlert
              size={17}
              className="text-[var(--warning)] flex-none"
            />
            <h2 className="text-base font-extrabold text-[var(--fg)] tracking-tight flex items-center gap-2 m-0">
              <span>지식 공백 (작성 대기 백로그)</span>
              <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-[var(--warning)]/10 text-[var(--warning)] border border-[var(--warning)]/25">
                <span>{String(backlogItems.length).padStart(2, "0")}</span>
              </span>
            </h2>
          </div>
          <Link
            href={`${base}/backlog`}
            className="text-xs font-bold text-[var(--warning)] hover:opacity-80 flex items-center gap-1 transition-opacity"
            data-od-id="view-all-backlog"
          >
            <span>전체 보기</span>
            <span aria-hidden="true">→</span>
          </Link>
        </div>

        <div className="flex flex-col gap-2">
          {backlogItems.length === 0 ? (
            <div className="py-8 text-center text-sm text-[var(--muted)] border border-dashed border-[var(--border)] rounded-lg">
              작성 대기 중인 백로그가 없습니다.
            </div>
          ) : (
            visibleBacklog.map((item) => {
              const displayTitle = item.display_title || item.target_slug;
              const count = item.impact ?? item.reference_count;
              const fullItem: BacklogItem = {
                target_slug: item.target_slug,
                display_title: displayTitle,
                impact: count,
                first_detected_at:
                  item.first_detected_at ?? new Date().toISOString(),
                referencing_pages: item.referencing_pages ?? [],
              };

              return (
                <div
                  key={item.target_slug}
                  className="flex items-center justify-between p-3 sm:p-3.5 rounded-lg border border-[var(--border)] border-l-[3px] border-l-[var(--warning)] bg-[var(--bg)] hover:bg-[var(--surface)] hover:border-[var(--border-strong)] hover:border-l-[var(--warning)] hover:shadow-2xs transition-all gap-3"
                  data-od-id={`backlog-${item.target_slug}`}
                >
                  <button
                    type="button"
                    onClick={() => setOpenTopic(fullItem)}
                    className="flex-1 min-w-0 bg-transparent p-0 text-left cursor-pointer border-none"
                    aria-haspopup="dialog"
                  >
                    <span className="text-[13.5px] sm:text-[14px] font-bold font-mono text-[var(--fg)] hover:text-[var(--accent)] transition-colors block truncate">
                      {displayTitle}
                    </span>
                    <span className="text-xs text-[var(--muted)] mt-0.5 block">
                      위키 {count}곳에서 인용됨 · 원문 소스 연결 필요
                    </span>
                  </button>
                  <Link
                    href={`${base}/sources?prefillTitle=${encodeURIComponent(displayTitle)}&tab=text`}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md border border-[var(--border)] bg-[var(--surface)] text-xs font-semibold text-[var(--fg)] hover:border-[var(--accent)] hover:bg-[var(--soft)] hover:text-[var(--accent)] transition-all flex-none shadow-2xs"
                  >
                    <Plus size={12} aria-hidden="true" />
                    <span>소스 추가</span>
                  </Link>
                </div>
              );
            })
          )}
        </div>

        {/* 하단 원문 연결 콜아웃 카드 */}
        <div
          className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3 mt-1.5 flex items-center justify-between gap-3"
          data-od-id="source-connection-callout"
        >
          <div className="min-w-0 flex-1">
            <b className="text-xs font-bold text-[var(--fg)] block">
              새 원문으로 지식 업데이트
            </b>
            <span className="text-[11px] text-[var(--muted)] block truncate">
              문서, 링크 또는 저장소 파일을 연결할 수 있습니다.
            </span>
          </div>
          <Link
            href={`${base}/sources`}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md bg-[var(--accent)] text-white text-xs font-bold hover:opacity-90 transition-all flex-none shadow-xs"
            id="openSourceInline"
          >
            <Plus size={12} aria-hidden="true" />
            <span>소스 연결</span>
          </Link>
        </div>
      </section>

      {/* 3. 백로그 상세 모달 */}
      <BacklogDetailModal
        workspaceId={workspaceId}
        item={openTopic}
        onClose={() => setOpenTopic(null)}
      />
    </div>
  );
}
