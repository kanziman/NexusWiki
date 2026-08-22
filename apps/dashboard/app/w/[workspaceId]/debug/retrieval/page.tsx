import { RetrievalDebugViewer } from "@/components/RetrievalDebugViewer";

type RetrievalDebugPageProps = {
  params: Promise<{ workspaceId: string }>;
};

// 구현 추적: openspec/changes/retrieval-debug-viewer
export default async function RetrievalDebugPage({
  params,
}: RetrievalDebugPageProps) {
  const { workspaceId } = await params;
  return <RetrievalDebugViewer workspaceId={workspaceId} />;
}
