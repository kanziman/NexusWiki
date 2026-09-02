"use client";

import Link from "next/link";
import { ChevronRight, Plus } from "lucide-react";
import React, { useState } from "react";

import {
  isExpiredVerification,
  isVerified,
  verificationLabel,
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

const MAX_WIKI_PAGES = 10;
const MAX_BACKLOG_ITEMS = 8;

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
      {/* 1. 컴파일된 위키 문서 피드 */}
      <section data-od-id="compiled-wiki-section">
        <div className="section-head">
          <h2>
            컴파일된 위키 문서
            <span>{String(filteredPages.length).padStart(2, "0")}</span>
          </h2>
          <Link
            href={`${base}/wiki`}
            className="text-button"
            data-od-id="view-all-documents"
          >
            전체 보기 →
          </Link>
        </div>

        <div className="doc-list">
          {filteredPages.length === 0 ? (
            <div className="py-8 text-center text-sm text-[var(--muted)] border-b border-[var(--border)]">
              {activeCategory
                ? `선택한 카테고리(${CATEGORY_LABELS[activeCategory] ?? activeCategory})에 해당하는 문서가 없습니다.`
                : "컴파일된 위키 문서가 아직 없습니다."}
            </div>
          ) : (
            visiblePages.map((page) => {
              const catLabel = page.category
                ? (CATEGORY_LABELS[page.category] ?? page.category)
                : "미분류";
              // 라벨과 판정 모두 lib/verification-label.ts 에서 가져온다 —
              // 위키 라이브러리와 같은 말을 써야 한다(이전에는 여기만
              // "검증 완료"라 목적지마다 다른 이름으로 불렸다).
              const verified = isVerified(page);
              // ⚠️ 검증을 무너뜨리는 상태(충돌·만료)도 배지로 띄운다. 검증만
              // 띄우면 그런 문서가 이 화면에서 아무 표식 없이 지나가고,
              // 라이브러리·리더에서만 경고가 보인다 — 같은 상태가 목적지마다
              // 다르게 보이는 문제의 다른 얼굴이다.
              //
              // workspace-home-prd.md §3.3 은 `.badge.verified` 를
              // `verification_status='verified'` 에만 쓰라고 한다. 그 규칙은
              // 지킨다 — 아래 className 이 verified 일 때만 .verified 를 붙이고
              // (isVerified 는 PRD 조건의 진부분집합이다), 충돌·만료는 중립
              // .badge 로 그린다.
              // ⚠️ 같은 항목의 둘째 절("나머지 3종은 뱃지를 달지 않는다")과는
              // `unverified ∧ disputed=true` 조합에서 문자 그대로 부딪힌다 —
              // enum 값과 boolean 컬럼은 배타가 아니다(불변식 §3). 무표식으로
              // 지나가는 쪽이 더 나쁘다고 보고 배지를 택했다. 되돌리려면
              // design.md Decision 2 의 마지막 문단을 먼저 읽는다.
              const disputed = Boolean(page.disputed);
              const expired = isExpiredVerification(page);
              const citations = page.citation_count ?? 0;

              return (
                <Link
                  key={page.id}
                  href={`${base}/wiki/${page.slug}`}
                  className="doc group"
                  data-od-id={`wiki-document-${page.slug}`}
                >
                  <div className="doc-body">
                    <span className="doc-meta flex flex-wrap items-center gap-1.5">
                      <span className="font-bold tracking-wide text-[var(--accent)]">
                        {catLabel}
                      </span>
                      {(verified || disputed || expired) && (
                        <b className={verified ? "badge verified" : "badge"}>
                          {verificationLabel(page)}
                        </b>
                      )}
                      {citations > 0 && <span>인용 원문 {citations}개</span>}
                    </span>
                    <span className="doc-title group-hover:text-[var(--accent)]">
                      {page.title}
                    </span>
                  </div>
                  <ChevronRight
                    className="nav-icon transition-transform group-hover:translate-x-0.5"
                    aria-hidden="true"
                  />
                </Link>
              );
            })
          )}
        </div>
      </section>

      {/* 2. 작성 대기 백로그 피드 */}
      <section className="backlog" data-od-id="writing-backlog-section">
        <div className="section-head">
          <h2>
            작성 대기 백로그
            <span>{String(backlogItems.length).padStart(2, "0")}</span>
          </h2>
          <Link
            href={`${base}/backlog`}
            className="text-button"
            data-od-id="view-all-backlog"
          >
            전체 보기 →
          </Link>
        </div>

        <div className="doc-list">
          {backlogItems.length === 0 ? (
            <div className="py-8 text-center text-sm text-[var(--muted)] border-b border-[var(--border)]">
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
                  className="doc w-full text-left"
                  data-od-id={`backlog-${item.target_slug}`}
                >
                  <button
                    type="button"
                    onClick={() => setOpenTopic(fullItem)}
                    className="doc-body min-w-0 flex-1 bg-transparent p-0 text-left"
                    aria-haspopup="dialog"
                  >
                    <span className="doc-title">{displayTitle}</span>
                    <span className="doc-meta">
                      위키 {count}곳에서 인용됨 · 원문 소스 연결 필요
                    </span>
                  </button>
                  <Link
                    href={`${base}/sources?prefillTitle=${encodeURIComponent(displayTitle)}&tab=text`}
                    className="button compact flex flex-none items-center gap-1"
                  >
                    <Plus size={13} aria-hidden="true" />
                    <span>소스 추가</span>
                  </Link>
                </div>
              );
            })
          )}
        </div>

        <div className="source-line" data-od-id="source-connection-callout">
          <div>
            <b>새 원문으로 지식 업데이트</b>
            <span>문서, 링크 또는 저장소 파일을 연결할 수 있습니다.</span>
          </div>
          <Link
            href={`${base}/sources`}
            className="button compact primary flex items-center gap-1"
            id="openSourceInline"
          >
            <Plus size={13} aria-hidden="true" />
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
