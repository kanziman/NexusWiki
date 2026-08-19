import { createServerClient } from "@supabase/ssr";

import { requireEnv } from "@/lib/env";

/**
 * 공개 표면(`/p/**`) 전용 Supabase 클라이언트 팩토리 — **쿠키를 읽지 않는다.**
 *
 * ⚠️ 이 파일이 존재하는 이유가 곧 이 프로젝트에서 조용히 깨졌던 것이다.
 *
 * `0016_public_sharing.sql`은 사이드카 두 테이블에 permissive 정책을 각각 둘씩
 * 건다. `*_select_public`은 `allow_public_sharing = true`를 요구하지만
 * `*_select_member`는 `is_workspace_member()`만 본다 — 두 정책은 OR로 결합되므로
 * **`authenticated`로 실행하면 킬스위치가 꺼져 있어도 멤버에게는 행이 돌아온다.**
 *
 * 그리고 `/p/`에도 세션 쿠키는 same-origin 이라 그대로 실려 오며, `middleware.ts`의
 * matcher(`["/w/:path*", "/login"]`)가 걸러 주지도 않는다. ⚠️ matcher 에 `/p/`를
 * 추가하는 것은 해결이 아니다 — 미들웨어는 쿠키를 지우지 않는다. 세션을 버리는
 * 것은 클라이언트를 만드는 이 지점뿐이다. 요청자 세션 클라이언트를 쓰면 로그인한 멤버가
 * 공개 URL을 열었을 때 킬스위치를 내린 페이지가 그대로 렌더링된다 — 설정 화면이
 * 사용자에게 한 약속("모든 외부 공개 URL이 즉시 404로 차단됩니다")과 어긋난다.
 *
 * 그래서 세션을 **의도적으로 버린다.** 공개 URL은 누가 열든 게스트가 보는 것과
 * 똑같은 것을 보여줘야 하고, 그래야 `public-sharing-prd.md` §3.1의 전제
 * ("이 경로는 anon 이므로")와 "차단은 DB가 한다"는 주장이 비로소 참이 된다.
 *
 * 근거: PRODUCT-INVARIANTS.md §4 · §5.3, public-sharing-prd.md §3.1.
 */
export function createPublicClient() {
  return createServerClient(
    requireEnv("NEXT_PUBLIC_SUPABASE_URL"),
    requireEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"),
    {
      cookies: {
        // 빈 배열을 돌려주면 `@supabase/ssr`이 세션 없는 anon 클라이언트를 만든다.
        getAll() {
          return [];
        },
        // 공개 경로는 세션을 갱신하지 않는다 — 읽을 세션 자체가 없다.
        setAll() {},
      },
    },
  );
}
