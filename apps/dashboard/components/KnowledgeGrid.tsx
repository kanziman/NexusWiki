"use client";

import Link from "next/link";
import { ChevronRight, Plus } from "lucide-react";

import { workspacePath } from "@/lib/workspace-path";

export type WikiPageSummary = {
  id: string;
  title: string;
  slug: string;
  category?: string | null;
  verification_status?: string | null;
  updated_at?: string | null;
  citation_count?: number;
};

export type BacklogSummary = {
  target_slug: string;
  reference_count: number;
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

export function KnowledgeGrid({
  workspaceId,
  wikiPages,
  backlogItems,
  activeCategory,
}: KnowledgeGridProps) {
  const base = workspacePath(workspaceId);

  const filteredPages = activeCategory
    ? wikiPages.filter((p) => p.category === activeCategory)
    : wikiPages;

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
            <div className="py-8 text-center text-sm text-[var(--nw-muted)] border-b border-[var(--border)]">
              {activeCategory
                ? `선택한 카테고리(${CATEGORY_LABELS[activeCategory] ?? activeCategory})에 해당하는 문서가 없습니다.`
                : "컴파일된 위키 문서가 아직 없습니다."}
            </div>
          ) : (
            filteredPages.map((page) => {
              const catLabel = page.category
                ? (CATEGORY_LABELS[page.category] ?? page.category)
                : "미분류";
              const isVerified = page.verification_status === "verified";
              const citations = page.citation_count ?? 0;

              return (
                <Link
                  key={page.id}
                  href={`${base}/wiki/${page.slug}`}
                  className="doc"
                  data-od-id={`wiki-document-${page.slug}`}
                >
                  <div className="doc-body">
                    <span className="doc-title">{page.title}</span>
                    <span className="doc-meta">
                      {catLabel}
                      {citations > 0 && ` · 인용 원문 ${citations}개`}
                      {isVerified && (
                        <>
                          {" "}
                          · <b className="badge verified">검증 완료</b>
                        </>
                      )}
                    </span>
                  </div>
                  <ChevronRight className="nav-icon" aria-hidden="true" />
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
            <div className="py-8 text-center text-sm text-[var(--nw-muted)] border-b border-[var(--border)]">
              작성 대기 중인 백로그가 없습니다.
            </div>
          ) : (
            backlogItems.map((item) => (
              <div
                key={item.target_slug}
                className="doc"
                data-od-id={`backlog-${item.target_slug}`}
              >
                <div className="doc-body">
                  <span className="doc-title">{item.target_slug}</span>
                  <span className="doc-meta">
                    위키 {item.reference_count}곳에서 인용됨 · 원본 소스 연결
                    필요
                  </span>
                </div>
                <ChevronRight className="nav-icon" aria-hidden="true" />
              </div>
            ))
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
    </div>
  );
}
