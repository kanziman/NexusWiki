import { AskConversation } from "@/components/AskConversation";
import { ContentViewer } from "@/components/ContentViewer";

type AskPageProps = {
  params: Promise<{ workspaceId: string }>;
};

// UI-04 Ask 라우트 — 통합 워크스페이스 뷰어 셸로 승격되었다: 좌측 대화
// (AskConversation) + 우측 콘텐츠 뷰어(ContentViewer, 위키/소스/그래프/
// 마인드맵 탭)를 한 화면에 나란히 렌더링한다. 이 파일 자신은 Server
// Component로 얇게 남는다 — SSE 스트림 상태와 탭/대상 쿼리 파라미터 상태는
// 둘 다 클라이언트에서만 살 수 있으므로, 실제 렌더링은 두 클라이언트
// 컴포넌트에 전담한다.
//
// 관련: openspec/changes/archive/2026-08-14-add-unified-workspace-viewer
// (unified-workspace-viewer 스펙)
export default async function AskPage({ params }: AskPageProps) {
  const { workspaceId } = await params;
  return (
    <div className="flex w-full flex-col gap-xl lg:h-[calc(100vh-var(--spacing-xxl)*2)] lg:flex-row">
      <div className="lg:flex-[2] lg:overflow-y-auto">
        <AskConversation workspaceId={workspaceId} />
      </div>
      <div className="lg:flex-[3] lg:overflow-y-auto">
        <ContentViewer workspaceId={workspaceId} />
      </div>
    </div>
  );
}
