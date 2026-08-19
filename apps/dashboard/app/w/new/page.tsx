import { WorkspaceOnboarding } from "@/components/WorkspaceOnboarding";
import { createPersonalWorkspace } from "@/app/onboarding-actions";
import { createClient } from "@/lib/supabase/server";

// 소속 워크스페이스가 1개 이상인 사용자가 추가로 워크스페이스를 만드는
// 유일한 진입점이다. `/`는 소속 개수에 따라 자동으로 리다이렉트/선택
// 화면을 보여주므로(§6.1) 이미 워크스페이스가 있는 사용자는 그 경로로
// WorkspaceOnboarding에 도달할 수 없다 — WorkspaceSwitcher의
// "새 워크스페이스 생성" 링크는 이 라우트를 가리킨다.
// 상한 판정의 정본은 onboarding-actions.ts의 createPersonalWorkspace다.
// 여기서 보여주는 문구는 표시용이며, 서버 액션이 다시 개수를 세어 최종
// 판정한다 — 두 판정이 어긋나도(레이스) 실제 생성 경로는 안전하다.
export default async function NewWorkspacePage() {
  const supabase = await createClient();
  const { data: workspaces } = await supabase.from("workspaces").select("id");

  if ((workspaces?.length ?? 0) >= 3) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-sm p-lg text-center">
        <h1 className="m-0 text-ink" style={{ font: "var(--font-display-lg)" }}>
          워크스페이스는 최대 3개까지 만들 수 있습니다
        </h1>
        <p
          className="max-w-[360px] text-muted"
          style={{ font: "var(--font-body-md)" }}
        >
          더 만들려면 기존 워크스페이스를 정리하거나 팀원에게 초대를 요청하세요.
        </p>
      </main>
    );
  }

  return <WorkspaceOnboarding createWorkspace={createPersonalWorkspace} />;
}
