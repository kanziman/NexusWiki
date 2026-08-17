"use server";

import { createClient } from "@/lib/supabase/server";

type CreateWorkspaceResult = { workspaceId: string } | { error: string };

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
