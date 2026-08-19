import { redirect } from "next/navigation";

import { WorkspaceEntryChooser } from "@/components/WorkspaceEntryChooser";
import { WorkspaceOnboarding } from "@/components/WorkspaceOnboarding";
import { createPersonalWorkspace } from "@/app/onboarding-actions";
import { workspacePath } from "@/lib/workspace-path";
import { createClient } from "@/lib/supabase/server";

// 루트 경로는 "테넌시 진입점"이다 — 요청자 자신에게 보이는 워크스페이스 수에
// 따라 직접 진입하거나 선택 화면을 표시한다.
// middleware.ts의 matcher가 `/`를 포함하므로 미인증 요청은 이 컴포넌트에
// 도달하기 전에 이미 /login으로 리다이렉트된다 — 아래 `if (user)` 분기는
// 그 게이트를 다시 판정하지 않고 통과를 전제로 워크스페이스 개수만 나눈다.
// 로그인 상태 판정을 이 파일과 middleware.ts 두 곳에서 하지 않는 것은
// D-02 boundary와의 중복 방지를 위해서다.
export default async function HomePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user) {
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
  }

  return <WorkspaceOnboarding createWorkspace={createPersonalWorkspace} />;
}
