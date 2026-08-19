"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { formatDate, formatRelativeTime } from "@/lib/relative-time";
import { workspacePath } from "@/lib/workspace-path";

export type BacklogReferencingPage = {
  id: string;
  slug: string;
  title: string;
  // add-backlog-topic-context 3.1: 서버가 만든 인용 문맥 발췌 — 이 문서
  // 본문에서 이 주제를 인용한 [[표기]] 주변을 잘라낸 평문. 본문 자체는
  // 여기 오지 않는다.
  excerpt: string | null;
};

export type BacklogItem = {
  target_slug: string;
  display_title: string;
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
  // add-backlog-topic-context 2.1: 행을 열면 상세 패널이 뜬다. URL 상태로
  // 만들지 않는다(design.md Non-Goals "딥링크 URL 상태") — 표기·발췌 모두
  // 목록 로드 시점에 이미 props 로 내려와 있어 패널은 그중 하나를 가리키는
  // 로컬 상태로 충분하다.
  const [openTopic, setOpenTopic] = useState<BacklogItem | null>(null);

  const filteredItems = items.filter((item) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    const matchesTitle = item.display_title.toLowerCase().includes(query);
    const matchesSlug = item.target_slug.toLowerCase().includes(query);
    const matchesPage = item.referencing_pages.some((page) =>
      page.title.toLowerCase().includes(query),
    );
    return matchesTitle || matchesSlug || matchesPage;
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
                  return (
                    <tr key={item.target_slug}>
                      <td>
                        {/* 행이 아니라 이 셀만 트리거다 — 행 안에 소스 추가
                            링크·인용 칩 등 다른 인터랙티브 요소가 함께 있어
                            <tr> 전체에 핸들러를 걸면 클릭 대상이 겹친다. */}
                        <button
                          type="button"
                          className="topic"
                          onClick={() => setOpenTopic(item)}
                          aria-haspopup="dialog"
                        >
                          <b title={item.display_title}>{item.display_title}</b>
                          <span>{item.target_slug}</span>
                        </button>
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
                            item.display_title,
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

      {/* 상세 패널. design.md "패널은 기존 모달 관용구를 쓴다" — SourcesList
          의 업로드 모달과 같은 Radix Dialog + .modal 을 그대로 쓴다. 섹션 15
          의 .drawer 는 재사용하지 않는다(좌표가 앱 셸 사이드바·리더 목차
          폭을 전제해 이 화면에서는 맞지 않는다). */}
      <Dialog.Root
        open={openTopic !== null}
        onOpenChange={(open) => {
          if (!open) setOpenTopic(null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="modal-backdrop fixed inset-0" />
          <Dialog.Content className="modal backlog-panel fixed top-1/2 left-1/2 max-h-[86vh] -translate-x-1/2 -translate-y-1/2 overflow-auto">
            {openTopic ? (
              <>
                <div className="modal-head">
                  <Dialog.Title>{openTopic.display_title}</Dialog.Title>
                  <Dialog.Close asChild>
                    <button
                      type="button"
                      className="icon-btn"
                      aria-label="닫기"
                    >
                      <X size={16} aria-hidden="true" />
                    </button>
                  </Dialog.Close>
                </div>
                <p className="backlog-panel-slug">{openTopic.target_slug}</p>
                <p className="backlog-panel-meta">
                  최초 감지 · {formatDate(openTopic.first_detected_at)}
                </p>

                <div className="backlog-panel-refs">
                  <h3>인용 중인 위키 {openTopic.referencing_pages.length}</h3>
                  {openTopic.referencing_pages.length === 0 ? (
                    <p className="sub">인용 문서 없음</p>
                  ) : (
                    <ul>
                      {openTopic.referencing_pages.map((page) => (
                        <li key={page.id}>
                          <Link
                            href={`${workspacePath(workspaceId)}/wiki/${page.slug}`}
                          >
                            {page.title}
                          </Link>
                          {/* 3.1: 이 문서가 이 주제를 인용한 지점 주변의
                              문맥. 링크 밖에 둔다 — 안에 넣으면 스크린
                              리더가 발췌 전체를 링크 접근성 이름으로 읽는다.
                              서버가 이미 평문으로 펼쳐 보냈으므로 여기서는
                              그대로 렌더만 한다. */}
                          {page.excerpt ? (
                            <p className="backlog-panel-excerpt">
                              {page.excerpt}
                            </p>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="modal-foot">
                  {/* ⚠️ 목록 행의 "소스 추가"와 같은 목적지다(PRD §2.3) —
                      패널이 별도의 연결 개념을 만들지 않는다. */}
                  <Link
                    href={`${workspacePath(workspaceId)}/sources?prefillTitle=${encodeURIComponent(
                      openTopic.display_title,
                    )}&tab=text`}
                    className="button primary"
                  >
                    소스 추가
                  </Link>
                </div>
              </>
            ) : null}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
