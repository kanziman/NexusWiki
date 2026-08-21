"use client";

import Link from "next/link";
import { Fragment, useState } from "react";

import { FavoriteButton } from "@/components/FavoriteButton";
import { RedLinkCta } from "@/components/RedLinkCta";
import { apiFetch } from "@/lib/api-client";
import { verificationLabel } from "@/lib/verification-label";
import { workspacePath } from "@/lib/workspace-path";
import { resolveWikiLinks } from "@/lib/wiki-links";

// UI-SPEC Copywriting Contract "Wiki viewer (UI-05)" — 문구를 한 글자도 바꾸지 않는다.
const READ_ONLY_BANNER =
  "이 페이지는 컴파일됩니다 — 직접 편집할 수 없으며, 소스가 갱신되면 다시 컴파일됩니다.";
// ⚠️ 상태 이름은 lib/verification-label.ts 에서 파생한다. 예전에는 여기만
// "충돌 감지됨"이라 홈·라이브러리의 "충돌 감지"와 갈렸고, 이 문자열이 위
// Copywriting Contract 의 보호 대상이라 못 고친다고 판단했었다 — 확인해 보니
// 그 계약 문서는 리포지토리에 없다(`grep -rl "Copywriting Contract" docs/` 0건).
// 뒤에 붙는 설명은 이 화면 고유의 확장이라 그대로 둔다.
const DISPUTED_CALLOUT = `${verificationLabel({ disputed: true })} — 상충하는 정보가 있습니다. 원문을 확인하세요.`;
const VERIFY_ACTION_LABEL = "검증됨으로 표시";
const VERIFY_FAILURE_MESSAGE = "검증 처리에 실패했습니다. 다시 시도해주세요.";

// workspace-home-prd.md 카테고리 표시명 매핑 — wiki_pages.category CHECK 4종 고정.
const CATEGORY_LABELS: Record<string, string> = {
  concepts: "개념",
  entities: "엔티티",
  guides: "가이드",
  maps: "맵",
};

type WikiPage = {
  id: string;
  title: string;
  content: string;
  category: string;
  verification_status: string;
  verified_by: string | null;
  verified_at: string | null;
  expires_at: string | null;
  disputed: boolean;
};

export type WikiPageContentProps = {
  page: WikiPage;
  links: { target_slug: string; resolved: boolean }[];
  workspaceId: string;
  canVerify: boolean;
  initialBookmarked: boolean;
};

type VerifyResponse = {
  id: string;
  slug: string;
  verification_status: string;
  verified_by: string | null;
  verified_at: string | null;
  expires_at: string | null;
  disputed: boolean;
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/**
 * 읽기 전용 위키 뷰어 본체 — 읽기전용 배너, 검증/충돌 콜아웃, WikiLink
 * 네비게이션을 렌더링한다. 이 파일 트리 전체에서 유일한 쓰기 경로는 검증
 * 상태 전이 PATCH뿐이며, 페이지 본문을 직접 고치는 어떤 경로도 존재하지
 * 않는다 — v1은 자유 편집을 구조적으로 지원하지 않는다
 * (REQUIREMENTS.md Out of Scope, PROJECT.md Key Decisions).
 *
 * 관련 태스크: 06-07-PLAN.md Task 2
 * 설계 근거: apps/api/src/api/routers/wiki.py (verify 엔드포인트 요청/응답 형태),
 *            06-UI-SPEC.md Color/Typography/Copywriting Contract
 *
 * 렌더 순서(위→아래)가 이 컴포넌트의 안전 계약이다: 충돌 콜아웃은 항상 본문보다
 * 먼저 나온다 — 사용자가 상충 경고를 못 보고 본문을 먼저 읽는 경로를 원천적으로
 * 없앤다(T-06-22 대응, 06-07-PLAN.md must_haves.prohibitions).
 */
export function WikiPageContent({
  page,
  links,
  workspaceId,
  canVerify,
  initialBookmarked,
}: WikiPageContentProps) {
  const [status, setStatus] = useState(page.verification_status);
  const [verifiedAt, setVerifiedAt] = useState(page.verified_at);
  const [expiresAt, setExpiresAt] = useState(page.expires_at);
  const [disputed, setDisputed] = useState(page.disputed);
  const [submitting, setSubmitting] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  async function handleVerify() {
    if (submitting) return;
    setSubmitting(true);
    setVerifyError(null);

    try {
      const result = await apiFetch<VerifyResponse>(
        `/workspaces/${workspaceId}/wiki/${page.id}/verify`,
        { method: "PATCH", body: { verification_status: "verified" } },
      );
      setStatus(result.verification_status);
      setVerifiedAt(result.verified_at);
      setExpiresAt(result.expires_at);
      setDisputed(result.disputed);
    } catch {
      // 문서화된 오류 형태별 분기가 필요할 만큼 다양한 실패 사유가 없다 —
      // Dropzone.tsx의 GENERIC_ERROR_MESSAGE 패턴과 동일하게 단일 재시도
      // 안내로 뭉갠다.
      setVerifyError(VERIFY_FAILURE_MESSAGE);
    } finally {
      setSubmitting(false);
    }
  }

  const isExpired =
    expiresAt !== null && new Date(expiresAt).getTime() < Date.now();

  const headings = extractHeadings(page.content);
  const relatedLinks = [
    ...new Map(
      links
        .filter((link) => link.resolved)
        .map((link) => [link.target_slug, link]),
    ).values(),
  ];

  return (
    <div className="reader-layout">
      <article className="reader">
        {/* ⚠️ .eyebrow 를 쓰지 않는다. 이 프로젝트의 유일하게 남은 맥락 라벨이자
            장식이 아닌 진짜 탐색 요소다(다른 다섯 화면의 eyebrow 는 제거됐다).
            .eyebrow 는 대문자 변환·넓은 자간·모노스페이스라 한국어에 맞지 않는다 —
            uppercase 는 한국어에 무효이고 .11em 자간은 자모를 벌려 읽기 나쁘다. */}
        <nav aria-label="위키 탐색 경로" className="breadcrumb-path">
          위키 / {page.category}
        </nav>

        <div className="title-row">
          <h1>{page.title}</h1>
          {/* key로 wiki 전환마다 강제 재마운트 — 아니면 같은 컴포넌트
              인스턴스가 재사용돼(특히 독립 리더 라우트는 페이지 전환 시
              언마운트를 강제하는 loading 경계가 없다) 이전 문서의
              bookmarked 상태가 다음 문서로 새면서 그대로 남는다. */}
          <FavoriteButton
            key={page.id}
            wikiId={page.id}
            workspaceId={workspaceId}
            initialBookmarked={initialBookmarked}
          />
        </div>

        {/* 1. 읽기전용 배너 + 상태 배지. 문구는 UI-SPEC 카피 계약이라
            한 글자도 바꾸지 않는다. */}
        <div className="governance">
          <span className="tag">
            {CATEGORY_LABELS[page.category] ?? page.category}
          </span>
          {/* 2/3. 충돌 콜아웃(항상 최우선) 또는 검증 상태 콜아웃 — 이 블록은
              항상 아래 본문 렌더 블록보다 파일/DOM 순서상 먼저 나온다. */}
          {disputed ? (
            <span className="badge" style={{ color: "var(--danger)" }}>
              {DISPUTED_CALLOUT}
            </span>
          ) : (
            <VerificationCallout
              status={status}
              verifiedAt={verifiedAt}
              expiresAt={expiresAt}
              isExpired={isExpired}
            />
          )}
        </div>

        <p className="mt-[14px] mb-0 text-[11px] text-[var(--muted)]">
          {READ_ONLY_BANNER}
        </p>

        {/* 5. 검증 액션 — editor 이상만(canVerify는 page.tsx가 서버에서 계산해
            내려준다; 이 버튼의 노출 여부는 UX 편의일 뿐, 실제 권한 경계는
            wiki.py의 RLS 기반 UPDATE 정책이다, T-06-21). */}
        {canVerify ? (
          <div className="mt-4 flex flex-col gap-1">
            <button
              type="button"
              onClick={handleVerify}
              disabled={submitting}
              className="button primary self-start"
            >
              {VERIFY_ACTION_LABEL}
            </button>
            {verifyError !== null ? (
              <p role="alert" className="invite-feedback error show">
                {verifyError}
              </p>
            ) : null}
          </div>
        ) : null}

        {/* 6. 본문 — 전체 컴파일 문서를 자르지 않고 그대로 자연스럽게 흘려보낸다
            ("read the whole page" 표면, UI-SPEC overflow/wiki-page-content). */}
        <div className="article mt-7">
          <DocumentBody
            content={page.content}
            links={links}
            workspaceId={workspaceId}
          />
        </div>

        {relatedLinks.length ? (
          <section
            className="mt-9 border-t border-[var(--border)] pt-6"
            aria-labelledby="related-wiki-heading"
          >
            <h2
              id="related-wiki-heading"
              className="m-0 text-[15px] font-extrabold"
            >
              관련 문서
            </h2>
            <ul className="mt-3 flex flex-wrap gap-2">
              {relatedLinks.map((link) => (
                <li key={link.target_slug}>
                  <Link
                    className="doc-chip"
                    href={`${workspacePath(workspaceId)}/wiki/${link.target_slug}`}
                  >
                    {link.target_slug.replace(/-/g, " ")}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </article>

      {/* 우측 목차 패널. 960px 이하에서는 CSS 가 감춘다 — 본문을 좁히지 않는다
          (openspec/changes/restore-standalone-wiki-reader 의 목차 요구사항). */}
      <aside className="toc">
        <div className="toc-heading">
          <h2>목차</h2>
        </div>
        {headings.length ? (
          <nav aria-label="이 문서에서" className="toc-list">
            {headings.map((heading) => (
              <a key={heading.id} href={`#${heading.id}`}>
                {heading.title}
              </a>
            ))}
          </nav>
        ) : (
          <p className="m-0 text-[11px] text-[var(--muted)]">
            제목이 없는 문서입니다.
          </p>
        )}
      </aside>
    </div>
  );
}

function extractHeadings(content: string) {
  return content.split("\n").flatMap((line, index) => {
    const match = /^(#{1,3})\s+(.+?)\s*$/.exec(line);
    return match ? [{ id: `section-${index}`, title: match[2] }] : [];
  });
}

function DocumentBody({
  content,
  links,
  workspaceId,
}: {
  content: string;
  links: { target_slug: string; resolved: boolean }[];
  workspaceId: string;
}) {
  return (
    <>
      {content.split("\n").map((line, index) => {
        const heading = /^(#{1,3})\s+(.+?)\s*$/.exec(line);
        const parts = resolveWikiLinks(heading ? heading[2] : line, links);
        const children = parts.map((part, partIndex) =>
          part.type === "text" ? (
            <Fragment key={partIndex}>{part.value}</Fragment>
          ) : part.resolved ? (
            <Link
              key={partIndex}
              href={`${workspacePath(workspaceId)}/wiki/${part.slug}`}
              className="cite"
            >
              {part.title}
            </Link>
          ) : (
            <RedLinkCta
              key={partIndex}
              title={part.title}
              slug={part.slug}
              workspaceId={workspaceId}
            />
          ),
        );
        if (heading) {
          const Tag =
            heading[1].length === 1
              ? "h2"
              : heading[1].length === 2
                ? "h3"
                : "h4";
          return (
            <Tag key={index} id={`section-${index}`} className="scroll-mt-6">
              {children}
            </Tag>
          );
        }
        return (
          <Fragment key={index}>
            {children}
            {index < content.split("\n").length - 1 ? "\n" : null}
          </Fragment>
        );
      })}
    </>
  );
}

type VerificationCalloutProps = {
  status: string;
  verifiedAt: string | null;
  expiresAt: string | null;
  isExpired: boolean;
};

// ⚠️ verifiedBy(계정 UUID)는 의도적으로 prop에서 받지 않는다. 이 컴포넌트에는
// UUID를 표시명으로 바꿀 조회 경로가 없어, 넘겨받아도 화면에는 못 쓴다 — 안
// 쓰는 prop을 시그니처에 남겨 두면 다음 사람이 "표시할 수 있는데 안 하나?"로
// 헷갈린다.
function VerificationCallout({
  status,
  verifiedAt,
  expiresAt,
  isExpired,
}: VerificationCalloutProps) {
  if (status === "verified" && !isExpired) {
    // ⚠️ 검증자를 표시하지 않는다. `verified_by`는 auth 사용자 UUID이고 이
    // 라우트에는 그것을 이름으로 바꿀 조회 경로가 없다 — 그대로 찍으면 화면에
    // 36자짜리 식별자가 남아 정작 읽어야 할 검증 날짜를 밀어낸다. 사람이 읽을
    // 이름을 붙이려면 표시명 조회가 먼저 필요하고, 그건 이 화면 밖의 일이다.
    const dateLabel = verifiedAt !== null ? formatDate(verifiedAt) : "";
    return (
      <span className="badge verified">
        {`${verificationLabel({ verification_status: "verified" })}${dateLabel ? ` · ${dateLabel}` : ""}`}
      </span>
    );
  }

  if (status === "verified" && isExpired) {
    // isExpired가 true인 분기이므로 expiresAt는 사실상 항상 non-null이지만,
    // prop 시그니처가 string | null이라 렌더 시점에 한 번 더 널가드한다.
    // ⚠️ 상태 이름은 모듈에서 파생한다 — 목록 화면이 같은 문서를 부르는 말과
    // 갈리면 안 된다. 뒤의 날짜·안내는 이 화면 고유의 확장이다.
    const dateLabel = expiresAt !== null ? formatDate(expiresAt) : "";
    const stateName = verificationLabel({
      verification_status: "verified",
      expires_at: expiresAt ?? "1970-01-01T00:00:00Z",
    });
    return (
      <span className="badge" style={{ color: "var(--danger)" }}>
        {`${stateName}${dateLabel ? ` · ${dateLabel} 이후 재검증 필요` : " · 재검증 필요"}`}
      </span>
    );
  }

  if (status === "partial") {
    // UI-SPEC에 partial 전용 문구가 없다 — expired-style(warning-text) 처리를
    // 이 컴포넌트의 합리적 확장으로 채택한다(06-07-PLAN.md Task 2 <action>).
    // ⚠️ 상태 이름 자체는 lib/verification-label.ts 에서 파생한다. 예전에는
    // 여기만 "부분 검증됨"이라 홈·라이브러리의 "부분 검증"과 갈렸다. 뒤에
    // 붙는 안내 문구는 이 화면 고유의 확장이라 그대로 둔다.
    return (
      <span className="badge">
        {verificationLabel({ verification_status: "partial" })} · 재검증이
        필요합니다
      </span>
    );
  }

  // "unverified" — UI-SPEC은 중립 기본 상태로 명시적 콜아웃을 요구하지 않는다.
  return null;
}
