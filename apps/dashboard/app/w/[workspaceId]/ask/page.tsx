import { AskConversation } from "@/components/AskConversation";
import { ContentViewer } from "@/components/ContentViewer";

type AskPageProps = {
  params: Promise<{ workspaceId: string }>;
};

// UI-04 Ask 라우트 — 통합 워크스페이스 뷰어 셸: 좌측 대화(AskConversation) +
// 우측 인용 인스펙터(ContentViewer, 위키/소스/그래프/마인드맵 탭)를 한 화면에
// 나란히 렌더링한다. 이 파일 자신은 Server Component로 얇게 남는다 — SSE 스트림
// 상태와 탭/대상 쿼리 파라미터 상태는 둘 다 클라이언트에서만 살 수 있으므로,
// 실제 렌더링은 두 클라이언트 컴포넌트에 전담한다.
//
// ⚠️ 2열 그리드는 이 라우트가 소유한다(.ask-layout). 프로토타입은 앱 셸의 .app
// 을 4열로 바꾸지만, .app 은 WorkspaceShell 이 소유하고 모든 라우트가 공유한다 —
// 리더(섹션 15)와 같은 판정이다. nexuswiki-design-system.css 섹션 16 참고.
//
// 관련: openspec/changes/archive/2026-08-14-add-unified-workspace-viewer
// (unified-workspace-viewer 스펙)
export default async function AskPage({ params }: AskPageProps) {
  const { workspaceId } = await params;
  return (
    <div className="ask-layout" data-od-id="ask-conversation-screen">
      <AskConversation workspaceId={workspaceId} />
      <ContentViewer workspaceId={workspaceId} />
    </div>
  );
}
