"use client";

import { File, FileText, Link2 } from "lucide-react";
import { useState } from "react";

import { Dropzone } from "@/components/Dropzone";
import {
  DetailHeader,
  EmptyState,
  PageHeader,
  StatusBadge,
} from "@/components/DashboardPrimitives";
import { JobStepper } from "@/components/JobStepper";
import { createClient } from "@/lib/supabase/client";

export type SourceRow = {
  id: string;
  title: string;
  source_type: string;
  created_at: string;
  content_hash: string;
};

export type SourcesListProps = {
  workspaceId: string;
  initialSources: SourceRow[];
  // RedLinkCta.handleCreate가 심는 ?prefillTitle=&tab=text를 page.tsx가 읽어
  // 여기로 넘긴다 — Dropzone까지 이어져야 06-REVIEW.md CR-01의 실제 동작이
  // 완성된다.
  prefillTitle?: string;
  initialTab?: "text";
};

// UI-SPEC Copywriting Contract "Empty state heading/body" — 문구를 한 글자도
// 바꾸지 않는다.
const EMPTY_HEADING = "아직 등록된 소스가 없습니다";
const EMPTY_BODY =
  "파일을 드래그하거나 URL/텍스트를 붙여넣어 첫 소스를 추가하세요.";

const SOURCE_ICONS: Record<string, typeof File> = {
  file: File,
  url: Link2,
  text: FileText,
};

const SELECT_COLUMNS = "id,title,source_type,created_at,content_hash";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/**
 * 소스 목록 클라이언트 래퍼 — Dropzone(등록) + 소스별 JobStepper(진행)를
 * 한 화면에 묶는다.
 *
 * 관련 태스크: 06-05-PLAN.md Task 3
 * 설계 근거: supabase/migrations/0004_rls_policies.sql 섹션 5
 *            (raw_sources_select_member — apps/api를 거치지 않는 직접 읽기)
 *
 * [Rule 3] page.tsx는 <action>이 명시한 대로 Server Component로 유지해야
 * 하지만, Dropzone.onIngested로 새 소스를 로컬 state에 prepend하려면 클라이언트
 * state가 필요하다 — Server Component는 state를 가질 수 없으므로 이 얇은
 * 클라이언트 래퍼로 분리했다 (SettingsMembersPanel.tsx와 같은 계열, 06-03-SUMMARY.md
 * Deviation 3 참고).
 */
export function SourcesList({
  workspaceId,
  initialSources,
  prefillTitle,
  initialTab,
}: SourcesListProps) {
  const [sources, setSources] = useState<SourceRow[]>(initialSources);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Dropzone.onIngested는 (jobId, rawSourceId) 두 인자만 준다(Task 1의 고정된
  // 시그니처) — title/source_type/created_at은 여기서 다시 조회해야 한다.
  // apps/api의 _insert_and_enqueue가 잡을 인큐하기 전에 이미 raw_sources 행을
  // 커밋했으므로(sources.py), 이 시점에는 행이 이미 존재한다. 목록 전체를
  // 다시 읽지 않고(limit(50) 재조회가 아니다) 이 한 행만 targeted select로
  // 가져와 앞에 붙인다 — "without a full refetch" 요구를 그대로 만족한다.
  async function handleIngested(_jobId: string, rawSourceId: string) {
    const supabase = createClient();
    const { data } = await supabase
      .from("raw_sources")
      .select(SELECT_COLUMNS)
      .eq("id", rawSourceId)
      .single<SourceRow>();

    if (data) {
      setSources((prev) => [data, ...prev]);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-xxl">
      <PageHeader
        title="Sources"
        description="생각의 근거가 되는 자료를 모으고, 연결하고, 다시 찾으세요."
      />

      <Dropzone
        workspaceId={workspaceId}
        onIngested={handleIngested}
        prefillTitle={prefillTitle}
        initialTab={initialTab}
      />

      {sources.length === 0 ? (
        <EmptyState title={EMPTY_HEADING} detail={EMPTY_BODY} />
      ) : (
        <ul
          id="sources-library"
          className="flex flex-col border-y border-[var(--nw-rule)]"
        >
          {sources.map((source) => {
            const Icon = SOURCE_ICONS[source.source_type] ?? File;
            return (
              <li
                key={source.id}
                className="flex flex-col gap-base border-b border-[var(--nw-rule)] py-lg last:border-b-0"
              >
                <div className="flex flex-col gap-sm sm:flex-row sm:items-center">
                  <div className="flex min-w-0 flex-1 items-center gap-sm">
                    <Icon
                      size={18}
                      aria-hidden="true"
                      className="shrink-0 text-[var(--nw-muted)]"
                    />
                    <span
                      title={source.title}
                      aria-label={source.title}
                      className="min-w-0 flex-1 truncate text-base font-semibold tracking-[-0.02em] text-[var(--nw-ink)]"
                    >
                      {source.title}
                    </span>
                  </div>
                  <div className="flex items-center gap-sm">
                    <StatusBadge>{formatDate(source.created_at)}</StatusBadge>
                    <button
                      type="button"
                      className="nw-focus-ring rounded-sm border border-[var(--nw-rule-strong)] px-sm py-xs text-sm text-[var(--nw-ink)]"
                      aria-expanded={selectedId === source.id}
                      aria-controls={`source-detail-${source.id}`}
                      onClick={() =>
                        setSelectedId((current) =>
                          current === source.id ? null : source.id,
                        )
                      }
                    >
                      {selectedId === source.id ? "접기" : "상세 보기"}
                    </button>
                  </div>
                </div>
                <JobStepper workspaceId={workspaceId} rawSourceId={source.id} />
                {selectedId === source.id ? (
                  <section
                    id={`source-detail-${source.id}`}
                    className="border-t border-[var(--nw-rule)] pt-lg"
                  >
                    <DetailHeader
                      libraryHref="#sources-library"
                      libraryLabel="자료 목록"
                      kind={source.source_type}
                      title={source.title}
                      meta={
                        <StatusBadge>
                          {formatDate(source.created_at)}
                        </StatusBadge>
                      }
                    />
                    <dl className="mt-lg grid gap-sm text-sm sm:grid-cols-2">
                      <div>
                        <dt className="text-[var(--nw-muted)]">유형</dt>
                        <dd className="mt-xs text-[var(--nw-ink)]">
                          {source.source_type}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-[var(--nw-muted)]">등록일</dt>
                        <dd className="mt-xs text-[var(--nw-ink)]">
                          {formatDate(source.created_at)}
                        </dd>
                      </div>
                    </dl>
                  </section>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
