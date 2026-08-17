import { redirect } from "next/navigation";

import { PageHeader } from "@/components/DashboardPrimitives";
import { SettingsMembersPanel } from "@/components/SettingsMembersPanel";
import { createClient } from "@/lib/supabase/server";

type SettingsPageProps = {
  params: Promise<{ workspaceId: string }>;
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

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-xl">
      <PageHeader
        title="설정"
        description="워크스페이스 멤버와 운영 상태를 관리합니다."
      />
      <SettingsMembersPanel
        workspaceId={workspaceId}
        currentUserId={user.id}
        currentRole={membership?.role ?? "viewer"}
        workspaceName={workspace?.name ?? ""}
        workspaceSlug={workspace?.slug ?? ""}
      />
    </div>
  );
}
