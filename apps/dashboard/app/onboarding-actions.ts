"use server";

import { createClient } from "@/lib/supabase/server";

type CreateWorkspaceResult = { workspaceId: string } | { error: string };

// 셀프서브 생성 개수 상한. auth-google-prd.md §5 에는 없는 값이라 규모가
// 커지면 재검토 대상이지만, 지금은 무제한 생성으로 인한 남용을 막는 게
// 우선이라 이 함수 안에서만 로컬로 정의한다.
const MAX_PERSONAL_WORKSPACES = 3;

function workspaceSlug(name: string, attempt: number) {
  const base =
    name
      .normalize("NFKC")
      .toLowerCase()
      .trim()
      .replace(/\s+/g, "-")
      .replace(/[^0-9a-z가-힣-]/g, "")
      .replace(/-{2,}/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80) || "workspace";

  if (attempt === 1) return base;

  const suffix = `-${attempt}`;
  return `${base.slice(0, 80 - suffix.length).replace(/-+$/, "")}${suffix}`;
}

// requester JWT로 INSERT한다. slug의 전역 UNIQUE 충돌은 RLS로 보이지 않을 수 있어
// DB를 최종 정본으로 삼고 숫자 접미사로 재시도한다.
export async function createPersonalWorkspace(
  submittedName: string,
): Promise<CreateWorkspaceResult> {
  const name = submittedName.trim();
  if (name.length < 1 || name.length > 100) {
    return { error: "이름은 1~100자여야 합니다." };
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { error: "로그인이 필요합니다." };

  // RLS(workspaces_select_member)가 요청자 소속 워크스페이스로만 좁혀 준다 —
  // 여기서도 owner_id 필터를 추가하면 초대받아 들어간 워크스페이스까지
  // 상한에 잡혀 과소 계산된다.
  const { data: existing } = await supabase.from("workspaces").select("id");
  if ((existing?.length ?? 0) >= MAX_PERSONAL_WORKSPACES) {
    return {
      error: `워크스페이스는 최대 ${MAX_PERSONAL_WORKSPACES}개까지 만들 수 있습니다.`,
    };
  }

  for (let attempt = 1; attempt <= 100; attempt += 1) {
    const { data, error } = await supabase
      .from("workspaces")
      .insert({
        name,
        slug: workspaceSlug(name, attempt),
        kind: "personal",
        owner_id: user.id,
      })
      .select("id")
      .single();

    if (!error && data) return { workspaceId: data.id };
    if (error?.code !== "23505")
      return { error: "워크스페이스를 만들 수 없습니다." };
  }

  return { error: "워크스페이스를 만들 수 없습니다." };
}
