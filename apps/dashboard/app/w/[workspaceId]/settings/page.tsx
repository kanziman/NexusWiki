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

  const [membershipResult, workspaceResult, publicSettingsResult] =
    await Promise.all([
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
      // ⚠️ 이 조회가 없으면 공개 설정 폼이 항상 기본값(꺼짐·빈 문자열)으로 뜬다.
      // 그 상태에서 저장하면 upsert 가 실제 값을 덮어써 표시명·설명이 null 이 되고
      // 켜져 있던 공개 공유가 조용히 꺼진다 — 폼이 화면에 보여준 적 없는 값으로.
      supabase
        .from("workspace_public_settings")
        .select("allow_public_sharing,public_display_name,public_description")
        .eq("workspace_id", workspaceId)
        .maybeSingle(),
    ]);

  const membership = membershipResult.data;
  const workspace = workspaceResult.data;
  const publicSettings = publicSettingsResult.data;
  const currentRole = membership?.role ?? "viewer";

  return (
    <div className="content settings">
      <section className="hero" data-od-id="settings-header">
        <div>
          {/* eyebrow(`WORKSPACE CONTROL · RBAC`)를 두지 않는다 — "RBAC"는
              내부 용어이고 h1 이 이미 화면을 설명한다. */}
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
        allowPublicSharing={publicSettings?.allow_public_sharing ?? false}
        publicDisplayName={publicSettings?.public_display_name ?? ""}
        publicDescription={publicSettings?.public_description ?? ""}
      />
    </div>
  );
}
