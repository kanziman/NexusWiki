/**
 * 날짜 표시 포맷 2종. 소스 관리와 백로그가 같은 두 표기를 쓰므로 컴포넌트마다
 * 복제하지 않고 여기서 소유한다 — 복제해 두면 한쪽만 고쳐져 같은 화면의 두 표에
 * 다른 상대 시간 기준이 생긴다.
 */

/** 절대 날짜. "언제 올렸는가"처럼 특정 시점을 가리킬 때 쓴다. */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/** 상대 시간. 30일이 넘으면 상대 표기가 오히려 읽기 어려워 절대 날짜로 넘어간다. */
export function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "방금 전";
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}일 전`;
  return formatDate(iso);
}
