"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { UserMinus } from "lucide-react";
import { useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/client";

export type MembersListProps = {
  workspaceId: string;
  currentUserId: string;
};

type Member = {
  user_id: string;
  email: string;
  role: string;
  created_at: string;
};

const ROLE_LABELS: Record<string, string> = {
  owner: "소유자",
  editor: "편집자",
  viewer: "뷰어",
};

// 0014의 workspace_members_list RPC -> InviteForm.tsx의 성공 콜백이 여기 로컬
// state를 다시 채운다 (설정 페이지가 key로 리마운트하거나 이 컴포넌트가 직접
// refetch하는 두 방식 중, 초대 성공 시 목록 갱신은 InviteFormProps.onInvited가
// settings/page.tsx에서 key 증가로 처리한다 — 06-03-PLAN.md Task 3 <behavior>
// "component's choice" 참고).
export function MembersList({ workspaceId, currentUserId }: MembersListProps) {
  const [members, setMembers] = useState<Member[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [removeTarget, setRemoveTarget] = useState<Member | null>(null);
  const [removing, setRemoving] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const supabase = createClient();

    supabase
      .rpc("workspace_members_list", { p_workspace_id: workspaceId })
      .then(
        ({
          data,
          error,
        }: {
          data: Member[] | null;
          error: { message: string } | null;
        }) => {
          if (cancelled) return;
          if (error) {
            setLoadError("멤버 목록을 불러오지 못했습니다.");
            return;
          }
          setMembers(data ?? []);
        },
      );

    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  // T-06-12는 삭제 자체를 workspace_members_delete_owner RLS 정책(0004)이
  // 강제한다고 명시한다 — 이 판정은 그 강제를 흉내내는 것이 아니라, owner가
  // 아닌 화면에서 애초에 제거 버튼을 노출하지 않는 UX 계층이다.
  const isOwner =
    members?.find((member) => member.user_id === currentUserId)?.role ===
    "owner";

  function openRemoveDialog(member: Member) {
    setRemoveError(null);
    setRemoveTarget(member);
  }

  // [Rule 2] protect_owner_membership 트리거(0004)는 owner가 자기 멤버십을
  // 지우는 것을 DB 레벨에서 거부한다 — 이 화면에서 owner 자신의 행에는
  // 애초에 제거 버튼을 그리지 않아, 클릭했을 때만 실패하는 죽은 버튼을
  // 만들지 않는다.
  async function handleConfirmRemove() {
    if (!removeTarget) return;

    setRemoving(true);
    setRemoveError(null);

    const supabase = createClient();
    // 06-REVIEW.md WR-03: CLAUDE.md "Error Handling"이 명시한 대로, RLS
    // USING 실패로 막힌 UPDATE/DELETE는 예외 없이 0행 영향으로 반환된다
    // (`error: null`). `.select()`로 삭제된 행을 되받아 실제 행 수를
    // 확인해야만 "차단됨"과 "성공"을 구분할 수 있다 — error만 보면 둘 다
    // 동일하게 성공으로 오판된다.
    const { data, error } = await supabase
      .from("workspace_members")
      .delete()
      .match({ workspace_id: workspaceId, user_id: removeTarget.user_id })
      .select();

    setRemoving(false);

    if (error || !data || data.length === 0) {
      setRemoveError("멤버를 제거하지 못했습니다.");
      return;
    }

    const removedId = removeTarget.user_id;
    setMembers((prev) =>
      prev ? prev.filter((member) => member.user_id !== removedId) : prev,
    );
    setRemoveTarget(null);
  }

  // UI-SPEC UI Considerations (loading/sources-job-list 항목과 같은 계열의
  // backstop) + 06-03-PLAN.md must_haves.truths: 초기 조회 동안 스켈레톤을
  // 보여준다 — 불확정 스피너 대신 행 개수를 예측 가능하게 흉내낸다.
  if (members === null) {
    return (
      <ul
        aria-busy="true"
        data-testid="members-list-skeleton"
        className="flex flex-col gap-xs"
      >
        {[0, 1, 2].map((row) => (
          <li
            key={row}
            className="h-11 animate-pulse rounded-sm bg-surface-soft"
          />
        ))}
      </ul>
    );
  }

  if (loadError !== null) {
    return (
      <p
        role="alert"
        className="text-primary-error-text"
        style={{ font: "var(--font-caption)" }}
      >
        {loadError}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-xs">
      <ul className="flex flex-col">
        {members.map((member) => {
          const canRemove = isOwner && member.user_id !== currentUserId;

          return (
            <li
              key={member.user_id}
              className="flex items-center justify-between gap-base border-b border-hairline px-base py-base"
            >
              <div className="flex items-center gap-sm">
                <span
                  className="text-ink"
                  style={{ font: "var(--font-title-md)" }}
                >
                  {member.email}
                </span>
                <span
                  data-role={member.role}
                  className="rounded-full bg-surface-soft px-sm py-xs text-ink"
                  style={{ font: "var(--font-caption)" }}
                >
                  {ROLE_LABELS[member.role] ?? member.role}
                </span>
              </div>

              {canRemove ? (
                // Icon-only touch target: 44x44px + aria-label (UI-SPEC 예외 규칙).
                <button
                  type="button"
                  aria-label={`제거: ${member.email}`}
                  onClick={() => openRemoveDialog(member)}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-sm text-primary-error-text"
                >
                  <UserMinus size={20} aria-hidden="true" />
                </button>
              ) : null}
            </li>
          );
        })}
      </ul>

      <Dialog.Root
        open={removeTarget !== null}
        onOpenChange={(open) => {
          if (!open) setRemoveTarget(null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40" />
          <Dialog.Content className="fixed top-1/2 left-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-md bg-canvas p-lg shadow-[var(--shadow-modal)]">
            <Dialog.Title
              className="text-ink"
              style={{ font: "var(--font-title-md)" }}
            >
              멤버 제거
            </Dialog.Title>
            {/* UI-SPEC Copywriting Contract "Members (UI-02) | Removal confirmation" —
                문구는 한 글자도 바꾸지 않는다. */}
            <Dialog.Description
              className="text-body"
              style={{ font: "var(--font-body-md)" }}
            >
              {removeTarget
                ? `제거: ${removeTarget.email}님을 이 워크스페이스에서 제거하시겠습니까? 소유한 콘텐츠는 유지되지만 접근 권한이 즉시 사라집니다.`
                : ""}
            </Dialog.Description>

            {removeError !== null ? (
              <p
                role="alert"
                className="text-primary-error-text"
                style={{ font: "var(--font-caption)" }}
              >
                {removeError}
              </p>
            ) : null}

            <div className="flex justify-end gap-sm">
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="rounded-sm border border-border-strong px-base py-sm text-ink"
                >
                  취소
                </button>
              </Dialog.Close>
              <button
                type="button"
                onClick={handleConfirmRemove}
                disabled={removing}
                className="rounded-sm bg-primary-error-text px-base py-sm text-on-primary disabled:opacity-60"
              >
                제거
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
