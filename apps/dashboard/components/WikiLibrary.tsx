"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { workspacePath } from "@/lib/workspace-path";

export type WikiLibraryPage = {
  id: string;
  slug: string;
  title: string;
  category: string;
  content: string;
  verification_status: string;
  disputed: boolean;
};

// UI-SPEC Copywriting Contract "Empty wiki (no pages yet)" — 문구를 한 글자도
// 바꾸지 않는다. ⚠️ 필터 결과 0건(아래 NO_MATCH_*)과 다른 상태다: 이쪽은
// "아직 만들어지지 않았다", 저쪽은 "있지만 조건에 안 맞는다"이고 사용자가 할
// 일도 다르다(소스 추가 vs 검색어 변경).
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

function stateLabel(page: WikiLibraryPage) {
  if (page.disputed) return "충돌 감지";
  if (page.verification_status === "verified") return "검증됨";
  if (page.verification_status === "partial") return "부분 검증";
  return "검증 필요";
}

/**
 * ⚠️ 브래킷을 노출하지 않는다. `[[문서명]]` 은 내부 마크업이므로 표기만 남긴다
 * (PRODUCT-INVARIANTS.md §4 가 공개 표면에 대해 못박은 규칙의 내부 화면 판본).
 */
function preview(content: string) {
  return content
    .replace(/\[\[([^\]]+)\]\]/g, "$1")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 150);
}

/**
 * 위키 라이브러리 — 컴파일된 문서의 전체 목록이자 리더로 들어가는 진입점이다.
 *
 * 계약: openspec/specs/wiki-library-navigation/spec.md
 *
 * ⚠️ 목록 조판은 홈 대시보드(섹션 12)의 .doc-list 를 그대로 재사용한다. 홈의
 * "컴파일된 위키 문서" 피드와 이 화면은 같은 물건의 요약본과 전체본이므로,
 * 두 곳이 다르게 생기면 사용자가 같은 목록을 두 번 배워야 한다.
 */
export function WikiLibrary({
  pages,
  workspaceId,
}: {
  pages: WikiLibraryPage[];
  workspaceId: string;
}) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string | null>(null);

  const visible = useMemo(
    () =>
      pages.filter(
        (page) =>
          (!category || page.category === category) &&
          `${page.title} ${preview(page.content)}`
            .toLocaleLowerCase()
            .includes(query.toLocaleLowerCase()),
      ),
    [category, pages, query],
  );

  const isEmpty = pages.length === 0;

  return (
    <div className="content library">
      <section className="hero" data-od-id="wiki-library-header">
        <div>
          <p className="eyebrow">COMPILED KNOWLEDGE</p>
          <h1>위키</h1>
          <p>팀의 소스에서 컴파일된 지식 문서입니다.</p>
        </div>
      </section>

      <section className="stats" aria-label="위키 요약">
        <div className="stat">
          <b>{pages.length}</b>
          <span>전체 문서</span>
        </div>
        <div className="stat">
          <b>
            {pages.filter((p) => p.verification_status === "verified").length}
          </b>
          <span>검증 완료</span>
        </div>
      </section>

      <section data-od-id="wiki-library-list">
        {/* 문서가 하나도 없으면 툴바를 그리지 않는다 — 걸러낼 대상이 없는
            검색창과 필터는 눌러도 아무 일이 없는 어포던스다. */}
        {isEmpty ? null : (
          <div className="toolbar">
            {/* 카테고리는 탭이 아니라 토글 필터다 — 상호 배타적 뷰 전환이 아니므로
              role="tab" 을 쓰지 않고 aria-pressed 로 표현한다. */}
            <div className="chips" role="group" aria-label="카테고리 필터">
              <button
                type="button"
                aria-pressed={category === null}
                className="chip"
                onClick={() => setCategory(null)}
              >
                전체
              </button>
              {categories.map((item) => (
                <button
                  key={item}
                  type="button"
                  aria-pressed={category === item}
                  className="chip"
                  onClick={() => setCategory(category === item ? null : item)}
                >
                  {labels[item]}
                </button>
              ))}
            </div>
            <input
              aria-label="위키 문서 검색"
              className="field search"
              placeholder="제목이나 내용으로 검색"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
        )}

        {visible.length ? (
          <div className="doc-list">
            {visible.map((page) => (
              <Link
                key={page.id}
                className="doc"
                href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
                data-od-id={`wiki-document-${page.slug}`}
              >
                <div className="doc-body">
                  <span className="doc-title">{page.title}</span>
                  <span className="doc-meta">
                    {labels[page.category] ?? page.category} ·{" "}
                    {stateLabel(page)}
                  </span>
                  <p className="doc-excerpt">{preview(page.content)}</p>
                </div>
                <ChevronRight className="nav-icon" aria-hidden="true" />
              </Link>
            ))}
          </div>
        ) : (
          <div className="library-empty" role="status">
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
    </div>
  );
}
