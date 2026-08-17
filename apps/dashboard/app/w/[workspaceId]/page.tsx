import Link from "next/link";

import {
  EmptyState,
  PageHeader,
  SectionHeading,
} from "@/components/DashboardPrimitives";
import { createClient } from "@/lib/supabase/server";
import { workspacePath } from "@/lib/workspace-path";

type Props = { params: Promise<{ workspaceId: string }> };

export default async function WorkspaceHomePage({ params }: Props) {
  const { workspaceId } = await params;
  const supabase = await createClient();
  const base = workspacePath(workspaceId);
  const [workspaceResult, sourcesResult, pagesResult] = await Promise.all([
    supabase.from("workspaces").select("name").eq("id", workspaceId).single(),
    supabase
      .from("raw_sources")
      .select("id,title,source_type")
      .eq("workspace_id", workspaceId)
      .order("created_at", { ascending: false })
      .limit(5),
    supabase
      .from("wiki_pages")
      .select("id,title,slug")
      .eq("workspace_id", workspaceId)
      .order("updated_at", { ascending: false })
      .limit(5),
  ]);
  const sources = sourcesResult.data ?? [];
  const pages = pagesResult.data ?? [];

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-xxl">
      <PageHeader
        title={workspaceResult.data?.name ?? "워크스페이스"}
        description="자료를 등록하고, 질문하며, 쌓인 지식을 탐색하세요."
        action={
          <div className="flex flex-wrap gap-sm">
            <Link
              href={`${base}/sources`}
              className="nw-action nw-focus-ring px-base py-sm"
            >
              자료 추가
            </Link>
            <Link
              href={`${base}/ask`}
              className="nw-focus-ring border border-[var(--nw-rule-strong)] px-base py-sm"
            >
              질문하기
            </Link>
          </div>
        }
      />
      {sources.length === 0 && pages.length === 0 ? (
        <EmptyState
          title="첫 자료를 등록하세요"
          detail="등록한 원문이 위키와 질문의 근거가 됩니다."
        />
      ) : (
        <div className="grid gap-xxl md:grid-cols-2">
          <Activity
            title="최근 자료"
            empty="최근 등록한 자료가 없습니다."
            items={sources.map((source) => ({
              id: source.id,
              label: source.title,
              href: `${base}/sources`,
              detail: source.source_type,
            }))}
          />
          <Activity
            title="최근 위키"
            empty="아직 생성된 위키 페이지가 없습니다."
            items={pages.map((page) => ({
              id: page.id,
              label: page.title,
              href: `${base}/wiki/${page.slug}`,
              detail: "위키 페이지",
            }))}
          />
        </div>
      )}
    </div>
  );
}

function Activity({
  title,
  empty,
  items,
}: {
  title: string;
  empty: string;
  items: { id: string; label: string; href: string; detail: string }[];
}) {
  return (
    <section>
      <SectionHeading title={title} />
      {items.length === 0 ? (
        <p className="mt-base text-[var(--nw-muted)]">{empty}</p>
      ) : (
        <ul className="mt-base border-y border-[var(--nw-rule)]">
          {items.map((item) => (
            <li
              key={item.id}
              className="border-b border-[var(--nw-rule)] last:border-b-0"
            >
              <Link
                href={item.href}
                className="nw-focus-ring flex justify-between gap-sm px-sm py-base"
              >
                <span>{item.label}</span>
                <span className="text-[var(--nw-muted)]">{item.detail}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
