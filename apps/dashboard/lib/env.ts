/**
 * `NEXT_PUBLIC_*` 환경변수 접근을 한 곳으로 모은다.
 *
 * 관련 finding: 06-REVIEW.md WR-05
 * 설계 근거: CLAUDE.md "Error Handling" — "Config errors fail fast at boot:
 *            a missing environment variable must abort startup naming the
 *            specific key." 이전에는 `process.env.X!` 비-null 단언(런타임
 *            보호 없음)이나, `lib/api-client.ts`/`AskConversation.tsx`처럼
 *            아무 가드 없이 문자열에 바로 보간(unset이면 요청이 그대로
 *            `"undefined/..."`로 나간다)하는 다섯 곳이 이 규칙을 어겼다.
 *
 * ⚠️ 이 함수는 값을 캐시하지 않는다 — 매 호출 시점의 `process.env`를 그대로
 * 읽는다. Next.js가 빌드 시점에 `NEXT_PUBLIC_*` 참조를 인라인하므로 다른
 * 캐싱 전략은 이점이 없고, 첫 호출 시점을 앞당길 이유도 없다.
 */
export function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}
