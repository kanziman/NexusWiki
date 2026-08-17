import { redirect } from "next/navigation";

import { SettingsMembersPanel } from "@/components/SettingsMembersPanel";
import { PageHeader } from "@/components/DashboardPrimitives";
import { createClient } from "@/lib/supabase/server";

type SettingsPageProps = {
  params: Promise<{ workspaceId: string }>;
};

// D-04: 멤버 초대는 모달이 아니라 이 페이지("전용 폼")다. 요청자 세션으로
// 자신의 user.id를 얻는 것 외에는 이 파일이 직접 하는 일이 없다 — 멤버
// 로스터/초대 폼의 실제 렌더링과 상호작용은 SettingsMembersPanel(클라이언트
// 컴포넌트)에 위임한다.
export default async function SettingsPage({ params }: SettingsPageProps) {
  const { workspaceId } = await params;
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    // 도달 불가 — middleware.ts가 /w/:path*를 이미 로그인 여부로 게이트한다
    // (D-02). app/page.tsx의 같은 원칙("로그인 상태 판정을 두 곳에서 하지
    // 않는다")을 따라 이 분기는 재판정이 아니라 TS 타입을 좁히기 위한
    // 방어선이다.
    redirect("/login");
  }

  // 운영 현황 탭의 노출은 UX 방어선이다. API가 별도로 editor 이상을 강제하므로
  // 여기의 실패/미가입은 보수적으로 viewer처럼 처리해 요청을 시작하지 않는다.
  const { data: membership } = await supabase
    .from("workspace_members")
    .select("role")
    .eq("workspace_id", workspaceId)
    .eq("user_id", user.id)
    .maybeSingle();

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
      />
    </div>
  );
}
