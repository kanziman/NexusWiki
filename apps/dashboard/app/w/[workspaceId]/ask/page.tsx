import { AskConversation } from "@/components/AskConversation";

type AskPageProps = {
  params: Promise<{ workspaceId: string }>;
};

// UI-04 Ask 라우트. 이 파일 자신은 Server Component로 얇게 남는다 — SSE
// 스트림 상태는 클라이언트에서만 살 수 있으므로(EventSource 미사용,
// fetch+ReadableStream), 대화 상태/empty-state 렌더링은 AskConversation.tsx가
// 전담한다. sources/page.tsx(06-05)와 같은 얇은 wrapper 패턴.
export default async function AskPage({ params }: AskPageProps) {
  const { workspaceId } = await params;
  return <AskConversation workspaceId={workspaceId} />;
}
