"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import type { AnchorPart } from "@/lib/citation-anchors";
import { createClient } from "@/lib/supabase/client";

export type CitationSidePanelProps = {
  part: AnchorPart | null;
  onClose: () => void;
  /**
   * 위키 카드에서 `/w/[workspaceId]/wiki/[slug]`로 링크하기 위한 선택적
   * workspaceId — Task 3의 `<action>`이 이 링크를 요구하지만 `CitationSidePanelProps`
   * 자체는 `{part, onClose}` 2개 필드만 명시한다. `AskConversation`은 자신의
   * `workspaceId` prop을 그대로 흘려 링크를 활성화하고, 이 prop이 없어도
   * (예: 단독 사용) 패널은 링크 없이 정상 동작한다 — Rule 2(누락된 부가 기능)
   * 관점의 최소 확장이며 필수 계약(part/onClose)은 그대로 둔다.
   */
  workspaceId?: string;
};

type WikiCardData = {
  id: string;
  title: string;
  slug: string;
  content: string;
};
type SourceCardData = {
  id: string;
  raw_source_id: string;
  chunk_index: number;
  char_start: number;
  char_end: number;
  content: string;
};

// 06-UI-SPEC.md "UI Considerations" long-text/citation-side-panel 행 — 고정
// ~400px max-height + 내부 스크롤. WINDOWS #11(이 프로젝트의 커스텀
// --spacing-* @theme 오버라이드가 max-w-*/w-*/h-* 이름 있는 유틸리티와 충돌)을
// 피하기 위해 클래스가 아니라 인라인 style 리터럴로 지정한다(GraphCanvas.tsx와
// 동일한 회피 패턴).
const EXCERPT_MAX_HEIGHT = "400px";
const PANEL_WIDTH = "400px";

/**
 * 인용 사이드 패널 — 클릭된 마커의 정확한 {kind, id}로만 위키 페이지 또는
 * 원문 청크를 조회한다 (T-06-19, must_haves.prohibitions).
 *
 * 관련 태스크: 06-06-PLAN.md Task 3
 * 설계 근거: 06-UI-SPEC.md "UI Considerations" citation-side-panel 행,
 *            03-03-PLAN.md의 content[char_start:char_end] 왕복 속성
 *
 * ⚠️ `char_start`/`char_end`는 이 청크 자신의 content 안 오프셋이 아니라 원본
 * raw_source 전체 기준 좌표다(`source_chunks.content`가 이미 그 슬라이스 자체).
 * 부분 문자열 하이라이트를 시도하려면 부모 raw_source content를 다시 페치해야
 * 하므로(사이드 패널 발췌 범위 밖) 청크 전체를 하나의 인용 단위로 하이라이트한다.
 */
export function CitationSidePanel({
  part,
  onClose,
  workspaceId,
}: CitationSidePanelProps) {
  const [wiki, setWiki] = useState<WikiCardData | null>(null);
  const [source, setSource] = useState<SourceCardData | null>(null);
  const markRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    setWiki(null);
    setSource(null);
    if (!part || !part.id) return;

    // 널 체크로 좁혀진 part를 명시적 인자로 넘긴다 — 중첩 함수 안에서
    // `part!.id`처럼 non-null assertion을 다시 쓰지 않기 위해서다(그러면 아래
    // `.eq("id", part.id)`가 T-06-19 수용기준의 grep 패턴과 문자 그대로
    // 일치한다).
    async function load(part: AnchorPart) {
      const supabase = createClient();
      if (part.kind === "wiki") {
        const { data } = await supabase
          .from("wiki_pages")
          .select("id,title,slug,content")
          .eq("id", part.id)
          .single();
        if (!cancelled && data) setWiki(data as WikiCardData);
      } else {
        const { data } = await supabase
          .from("source_chunks")
          .select("id,raw_source_id,chunk_index,char_start,char_end,content")
          .eq("id", part.id)
          .single();
        if (!cancelled && data) setSource(data as SourceCardData);
      }
    }

    load(part);
    return () => {
      cancelled = true;
    };
  }, [part]);

  useEffect(() => {
    markRef.current?.scrollIntoView({ block: "center" });
  }, [wiki, source]);

  if (!part) return null;

  return (
    <div
      role="dialog"
      aria-label="인용 상세"
      data-testid="citation-side-panel"
      className="fixed top-0 right-0 z-10 flex h-full flex-col gap-base border-l border-hairline bg-canvas p-lg shadow-[var(--shadow-modal)]"
      style={{ width: PANEL_WIDTH }}
    >
      <div className="flex items-center justify-between">
        <span className="text-ink" style={{ font: "var(--font-title-md)" }}>
          {part.kind === "wiki" ? "위키" : "원문"} 인용
        </span>
        <button
          type="button"
          aria-label="닫기"
          onClick={onClose}
          className="flex h-11 w-11 items-center justify-center rounded-sm text-muted"
        >
          ✕
        </button>
      </div>

      {part.kind === "wiki" ? (
        wiki ? (
          <div
            className="overflow-y-auto rounded-md border border-hairline p-base"
            style={{ maxHeight: EXCERPT_MAX_HEIGHT }}
          >
            <p className="text-ink" style={{ font: "var(--font-title-md)" }}>
              {wiki.title}
            </p>
            <p
              ref={(node) => {
                markRef.current = node;
              }}
              className="text-body"
              style={{ font: "var(--font-body-md)" }}
            >
              {wiki.content}
            </p>
            {workspaceId ? (
              <Link
                href={`/w/${workspaceId}/wiki/${wiki.slug}`}
                className="text-primary"
                style={{ font: "var(--font-caption)", fontWeight: 600 }}
              >
                위키 페이지에서 전체 보기
              </Link>
            ) : null}
          </div>
        ) : null
      ) : source ? (
        <div
          className="overflow-y-auto rounded-md border border-hairline p-base"
          style={{ maxHeight: EXCERPT_MAX_HEIGHT }}
        >
          <p
            className="text-muted"
            style={{ font: "var(--font-caption)", fontWeight: 600 }}
          >
            {`청크 #${source.chunk_index} · 원문 좌표 ${source.char_start}–${source.char_end}`}
          </p>
          <mark
            ref={(node) => {
              markRef.current = node;
            }}
            className="bg-surface-soft text-body"
            style={{ font: "var(--font-body-md)" }}
          >
            {source.content}
          </mark>
        </div>
      ) : null}
    </div>
  );
}
