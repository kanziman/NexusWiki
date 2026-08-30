/**
 * 내부 마이크로달러(micros) 비용을 사용자 친화적인 가상 크레딧 단위로 변환합니다.
 * 1 크레딧 = 10,000 micros ($0.01)
 *
 * 예시:
 * - 5,000,000 micros ($5.00) = 500 크레딧
 * - 1,000,000 micros ($1.00) = 100 크레딧
 * - 10,000 micros ($0.01) = 1 크레딧
 */
export const MICROS_PER_CREDIT = 10_000;

export function microsToCredits(micros: number): number {
  if (!micros || micros <= 0) return 0;
  return Math.round(micros / MICROS_PER_CREDIT);
}

export function formatCredits(micros: number): string {
  const credits = microsToCredits(micros);
  return `${credits.toLocaleString("ko-KR")} 크레딧`;
}
