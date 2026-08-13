import { redirect } from "next/navigation";

import { workspacePath } from "@/lib/workspace-path";

type GraphPageProps = {
  params: Promise<{ workspaceId: string }>;
};

// UI-06 그래프 캔버스 라우트 — 통합 워크스페이스 뷰어(`/ask?tab=graph`)로
// 리다이렉트한다 (openspec/changes/archive/2026-08-14-add-unified-workspace-viewer).
// 실제 렌더링(GraphCanvas/GraphLensFilter)은 ContentViewer의 graph 탭이
// 그대로 재사용한다 — 이 파일은 더 이상 데이터를 조회하지 않는다.
export default async function GraphPage({ params }: GraphPageProps) {
  const { workspaceId } = await params;
  redirect(`${workspacePath(workspaceId)}/ask?tab=graph`);
}
