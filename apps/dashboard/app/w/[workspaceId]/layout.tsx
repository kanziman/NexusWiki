import { redirect } from "next/navigation";
import type { ReactNode } from "react";

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

  const { data: workspace, error } = await supabase
    .from("workspaces")
    .select("id,name")
    .eq("id", workspaceId)
    .single();

  if (error || !workspace) {
    redirect("/");
  }

  return (
    <div style={{ minHeight: "100vh" }}>
      <header
        style={{
          borderBottom: "1px solid var(--color-hairline)",
          padding: "var(--spacing-base) var(--spacing-lg)",
        }}
      >
        <h1 style={{ font: "var(--font-title-md)", margin: 0 }}>
          {workspace.name}
        </h1>
      </header>
      <main style={{ padding: "var(--spacing-lg)" }}>{children}</main>
    </div>
  );
}
