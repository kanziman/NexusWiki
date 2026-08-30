import { redirect } from "next/navigation";

import { PublicLandingPage } from "@/components/PublicLandingPage";
import { WorkspaceEntryChooser } from "@/components/WorkspaceEntryChooser";
import { WorkspaceOnboarding } from "@/components/WorkspaceOnboarding";
import { createPersonalWorkspace } from "@/app/onboarding-actions";
import { workspacePath } from "@/lib/workspace-path";
import { createClient } from "@/lib/supabase/server";

export default async function HomePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // 미인증 방문자에게는 공개 랜딩 & 라이브 쇼케이스 페이지를 노출한다.
  if (!user) {
    return <PublicLandingPage />;
  }

  // RLS(workspaces_select_member)가 요청자 소속 워크스페이스로만 좁혀 준다 —
  // owner_id 필터를 추가하면 non-owner 멤버 워크스페이스가 숨어버리므로 넣지 않는다.
  const { data: workspaces } = await supabase
    .from("workspaces")
    .select("id,name")
    .order("name");

  if (workspaces?.length === 1) {
    redirect(workspacePath(workspaces[0].id));
  }

  if (workspaces && workspaces.length > 1) {
    return <WorkspaceEntryChooser workspaces={workspaces} />;
  }

  return <WorkspaceOnboarding createWorkspace={createPersonalWorkspace} />;
}
