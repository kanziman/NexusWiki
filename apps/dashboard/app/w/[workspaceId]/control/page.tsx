import { ControlRoom } from "@/components/ControlRoom";

type ControlPageProps = {
  params: Promise<{ workspaceId: string }>;
};

// 구현 추적: openspec/changes/ai-control-flow-accounting
export default async function ControlPage({ params }: ControlPageProps) {
  const { workspaceId } = await params;
  return <ControlRoom workspaceId={workspaceId} />;
}
