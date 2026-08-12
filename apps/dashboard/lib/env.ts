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
 *
 * ⚠️ 반드시 리터럴 `process.env.NEXT_PUBLIC_X` 형태로 각 키를 나열해야 한다.
 * `process.env[name]`처럼 동적 인덱싱을 쓰면 웹팩의 DefinePlugin이 클라이언트
 * 번들 시점에 정적으로 치환하지 못해 브라우저에서 항상 undefined가 된다 —
 * 실측: UAT 06 세션에서 로그인 자체가 깨지는 것으로 발견 (WR-05 후속 회귀).
 * 모듈 스코프 객체 리터럴로 한 번만 읽으면 안 된다 — 테스트가 호출 사이사이
 * `process.env.X`를 직접 바꿔가며 기대하는 "매 호출 시점에 읽는다" 계약이
 * 깨진다(실측: vitest 14건 실패). `switch` 안에서 읽어야 리터럴 정적 분석과
 * 호출 시점 평가를 동시에 만족한다. 새 `NEXT_PUBLIC_*` 키를 쓰려면 이 switch에
 * 케이스를 추가할 것.
 */
type EnvKey =
  | "NEXT_PUBLIC_SUPABASE_URL"
  | "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"
  | "NEXT_PUBLIC_API_URL";

function readEnv(name: EnvKey): string | undefined {
  switch (name) {
    case "NEXT_PUBLIC_SUPABASE_URL":
      return process.env.NEXT_PUBLIC_SUPABASE_URL;
    case "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY":
      return process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
    case "NEXT_PUBLIC_API_URL":
      return process.env.NEXT_PUBLIC_API_URL;
  }
}

export function requireEnv(name: EnvKey): string {
  const value = readEnv(name);
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}
