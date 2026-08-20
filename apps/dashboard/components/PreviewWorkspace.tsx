"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  ChevronRight,
  CircleAlert,
  FileText,
  HelpCircle,
  Home,
  LogOut,
  Plus,
  Search,
  Upload,
  Users,
} from "lucide-react";

import {
  previewAskAnswer,
  previewBacklog,
  previewMembers,
  previewSources,
  previewUser,
  previewWikiPages,
  previewWorkspace,
} from "@/lib/preview-data";

type PreviewWorkspaceProps = { path: string[] };
type Notice = "저장" | "업로드" | "초대" | "로그아웃" | "워크스페이스 생성";

const categories = [
  ["all", "전체"],
  ["concepts", "개념"],
  ["entities", "엔티티"],
  ["guides", "가이드"],
  ["maps", "맵"],
] as const;

const navigation = [
  { href: "/preview", label: "홈 대시보드", icon: Home, screen: "home" },
  {
    href: "/preview/sources",
    label: "원문 소스",
    icon: Upload,
    screen: "sources",
  },
  { href: "/preview/ask", label: "질문하기", icon: HelpCircle, screen: "ask" },
  { href: "/preview/wiki", label: "위키 문서", icon: FileText, screen: "wiki" },
  {
    href: "/preview/backlog",
    label: "미완성 백로그",
    icon: CircleAlert,
    screen: "backlog",
  },
  {
    href: "/preview/settings",
    label: "팀원 & 역할 관리",
    icon: Users,
    screen: "settings",
  },
] as const;

function previewScreen(path: string[]) {
  if (path[0] === "sources") return "sources";
  if (path[0] === "ask") return "ask";
  if (path[0] === "wiki") return "wiki";
  if (path[0] === "backlog") return "backlog";
  if (path[0] === "settings") return "settings";
  return "home";
}

function PreviewNotice({ action }: { action: Notice }) {
  return (
    <p
      role="status"
      className="rounded-sm bg-[var(--soft)] px-sm py-xs text-sm text-[var(--fg)]"
    >
      미리보기에서는 {action}되지 않습니다.
    </p>
  );
}

export function PreviewWorkspace({ path }: PreviewWorkspaceProps) {
  const screen = previewScreen(path);
  const [notice, setNotice] = useState<Notice | null>(null);

  return (
    <div className="app min-h-screen" data-preview-mode="true">
      <aside className="sidebar" aria-label="미리보기 주요 메뉴">
        <div
          className="switcher cursor-default"
          data-od-id="preview-workspace-switcher"
        >
          <span className="switcher-mark">N</span>
          <span className="switcher-name">{previewWorkspace.name}</span>
        </div>
        <p className="px-base pt-base text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
          LOCAL PREVIEW
        </p>
        <nav className="nav-stack" aria-label="미리보기 탐색">
          {navigation.map(({ href, label, icon: Icon, screen: navScreen }) => (
            <Link
              key={href}
              href={href}
              className={`nav-item ${screen === navScreen ? "active" : ""}`}
              aria-current={screen === navScreen ? "page" : undefined}
            >
              <Icon className="nav-icon" aria-hidden="true" />
              <span>{label}</span>
            </Link>
          ))}
        </nav>
        <button
          type="button"
          className="mx-base mt-base flex items-center gap-sm text-sm font-semibold text-[var(--muted)]"
          onClick={() => setNotice("워크스페이스 생성")}
        >
          <Plus size={15} aria-hidden="true" />새 워크스페이스 생성
        </button>
        <div className="profile">
          <div className="avatar">민</div>
          <div className="profile-text">
            <strong>{previewUser.name}</strong>
            <span>{previewUser.email}</span>
          </div>
        </div>
      </aside>

      <div className="workspace flex min-w-0 flex-1 flex-col">
        <header className="topbar">
          <div className="crumb">
            <strong>{previewWorkspace.name}</strong>
            <span className="ml-sm rounded-full bg-[var(--soft)] px-xs py-xxs text-[10px] font-semibold text-[var(--muted)]">
              로컬 미리보기
            </span>
          </div>
          <div className="top-actions">
            <Link href="/preview/sources" className="button">
              소스 추가
            </Link>
            <Link href="/preview/ask" className="button primary">
              질문 시작
            </Link>
            <button
              type="button"
              className="icon-btn"
              aria-label="미리보기 로그아웃"
              onClick={() => setNotice("로그아웃")}
            >
              <LogOut size={16} aria-hidden="true" />
            </button>
          </div>
        </header>
        <main className="workspace-main flex-1">
          {notice ? (
            <div className="mx-auto max-w-[1200px] px-base pt-base">
              <PreviewNotice action={notice} />
            </div>
          ) : null}
          {screen === "home" ? <PreviewHome /> : null}
          {screen === "sources" ? (
            <PreviewSources onAction={setNotice} />
          ) : null}
          {screen === "ask" ? <PreviewAsk /> : null}
          {screen === "wiki" ? <PreviewWiki slug={path[1]} /> : null}
          {screen === "backlog" ? (
            <PreviewBacklog onAction={setNotice} />
          ) : null}
          {screen === "settings" ? (
            <PreviewSettings onAction={setNotice} />
          ) : null}
        </main>
      </div>
    </div>
  );
}

function PreviewHome() {
  const [category, setCategory] =
    useState<(typeof categories)[number][0]>("all");
  const visiblePages =
    category === "all"
      ? previewWikiPages
      : previewWikiPages.filter((page) => page.category === category);

  return (
    <div className="content">
      <section className="context">
        <div>
          <p className="eyebrow">WORKSPACE · LOCAL REVIEW</p>
          <div className="title-row">
            <h1>NexusWiki 제품 탐색</h1>
          </div>
          <p>
            원문과 컴파일된 위키가 연결되는 제품 흐름을 목업 데이터로
            검토합니다.
          </p>
        </div>
      </section>
      <section className="stats" aria-label="미리보기 현황">
        <Stat value="04" label="컴파일된 문서" />
        <Stat value="03" label="연결된 원문 소스" />
        <Stat value="02" label="작성 대기 항목" />
        <Stat value="오늘" label="최종 업데이트" />
      </section>
      <section className="ask-hero" aria-labelledby="preview-ask-heading">
        <div>
          <p className="eyebrow">ASK NEXUSWIKI</p>
          <h2 id="preview-ask-heading">근거와 함께 지식을 탐색하세요</h2>
          <p>질문과 인용 흐름은 목업 답변으로 직접 확인할 수 있습니다.</p>
        </div>
        <Link href="/preview/ask" className="button primary">
          질문하기
        </Link>
      </section>
      <section className="toolbar" aria-label="문서 카테고리 필터">
        <div className="chips">
          {categories.map(([value, label]) => (
            <button
              key={value}
              type="button"
              className="chip"
              aria-pressed={category === value}
              onClick={() => setCategory(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </section>
      <section className="sections">
        <div>
          <SectionHead
            title="컴파일된 위키 문서"
            count={visiblePages.length}
            href="/preview/wiki"
          />
          <div className="doc-list">
            {visiblePages.map((page) => (
              <Link
                key={page.id}
                href={`/preview/wiki/${page.slug}`}
                className="doc"
              >
                <div className="doc-body">
                  <span className="doc-title">{page.title}</span>
                  <span className="doc-meta">
                    {page.category} · 인용 원문 {page.sourceCount}개
                  </span>
                </div>
                <ChevronRight className="nav-icon" aria-hidden="true" />
              </Link>
            ))}
          </div>
        </div>
        <div className="backlog">
          <SectionHead
            title="작성 대기 백로그"
            count={previewBacklog.length}
            href="/preview/backlog"
          />
          <div className="doc-list">
            {previewBacklog.map((item) => (
              <Link key={item.slug} href="/preview/backlog" className="doc">
                <div className="doc-body">
                  <span className="doc-title">{item.title}</span>
                  <span className="doc-meta">
                    위키 {item.references}곳에서 인용됨 · {item.firstDetected}{" "}
                    감지
                  </span>
                </div>
                <ChevronRight className="nav-icon" aria-hidden="true" />
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function PreviewSources({ onAction }: { onAction: (action: Notice) => void }) {
  return (
    <div className="content">
      <PageHero
        eyebrow="SOURCES · ORIGINAL EVIDENCE"
        title="원문 소스"
        body="위키를 만든 원문 자료와 처리 상태를 확인합니다."
      />
      <section className="source-line mb-lg">
        <div>
          <b>새 자료 추가</b>
          <span>업로드와 URL 수집은 미리보기에서 저장되지 않습니다.</span>
        </div>
        <button
          type="button"
          className="button primary"
          onClick={() => onAction("업로드")}
        >
          소스 업로드
        </button>
      </section>
      <section className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>원문</th>
              <th>형식</th>
              <th>상태</th>
              <th>업데이트</th>
            </tr>
          </thead>
          <tbody>
            {previewSources.map((source) => (
              <tr key={source.id}>
                <td>
                  <b>{source.title}</b>
                </td>
                <td>{source.type}</td>
                <td>
                  <span className="badge">{source.status}</span>
                </td>
                <td className="sub">{source.updatedAt}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function PreviewAsk() {
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState(false);
  const [evidence, setEvidence] = useState<"wiki" | "source">("wiki");
  const wiki = previewWikiPages.find(
    (page) => page.slug === previewAskAnswer.wikiSlug,
  )!;
  const source = previewSources.find(
    (item) => item.id === previewAskAnswer.sourceId,
  )!;
  const answerQuestion = asked
    ? question.trim() || previewAskAnswer.question
    : previewAskAnswer.question;

  return (
    <div className="ask-layout" data-od-id="preview-ask-screen">
      <section className="conversation">
        <div className="conversation-head">
          <p className="eyebrow">ASK NEXUSWIKI</p>
          <h1>무엇이든 물어보세요</h1>
          <p>목업 답변과 인용을 통해 검토 흐름을 확인하세요.</p>
        </div>
        <div className="thread">
          <p className="user">{answerQuestion}</p>
          <article className="answer">
            <div className="answer-head">
              <span className="dot" aria-hidden="true" />
              <b>NexusWiki</b>
              <span>목업 답변</span>
            </div>
            <p>{previewAskAnswer.answer}</p>
            <div className="mt-base flex flex-wrap gap-sm">
              <button
                type="button"
                className="doc-chip"
                onClick={() => setEvidence("wiki")}
              >
                위키 · {wiki.title}
              </button>
              <button
                type="button"
                className="doc-chip"
                onClick={() => setEvidence("source")}
              >
                원문 · {source.title}
              </button>
            </div>
          </article>
        </div>
        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            setAsked(true);
          }}
        >
          <label className="sr-only" htmlFor="preview-question">
            질문
          </label>
          <div className="compose-inner">
            <input
              id="preview-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="예: 이 제품의 핵심 가치는 무엇인가요?"
            />
            <button type="submit" className="send" aria-label="질문하기">
              →
            </button>
          </div>
        </form>
      </section>
      <aside className="inspect" aria-label="인용 근거">
        <div className="inspect-head">
          <div className="inspect-title">
            <h2>근거 보기</h2>
            <span className="kicker">EVIDENCE VIEWER</span>
          </div>
          <div className="tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={evidence === "wiki"}
              className={`tab ${evidence === "wiki" ? "active" : ""}`}
              onClick={() => setEvidence("wiki")}
            >
              위키 문서
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={evidence === "source"}
              className={`tab ${evidence === "source" ? "active" : ""}`}
              onClick={() => setEvidence("source")}
            >
              원문 소스
            </button>
          </div>
        </div>
        <div className="inspect-body">
          <div className="card">
            {evidence === "wiki" ? (
              <>
                <span className="kicker">COMPILED WIKI</span>
                <h3>{wiki.title}</h3>
                {wiki.content.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
                <Link href={`/preview/wiki/${wiki.slug}`} className="link">
                  전체 문서 열기 →
                </Link>
              </>
            ) : (
              <>
                <span className="kicker">RAW SOURCE · CHUNK 03</span>
                <h3>{source.title}</h3>
                <p>원문 청크 03 · 1,240–1,834자</p>
                <pre className="code">
                  사용자는 요약만이 아니라, 답변을 뒷받침하는 원문과 위키 문서를
                  함께 확인할 수 있어야 한다.
                </pre>
              </>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}

function PreviewWiki({ slug }: { slug?: string }) {
  const [query, setQuery] = useState("");
  const selected = slug
    ? previewWikiPages.find((page) => page.slug === slug)
    : null;
  const pages = useMemo(
    () =>
      previewWikiPages.filter((page) =>
        `${page.title} ${page.content.join(" ")}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [query],
  );
  if (selected) return <PreviewWikiReader page={selected} />;
  return (
    <div className="content">
      <PageHero
        eyebrow="WIKI · COMPILED KNOWLEDGE"
        title="위키 문서"
        body="원문에서 컴파일된 지식을 탐색하고 인용 근거를 확인합니다."
      />
      <section className="toolbar">
        <div className="field search flex items-center gap-sm">
          <Search size={15} aria-hidden="true" />
          <input
            className="w-full bg-transparent outline-none"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="제목이나 내용으로 검색"
            aria-label="위키 문서 검색"
          />
        </div>
      </section>
      <section className="doc-list">
        {pages.map((page) => (
          <Link
            key={page.id}
            href={`/preview/wiki/${page.slug}`}
            className="doc"
          >
            <div className="doc-body">
              <span className="doc-title">{page.title}</span>
              <span className="doc-meta">
                {page.category} ·{" "}
                {page.verificationStatus === "verified"
                  ? "검증됨"
                  : "부분 검증"}
              </span>
              <p className="doc-excerpt">{page.content[0]}</p>
            </div>
            <ChevronRight className="nav-icon" aria-hidden="true" />
          </Link>
        ))}
      </section>
    </div>
  );
}

function PreviewWikiReader({
  page,
}: {
  page: (typeof previewWikiPages)[number];
}) {
  return (
    <article className="content reader">
      <Link href="/preview/wiki" className="text-button">
        ← 위키 문서
      </Link>
      <p className="eyebrow mt-lg">
        {page.category} ·{" "}
        {page.verificationStatus === "verified" ? "검증됨" : "부분 검증"}
      </p>
      <h1>{page.title}</h1>
      {page.content.map((paragraph) => (
        <p key={paragraph} className="text-lg leading-8">
          {paragraph}
        </p>
      ))}
      <section className="source-line mt-xl">
        <div>
          <b>인용 원문 {page.sourceCount}개</b>
          <span>미리보기에서는 목업 인용만 표시합니다.</span>
        </div>
        <Link href="/preview/ask" className="button">
          질문에서 확인
        </Link>
      </section>
    </article>
  );
}

function PreviewBacklog({ onAction }: { onAction: (action: Notice) => void }) {
  return (
    <div className="content backlog">
      <PageHero
        eyebrow="BACKLOG · RED LINKS"
        title="미완성 백로그"
        body="위키에서 참조되었지만 아직 작성되지 않은 지식을 확인합니다."
      />
      <section className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>백로그 주제</th>
              <th>인용 빈도</th>
              <th>최초 감지</th>
              <th>
                <span className="sr-only">작업</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {previewBacklog.map((item) => (
              <tr key={item.slug}>
                <td>
                  <b>{item.title}</b>
                  <span className="sub block">{item.slug}</span>
                </td>
                <td>
                  <b className="impact">{item.references}</b>회
                </td>
                <td>{item.firstDetected}</td>
                <td>
                  <button
                    type="button"
                    className="button compact"
                    onClick={() => onAction("업로드")}
                  >
                    소스 추가
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function PreviewSettings({ onAction }: { onAction: (action: Notice) => void }) {
  return (
    <div className="content settings">
      <PageHero
        eyebrow="WORKSPACE CONTROL · RBAC"
        title="워크스페이스 설정"
        body="목업 멤버와 권한 구성을 검토합니다."
      />
      <section className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>멤버</th>
              <th>이메일</th>
              <th>역할</th>
            </tr>
          </thead>
          <tbody>
            {previewMembers.map((member) => (
              <tr key={member.email}>
                <td>
                  <b>{member.name}</b>
                </td>
                <td>{member.email}</td>
                <td>
                  <span className="badge">{member.role}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <div className="mt-lg flex gap-sm">
        <button
          type="button"
          className="button"
          onClick={() => onAction("초대")}
        >
          멤버 초대
        </button>
        <button
          type="button"
          className="button primary"
          onClick={() => onAction("저장")}
        >
          설정 저장
        </button>
      </div>
    </div>
  );
}

function PageHero({
  eyebrow,
  title,
  body,
}: {
  eyebrow: string;
  title: string;
  body: string;
}) {
  return (
    <section className="hero">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{body}</p>
      </div>
    </section>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="stat">
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}

function SectionHead({
  title,
  count,
  href,
}: {
  title: string;
  count: number;
  href: string;
}) {
  return (
    <div className="section-head">
      <h2>
        {title}
        <span>{String(count).padStart(2, "0")}</span>
      </h2>
      <Link href={href} className="text-button">
        전체 보기 →
      </Link>
    </div>
  );
}
