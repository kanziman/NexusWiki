"use client";

import Link from "next/link";
import { Fragment, useState } from "react";

import { RedLinkCta } from "@/components/RedLinkCta";
import { DetailHeader } from "@/components/DashboardPrimitives";
import { apiFetch } from "@/lib/api-client";
import { workspacePath } from "@/lib/workspace-path";
import { resolveWikiLinks } from "@/lib/wiki-links";

// UI-SPEC Copywriting Contract "Wiki viewer (UI-05)" — 문구를 한 글자도 바꾸지 않는다.
const READ_ONLY_BANNER =
  "이 페이지는 컴파일됩니다 — 직접 편집할 수 없으며, 소스가 갱신되면 다시 컴파일됩니다.";
const DISPUTED_CALLOUT =
  "충돌 감지됨 — 상충하는 정보가 있습니다. 원문을 확인하세요.";
const VERIFY_ACTION_LABEL = "검증됨으로 표시";
const VERIFY_FAILURE_MESSAGE = "검증 처리에 실패했습니다. 다시 시도해주세요.";

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
}: WikiPageContentProps) {
  const [status, setStatus] = useState(page.verification_status);
  const [verifiedBy, setVerifiedBy] = useState(page.verified_by);
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
      setVerifiedBy(result.verified_by);
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
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-xl">
      <DetailHeader
        libraryHref={`${workspacePath(workspaceId)}/wiki`}
        libraryLabel="위키 목록"
        navigationLabel="위키 탐색 경로"
        breadcrumb={`위키 / ${page.category}`}
        kind={page.category}
        title={page.title}
      />
      {/* 1. 읽기전용 배너 */}
      <p
        className="rounded-md bg-surface-soft px-base py-sm text-ink"
        style={{ font: "var(--font-body-sm)" }}
      >
        {READ_ONLY_BANNER}
      </p>

      {/* 2/3. 충돌 콜아웃(항상 최우선) 또는 검증 상태 콜아웃 — 이 블록은 항상
          아래 본문 렌더 블록보다 파일/DOM 순서상 먼저 나온다. */}
      {disputed ? (
        <p
          className="text-primary-error-text"
          style={{ font: "var(--font-caption)", fontWeight: 600 }}
        >
          {DISPUTED_CALLOUT}
        </p>
      ) : (
        <VerificationCallout
          status={status}
          verifiedBy={verifiedBy}
          verifiedAt={verifiedAt}
          expiresAt={expiresAt}
          isExpired={isExpired}
        />
      )}

      {/* 4. 페이지 제목 — Display(28px/600), UI-SPEC 2-weight cap 개정 반영 */}
      {/* 5. 검증 액션 — editor 이상만(canVerify는 page.tsx가 서버에서 계산해
          내려준다; 이 버튼의 노출 여부는 UX 편의일 뿐, 실제 권한 경계는
          wiki.py의 RLS 기반 UPDATE 정책이다, T-06-21). */}
      {canVerify ? (
        <div className="flex flex-col gap-xs">
          <button
            type="button"
            onClick={handleVerify}
            disabled={submitting}
            className="h-12 self-start rounded-sm bg-primary px-lg text-on-primary transition-colors active:bg-primary-active disabled:cursor-not-allowed disabled:bg-primary-disabled"
            style={{ font: "var(--font-button-sm)", fontWeight: 600 }}
          >
            {VERIFY_ACTION_LABEL}
          </button>
          {verifyError !== null ? (
            <p
              role="alert"
              className="text-primary-error-text"
              style={{ font: "var(--font-caption)", fontWeight: 600 }}
            >
              {verifyError}
            </p>
          ) : null}
        </div>
      ) : null}

      {headings.length ? (
        <nav
          aria-label="이 문서에서"
          className="rounded-sm bg-surface-soft p-base"
        >
          <p className="text-ink" style={{ font: "var(--font-caption)" }}>
            이 문서에서
          </p>
          <ul className="mt-xs flex flex-wrap gap-x-base gap-y-xs">
            {headings.map((heading) => (
              <li key={heading.id}>
                <a
                  className="nw-focus-ring text-primary underline"
                  href={`#${heading.id}`}
                >
                  {heading.title}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}

      {/* 6. 본문 — 전체 컴파일 문서를 자르지 않고 그대로 자연스럽게 흘려보낸다
          ("read the whole page" 표면, UI-SPEC overflow/wiki-page-content). */}
      <div
        className="text-body"
        style={{
          font: "var(--font-body-md)",
          whiteSpace: "pre-wrap",
          maxWidth: "72ch",
        }}
      >
        <DocumentBody
          content={page.content}
          links={links}
          workspaceId={workspaceId}
        />
      </div>
      {relatedLinks.length ? (
        <section
          className="border-t border-hairline pt-lg"
          aria-labelledby="related-wiki-heading"
        >
          <h2
            id="related-wiki-heading"
            className="text-ink"
            style={{ font: "var(--font-title-md)" }}
          >
            관련 문서
          </h2>
          <ul className="mt-sm flex flex-wrap gap-sm">
            {relatedLinks.map((link) => (
              <li key={link.target_slug}>
                <Link
                  className="nw-focus-ring text-primary underline"
                  href={`${workspacePath(workspaceId)}/wiki/${link.target_slug}`}
                >
                  {link.target_slug.replace(/-/g, " ")}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
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
              className="text-primary underline"
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
            <Tag
              key={index}
              id={`section-${index}`}
              className="scroll-mt-xl pt-base text-ink"
              style={{ font: "var(--font-title-md)" }}
            >
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
  verifiedBy: string | null;
  verifiedAt: string | null;
  expiresAt: string | null;
  isExpired: boolean;
};

function VerificationCallout({
  status,
  verifiedBy,
  verifiedAt,
  expiresAt,
  isExpired,
}: VerificationCalloutProps) {
  if (status === "verified" && !isExpired) {
    // UI-SPEC Copywriting Contract "Verified callout" — {verifier}/{verified_at
    // 날짜}는 실제 값으로 치환한다. 계정 삭제로 verified_by가 null이 된 경우를
    // 대비한 방어적 폴백("알 수 없음")이 있다 — 0007 verified_by 컬럼 주석 참조.
    const verifierLabel = verifiedBy ?? "알 수 없음";
    const dateLabel = verifiedAt !== null ? formatDate(verifiedAt) : "";
    return (
      <p
        className="text-success-text"
        style={{ font: "var(--font-caption)", fontWeight: 600 }}
      >
        {`검증됨 · ${verifierLabel}${dateLabel ? ` · ${dateLabel}` : ""}`}
      </p>
    );
  }

  if (status === "verified" && isExpired) {
    // UI-SPEC Copywriting Contract "Expired-verification callout" — verbatim.
    // isExpired가 true인 분기이므로 expiresAt는 사실상 항상 non-null이지만,
    // prop 시그니처가 string | null이라 렌더 시점에 한 번 더 널가드한다.
    const dateLabel = expiresAt !== null ? formatDate(expiresAt) : "";
    return (
      <p
        className="text-warning-text"
        style={{ font: "var(--font-caption)", fontWeight: 600 }}
      >
        {`검증 만료됨${dateLabel ? ` · ${dateLabel} 이후 재검증 필요` : " · 재검증 필요"}`}
      </p>
    );
  }

  if (status === "partial") {
    // UI-SPEC에 partial 전용 문구가 없다 — expired-style(warning-text) 처리를
    // 이 컴포넌트의 합리적 확장으로 채택한다(06-07-PLAN.md Task 2 <action>).
    return (
      <p
        className="text-warning-text"
        style={{ font: "var(--font-caption)", fontWeight: 600 }}
      >
        부분 검증됨 · 재검증이 필요합니다
      </p>
    );
  }

  // "unverified" — UI-SPEC은 중립 기본 상태로 명시적 콜아웃을 요구하지 않는다.
  return null;
}
