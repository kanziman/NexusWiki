"use client";

import Link from "next/link";
import { useState } from "react";

import { formatRelativeTime } from "@/lib/relative-time";
import { workspacePath } from "@/lib/workspace-path";

export type BacklogReferencingPage = {
  id: string;
  slug: string;
  title: string;
};

export type BacklogItem = {
  target_slug: string;
  impact: number;
  first_detected_at: string;
  referencing_pages: BacklogReferencingPage[];
};

export type BacklogListProps = {
  workspaceId: string;
  initialItems: BacklogItem[];
};

const EMPTY_HEADING = "작성 대기 중인 백로그가 없습니다";
const EMPTY_BODY = "모든 위키 링크가 정상적으로 연결되어 있습니다.";

/**
 * ⚠️ 표시용 제목은 slug 의 하이픈을 공백으로 되돌린 근사값이다. 원문 표기
 * (`[[캐시 계층 전략]]`)는 저장되지 않는다 — link_sync 가 slugify 한 값만 넣는다.
 * backlog-management-prd.md §6-2 의 미해결 결정이며, 정확한 표기를 얻으려면
 * from_wiki_id 본문에서 찾아야 한다(권고안 (c), 별도 change).
 * 그래서 원본 slug 를 title/aria-label 과 보조 줄에 함께 남긴다.
 */
function displayTopic(slug: string): string {
  return slug.replace(/-/g, " ");
}

/**
 * UI-06 작성 대기 백로그 — 미해결 레드링크(`to_wiki_id IS NULL`)를 target_slug
 * 로 집계해 인용 빈도 내림차순으로 보여준다.
 *
 * 계약: openspec/specs/backlog-ask/spec.md
 * 화면 요구사항: docs/design-systems/v2/backlog-management-prd.md §3.1~3.2
 *
 * ⚠️ 백로그는 "할 일 목록"이 아니라 위키 본문의 파생 상태다(PRD §1.1). 사용자가
 * 항목을 만들거나 지우거나 보류할 수 없고 — `authenticated` 에게 `wiki_links` 는
 * SELECT 뿐이다 — 만들어도 다음 link_sync 가 지운다. 그래서 이 화면에는 쓰기
 * 액션이 하나도 없다. 유일한 동선은 "이 주제의 자료를 넣는다"(§2.3)이며
 * RedLinkCta 와 같은 목적지로 보낸다.
 */
export function BacklogList({ workspaceId, initialItems }: BacklogListProps) {
  const [items] = useState<BacklogItem[]>(initialItems);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredItems = items.filter((item) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    const matchesSlug = item.target_slug.toLowerCase().includes(query);
    const matchesPage = item.referencing_pages.some((page) =>
      page.title.toLowerCase().includes(query),
    );
    return matchesSlug || matchesPage;
  });

  // ⚠️ PRD §3.1: 주제 수는 distinct target_slug 로 센다. wiki_links 는
  // (출발 문서 × 대상) 행이라 5개 문서가 같은 주제를 가리키면 5행이다 — 그대로
  // 세면 결손 주제 1개가 "미해결 5건"으로 부풀려진다. 서버가 이미 target_slug
  // 로 접어서 넘기므로 items.length 가 곧 distinct 주제 수다.
  const distinctReferringPages = new Set(
    items.flatMap((item) => item.referencing_pages.map((p) => p.id)),
  );

  return (
    <div className="content backlog">
      <section className="hero" data-od-id="backlog-header">
        <div>
          <p className="eyebrow">BACKLOG · RED LINKS</p>
          {/* 라우트 이름은 LNB 와 맞춘다. PRD §3.1 은 브레드크럼을 "작성 대기
              백로그"로 적지만, LNB(프로토타입·테스트 계약)가 "미완성 백로그"라
              화면이 진입 경로와 다른 이름을 갖게 된다. */}
          <h1>미완성 백로그</h1>
          <p>
            위키 문서에서 참조되었으나 아직 작성되지 않은 레드링크 목록입니다.
            관련 소스를 추가하면 자동으로 컴파일되어 해결됩니다.
          </p>
        </div>
      </section>

      <section className="stats" aria-label="백로그 요약">
        <div className="stat">
          <b>{items.length}</b>
          <span>미해결 백로그</span>
        </div>
        <div className="stat">
          <b>{distinctReferringPages.size}</b>
          <span>영향받는 위키</span>
        </div>
      </section>

      <section data-od-id="backlog-table-section">
        <div className="toolbar">
          {/* PRD §3.2: 필터 탭은 `전체` 하나로 시작한다. `높은 인용 빈도`·`신규
              감지`는 정렬로 충분하고, `소스 삭제 결손`은 그런 경로 자체가 없다
              (§2.4) — 축이 없는 탭을 만들지 않는다. */}
          <nav className="tabs" role="tablist" aria-label="백로그 필터">
            <button
              type="button"
              role="tab"
              aria-selected
              className="tab active"
            >
              전체 {items.length}
            </button>
          </nav>
          <input
            className="field search"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="주제 또는 참조 문서로 검색"
            aria-label="백로그 검색"
          />
        </div>

        {filteredItems.length === 0 ? (
          <div className="table-wrap p-8 text-center">
            <b className="block text-[13px]">
              {items.length === 0 ? EMPTY_HEADING : "검색 결과가 없습니다"}
            </b>
            <span className="mt-1 block text-[11px] text-[var(--muted)]">
              {items.length === 0
                ? EMPTY_BODY
                : "다른 검색어를 입력하거나 검색어를 지우세요."}
            </span>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="table" id="backlog-items-list">
              <colgroup>
                <col style={{ width: "30%" }} />
                <col style={{ width: "32%" }} />
                <col style={{ width: "12%" }} />
                <col style={{ width: "14%" }} />
                <col style={{ width: "12%" }} />
              </colgroup>
              <thead>
                <tr>
                  <th scope="col">백로그 주제</th>
                  <th scope="col">인용 중인 위키</th>
                  <th scope="col">인용 빈도</th>
                  <th scope="col">최초 감지</th>
                  <th scope="col">
                    <span className="sr-only">작업</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => {
                  const topic = displayTopic(item.target_slug);

                  return (
                    <tr key={item.target_slug}>
                      <td>
                        <div className="topic">
                          <b
                            title={item.target_slug}
                            aria-label={item.target_slug}
                          >
                            {topic}
                          </b>
                          <span>{item.target_slug}</span>
                        </div>
                      </td>

                      <td>
                        {item.referencing_pages.length === 0 ? (
                          <span className="sub">인용 문서 없음</span>
                        ) : (
                          <div className="doc-chips">
                            {item.referencing_pages.map((page) => (
                              <Link
                                key={page.id}
                                href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
                                className="doc-chip"
                                title={page.title}
                              >
                                {page.title}
                              </Link>
                            ))}
                          </div>
                        )}
                      </td>

                      <td>
                        {/* 결손은 오류가 아니라 정상적인 작업 대기 상태다
                            (PRD §3.2) — --danger 를 쓰지 않고 정렬 축인 이 수치에만
                            강세를 준다. */}
                        <b className="impact">{item.impact}</b>
                        <span className="impact-unit">회</span>
                      </td>

                      <td>
                        <span className="sub">
                          {formatRelativeTime(item.first_detected_at)}
                        </span>
                      </td>

                      <td>
                        {/* ⚠️ 이 백로그에 소스를 "연결"하는 것이 아니다(PRD §2.3).
                            워크스페이스에 자료를 넣으면 컴파일러가 그 slug 의
                            페이지를 만들고 resolve_red_links 가 기다리던 링크를
                            일괄 해소한다. RedLinkCta 와 같은 목적지다. */}
                        <Link
                          href={`${workspacePath(workspaceId)}/sources?prefillTitle=${encodeURIComponent(
                            topic,
                          )}&tab=text`}
                          className="button compact"
                        >
                          소스 추가
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
