import { redirect } from "next/navigation";

import { SettingsMembersPanel } from "@/components/SettingsMembersPanel";
import { createClient } from "@/lib/supabase/server";

type SettingsPageProps = {
  params: Promise<{ workspaceId: string }>;
};

const ROLE_LABELS: Record<string, string> = {
  owner: "소유자",
  editor: "편집자",
  viewer: "뷰어",
};

export default async function SettingsPage({ params }: SettingsPageProps) {
  const { workspaceId } = await params;
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const [membershipResult, workspaceResult] = await Promise.all([
    supabase
      .from("workspace_members")
      .select("role")
      .eq("workspace_id", workspaceId)
      .eq("user_id", user.id)
      .maybeSingle(),
    supabase
      .from("workspaces")
      .select("name,slug")
      .eq("id", workspaceId)
      .maybeSingle(),
  ]);

  const membership = membershipResult.data;
  const workspace = workspaceResult.data;
  const currentRole = membership?.role ?? "viewer";

  return (
    <div className="content settings">
      <section className="hero" data-od-id="settings-header">
        <div>
          <p className="eyebrow">WORKSPACE CONTROL · RBAC</p>
          <h1>워크스페이스 설정</h1>
          <p>워크스페이스 멤버와 운영 상태를 관리합니다.</p>
        </div>
        {/* 역할 표기는 UX 안내일 뿐이다 — 실제 차단은 RLS 와 API 의
            _require_operations_role 이 한다(PRD §3.1). */}
        <div className="role-note" data-od-id="current-role-note">
          현재 역할 <b>{ROLE_LABELS[currentRole] ?? currentRole}</b>
        </div>
      </section>

      <SettingsMembersPanel
        workspaceId={workspaceId}
        currentUserId={user.id}
        currentRole={currentRole}
        workspaceName={workspace?.name ?? ""}
        workspaceSlug={workspace?.slug ?? ""}
      />
    </div>
  );
}
