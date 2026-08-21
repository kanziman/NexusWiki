"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Plus, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Dropzone } from "@/components/Dropzone";
import { JobStepper } from "@/components/JobStepper";
import { formatDate, formatRelativeTime } from "@/lib/relative-time";
import { createClient } from "@/lib/supabase/client";
import { workspacePath } from "@/lib/workspace-path";

export type SourceRow = {
  id: string;
  title: string;
  source_type: string;
  mime_type?: string | null;
  byte_size?: number | null;
  created_at: string;
  content_hash: string;
};

export type ChunkStat = { count: number; charStart: number; charEnd: number };
export type CitingPage = { title: string; slug: string };

export type SourcesListProps = {
  workspaceId: string;
  initialSources: SourceRow[];
  chunkStats?: Record<string, ChunkStat>;
  citingPages?: Record<string, CitingPage[]>;
  prefillTitle?: string;
  initialTab?: "text";
};

const EMPTY_HEADING = "아직 등록된 소스가 없습니다";
const EMPTY_BODY =
  "파일을 드래그하거나 URL/텍스트를 붙여넣어 첫 소스를 추가하세요.";

const SELECT_COLUMNS =
  "id,title,source_type,mime_type,byte_size,created_at,content_hash";

function formatBytes(bytes?: number | null): string | null {
  if (bytes === null || bytes === undefined) return null;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

type MimeFilter = "all" | "pdf" | "text_md";

// PRD §3.2: 탭 축은 mime_type 이다. source_type 은 사용자가 고르는 값이라
// 포맷과 어긋날 수 있어(url 로 수집했는데 실체는 PDF) 탭 축으로 쓰지 않는다 —
// 행 안의 메타데이터로만 표시한다.
function isPdf(source: SourceRow): boolean {
  return (
    source.mime_type === "application/pdf" ||
    source.title.toLowerCase().endsWith(".pdf")
  );
}

function isTextMd(source: SourceRow): boolean {
  return (
    source.mime_type === "text/plain" ||
    source.mime_type === "text/markdown" ||
    ["text", "clipping", "article"].includes(source.source_type) ||
    source.title.toLowerCase().endsWith(".md") ||
    source.title.toLowerCase().endsWith(".txt")
  );
}

function formatLabel(source: SourceRow): { label: string; variant: string } {
  if (isPdf(source)) return { label: "PDF", variant: "pdf" };
  if (source.mime_type === "text/markdown" || source.title.endsWith(".md")) {
    return { label: "MD", variant: "md" };
  }
  return { label: "TXT", variant: "" };
}

export function SourcesList({
  workspaceId,
  initialSources,
  chunkStats = {},
  citingPages = {},
  prefillTitle,
  initialTab,
}: SourcesListProps) {
  const [sources, setSources] = useState<SourceRow[]>(initialSources);
  const [activeMime, setActiveMime] = useState<MimeFilter>("all");
  const [query, setQuery] = useState("");
  // RedLinkCta 가 심은 prefillTitle/tab 으로 들어오면 업로드 모달이 닫힌 채
  // 도착한다 — 그러면 그 링크가 아무 일도 하지 않는 것처럼 보인다.
  const [uploadOpen, setUploadOpen] = useState(
    Boolean(prefillTitle) || initialTab === "text",
  );

  async function handleIngested(_jobId: string, rawSourceId: string) {
    const supabase = createClient();
    const { data } = await supabase
      .from("raw_sources")
      .select(SELECT_COLUMNS)
      .eq("id", rawSourceId)
      .single<SourceRow>();

    if (data) {
      setSources((prev) => [data, ...prev]);
      setUploadOpen(false);
    }
  }

  const searched = query.trim()
    ? sources.filter((source) =>
        source.title.toLowerCase().includes(query.trim().toLowerCase()),
      )
    : sources;

  const filteredSources = searched.filter((source) => {
    if (activeMime === "all") return true;
    if (activeMime === "pdf") return isPdf(source);
    return isTextMd(source);
  });

  const pdfCount = sources.filter(isPdf).length;
  const textMdCount = sources.filter(isTextMd).length;
  const totalChunks = Object.values(chunkStats).reduce(
    (sum, stat) => sum + stat.count,
    0,
  );
  const indexedCount = sources.filter(
    (source) => (chunkStats[source.id]?.count ?? 0) > 0,
  ).length;

  const TABS: { id: MimeFilter; label: string }[] = [
    { id: "all", label: `전체 ${sources.length}` },
    { id: "pdf", label: `PDF ${pdfCount}` },
    { id: "text_md", label: `텍스트/마크다운 ${textMdCount}` },
  ];

  return (
    <div className="content sources">
      <section className="hero" data-od-id="source-management-header">
        <div>
          {/* eyebrow(`SOURCE PIPELINE · DATABASE & RLS`)를 두지 않는다 —
              "DATABASE & RLS"는 내부 구현 용어라 사용자에게 의미가 없다. */}
          <h1>원문 소스 관리</h1>
          <p>
            등록된 원본의 청킹, 5채널 인덱싱 상태와 위키 인용 관계를 관리합니다.
          </p>
        </div>
        <button
          type="button"
          className="button primary"
          onClick={() => setUploadOpen(true)}
          data-od-id="upload-open"
        >
          <Plus size={14} aria-hidden="true" />
          <span>소스 업로드</span>
        </button>
      </section>

      <section className="stats" data-od-id="pipeline-stats">
        <div className="stat">
          <b>{sources.length}</b>
          <span>총 등록 소스</span>
        </div>
        <div className="stat">
          <b>{totalChunks}</b>
          <span>생성된 청크</span>
        </div>
        {/* ⚠️ "100% 정상" 같은 단정은 쓰지 않는다 — 인덱싱 실패 여부는 잡
            테이블이 알고 이 조회에는 없다. 셀 수 있는 것만 센다. */}
        <div className="stat">
          <b>
            {indexedCount}/{sources.length}
          </b>
          <span>청크 생성 완료 소스</span>
        </div>
      </section>

      <section data-od-id="source-table-section">
        <div className="toolbar">
          <nav className="tabs" role="tablist" aria-label="파일 형식 필터">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={activeMime === tab.id}
                onClick={() => setActiveMime(tab.id)}
                className={`tab ${activeMime === tab.id ? "active" : ""}`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
          <input
            className="field search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="파일명으로 검색"
            aria-label="파일명으로 검색"
          />
        </div>

        {filteredSources.length === 0 ? (
          <div className="table-wrap p-8 text-center">
            <b className="block text-[13px]">
              {sources.length === 0
                ? EMPTY_HEADING
                : "해당 조건의 소스가 없습니다"}
            </b>
            <span className="mt-1 block text-[11px] text-[var(--muted)]">
              {sources.length === 0
                ? EMPTY_BODY
                : "다른 형식 탭을 선택하거나 검색어를 지우세요."}
            </span>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="table" id="sources-library">
              {/* ⚠️ 프로토타입(26/27/14/15/12/6)에서 의도적으로 벗어난 값이다.
                  프로토타입의 파이프라인 칸은 정적 레이블 하나지만 앱은 진행률
                  막대와 취소·재시도 버튼을 함께 싣는다 — 15% 로는 상태 문구가
                  한 글자씩 세로로 접힌다. 남는 폭은 말줄임이 이미 걸려 있는
                  두 칸(소스 파일·연결된 위키)에서 가져온다. 액션 칸도 6% 로는
                  "상세 보기"가 두 줄이 되어 행 높이를 늘린다. */}
              <colgroup>
                <col style={{ width: "23%" }} />
                <col style={{ width: "17%" }} />
                <col style={{ width: "13%" }} />
                <col style={{ width: "25%" }} />
                <col style={{ width: "12%" }} />
                <col style={{ width: "10%" }} />
              </colgroup>
              <thead>
                <tr>
                  <th scope="col">소스 파일</th>
                  <th scope="col">연결된 위키 문서</th>
                  <th scope="col">청크 및 좌표</th>
                  <th scope="col">파이프라인 상태</th>
                  <th scope="col">업로드</th>
                  <th scope="col">
                    <span className="sr-only">작업</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredSources.map((source) => {
                  const format = formatLabel(source);
                  const size = formatBytes(source.byte_size);
                  const stat = chunkStats[source.id];
                  const cited = citingPages[source.id] ?? [];

                  return (
                    <tr key={source.id}>
                      <td>
                        <div className="file">
                          <span className={`format ${format.variant}`}>
                            {format.label}
                          </span>
                          <div className="min-w-0">
                            <b title={source.title} aria-label={source.title}>
                              {source.title}
                            </b>
                            <span>
                              {size ? `${size} · ` : ""}
                              {source.source_type}
                            </span>
                          </div>
                        </div>
                      </td>

                      <td>
                        {cited.length === 0 ? (
                          <span className="sub">인용한 위키 없음</span>
                        ) : (
                          <div className="doc-chips">
                            {cited.map((page) => (
                              <Link
                                key={page.slug}
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
                        {stat ? (
                          <>
                            <b className="mono text-[12px]">
                              {stat.count} 청크
                            </b>
                            <span className="sub">
                              {stat.charStart.toLocaleString("ko-KR")}–
                              {stat.charEnd.toLocaleString("ko-KR")} char
                            </span>
                          </>
                        ) : (
                          <span className="sub">청크 없음</span>
                        )}
                      </td>

                      <td>
                        <JobStepper
                          workspaceId={workspaceId}
                          rawSourceId={source.id}
                        />
                      </td>

                      <td>
                        {formatRelativeTime(source.created_at)}
                        <span className="sub">
                          {formatDate(source.created_at)}
                        </span>
                      </td>

                      <td>
                        <Link
                          href={`${workspacePath(workspaceId)}/sources/${source.id}`}
                          className="text-button"
                        >
                          상세 보기
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

      {/* PRD §3.5 업로드 모달. 시작 버튼은 없다 — 업로드 즉시 백그라운드
          청킹·인덱싱 큐에 진입한다(불변식 §2). */}
      <Dialog.Root open={uploadOpen} onOpenChange={setUploadOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="modal-backdrop fixed inset-0" />
          <Dialog.Content className="modal fixed top-1/2 left-1/2 max-h-[86vh] -translate-x-1/2 -translate-y-1/2 overflow-auto">
            <div className="modal-head">
              <Dialog.Title>소스 업로드</Dialog.Title>
              <Dialog.Close asChild>
                <button type="button" className="icon-btn" aria-label="닫기">
                  <X size={16} aria-hidden="true" />
                </button>
              </Dialog.Close>
            </div>
            <Dropzone
              workspaceId={workspaceId}
              onIngested={handleIngested}
              prefillTitle={prefillTitle}
              initialTab={initialTab}
            />
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
