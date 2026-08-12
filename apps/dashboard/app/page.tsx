import { redirect } from "next/navigation";

import { workspacePath } from "@/lib/workspace-path";
import { createClient } from "@/lib/supabase/server";

// 루트 경로는 "테넌시 진입점"이다 — 사용자를 자신의 첫 워크스페이스로 보낸다.
// middleware.ts가 이미 `/`를 게이트하지 않으므로(matcher는 /w/:path*, /login만
// 포함) 여기서 user가 null일 수 있다는 걱정은 하지 않는다: 이 페이지는 로그인
// 여부와 무관하게 항상 렌더링되고, 미인증 사용자는 아래에서 user가 없을 때
// 자연히 "워크스페이스 없음" 문구를 보게 된다 — 별도 리다이렉트 분기를 두지
// 않는 것은 로그인 상태 판정을 이 파일과 middleware.ts 두 곳에서 하지 않기
// 위해서다(D-02 boundary와의 중복 방지).
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
      .select("id")
      .order("created_at")
      .limit(1);

    if (workspaces && workspaces.length > 0) {
      redirect(workspacePath(workspaces[0].id));
    }
  }

  return (
    <main
      style={{
        display: "flex",
        minHeight: "100vh",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--spacing-lg)",
      }}
    >
      <p style={{ font: "var(--font-body-md)", color: "var(--color-body)" }}>
        워크스페이스가 없습니다 — 관리자에게 초대를 요청하세요.
      </p>
    </main>
  );
}
