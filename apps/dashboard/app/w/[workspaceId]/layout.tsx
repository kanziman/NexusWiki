import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { WorkspaceShell } from "@/components/WorkspaceShell";
import { createClient } from "@/lib/supabase/server";

type WorkspaceLayoutProps = {
  children: ReactNode;
  params: Promise<{ workspaceId: string }>;
};

// `/w/[workspaceId]`는 테넌시의 단일 진실 소스다(UI-01) — 이 레이아웃이 요청자
// 세션으로 워크스페이스를 직접 읽어(RLS 강제) 실제 이름을 보여주는 것 자체가
// 06-01의 트레이서 증거다.
//
// T-06-02 (Information Disclosure, D-12 상속): RLS가 0행을 돌려주면
// "존재하지 않음"과 "멤버 아님"을 구분하지 않고 동일하게 `/`로 리다이렉트한다 —
// apps/api/src/api/errors.py의 _render_isolation_failure와 같은 원칙.
export default async function WorkspaceLayout({
  children,
  params,
}: WorkspaceLayoutProps) {
  const { workspaceId } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { data: workspace, error } = await supabase
    .from("workspaces")
    .select("id,name")
    .eq("id", workspaceId)
    .single();

  if (error || !workspace) {
    redirect("/");
  }

  // Task 2: 스위처가 보여줄 전체 목록 — .eq 필터가 없다. RLS
  // workspaces_select_member가 이미 요청자가 멤버인 워크스페이스로만
  // scoping하므로, 이 두 번째 조회는 위의 단일 행 조회(현재 워크스페이스
  // 존재/멤버십 판정)와 다른 목적이며 그대로 남는다 — 하나로 합치면
  // "현재 워크스페이스가 존재하지 않음"과 "목록이 비어 있음"을 구분할 수
  // 없게 된다.
  const { data: workspaces } = await supabase
    .from("workspaces")
    .select("id,name")
    .order("name");

  return (
    <WorkspaceShell
      workspace={workspace}
      workspaces={workspaces ?? []}
      currentWorkspaceId={workspaceId}
      accountEmail={user?.email ?? "계정"}
    >
      {children}
    </WorkspaceShell>
  );
}
