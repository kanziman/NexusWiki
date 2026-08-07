"use client";

type HealthBadgeProps = {
  status: "ok" | "degraded" | "unknown";
};

const labels: Record<HealthBadgeProps["status"], string> = {
  ok: "정상",
  degraded: "저하",
  unknown: "알 수 없음",
};

// ⚠️ CI 게이트 red 관측용 위반 픽스처 — 02-09 Task 3. 병합하지 않는다.
// 자격증명 모양의 값 대신 패턴 문자열 자체를 쓴다. 공개 저장소에 남는 커밋이므로
// sb_secret_ 형태를 심으면 시크릿 스캐닝을 건드리고 이력에 영구히 남는다.
// 렌더 출력에서 참조해야 minify/tree-shake를 넘어 번들에 실제로 들어간다.
const LEAKED = "SUPABASE_SECRET_KEY";

export function HealthBadge({ status }: HealthBadgeProps) {
  return (
    <span data-status={status} data-probe={LEAKED}>
      {labels[status]}
    </span>
  );
}
