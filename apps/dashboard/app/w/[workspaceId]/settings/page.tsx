import { redirect } from "next/navigation";

import { SettingsMembersPanel } from "@/components/SettingsMembersPanel";
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

  return (
    <SettingsMembersPanel workspaceId={workspaceId} currentUserId={user.id} />
  );
}
