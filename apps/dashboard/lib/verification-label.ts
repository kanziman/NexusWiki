/**
 * 위키 문서의 검증 상태 → 화면 라벨. **이 매핑의 유일한 출처다.**
 *
 * 계약: openspec/specs/dashboard-design-consistency/spec.md
 * 「Shared state and control language」 — "A given underlying status value SHALL
 * be presented with the same label wherever it appears, so that one state is
 * never named differently on two destinations."
 *
 * ⚠️ 컴포넌트가 라벨 문자열을 직접 들고 있으면 안 된다. 실제로 그렇게 두었다가
 * 같은 `verified` 하나를 홈 대시보드는 "검증 완료", 위키 라이브러리는 "검증됨"
 * 으로 부르는 상태가 됐다. 이중 Citation 이 이 제품의 존재 이유인데 신뢰 상태를
 * 부르는 말이 화면마다 갈리면 그 신뢰 표시 자체가 흔들린다.
 *
 * 새 목적지에서 검증 상태를 보여줄 때는 문자열을 새로 쓰지 말고 이 함수를 쓴다.
 */

/** `wiki_pages.verification_status` 가 취할 수 있는 값(0001_core_schema.sql). */
export type VerificationStatus =
  "verified" | "partial" | "unverified" | "disputed";

export type VerificationLabelInput = {
  /**
   * 목적지마다 조회 폭이 달라 이 컬럼이 없을 수 있다(홈 대시보드의 요약 카드
   * 등). 없으면 미검증과 같이 취급한다.
   */
  verification_status?: string | null;
  /**
   * `wiki_pages.disputed`. 별도 boolean 컬럼이며 verification_status 와 독립이라
   * 함께 받는다. 이 값이 참이면 검증 단계보다 우선해서 표시한다 — 충돌은
   * "얼마나 검증됐는가"보다 먼저 해소해야 하는 상태다.
   *
   * ⚠️ `verification_status` 의 enum 값 `'disputed'` 와 **다른 것**이다
   * (PRODUCT-INVARIANTS.md §3). 둘을 혼동하지 않는다.
   */
  disputed?: boolean | null;
  /**
   * `wiki_pages.expires_at`. 검증에는 유효기간이 있다 —
   * `0007_search_and_queue_extensions.sql` 이 그 이유를 못박아 두었다:
   * "만료된 검증을 검증으로 세면 오래된 위키가 영원히 verified 로 남습니다."
   * 이 필드를 빠뜨리면 목록은 "검증됨"인데 리더만 "검증 만료됨"을 띄운다.
   */
  expires_at?: string | null;
};

/** 검증이 만료됐는지. `expires_at` 이 없으면 만료 개념이 없는 것으로 본다. */
function isExpired(page: VerificationLabelInput, now: number): boolean {
  if (!page.expires_at) return false;
  const at = new Date(page.expires_at).getTime();
  // 파싱 불가한 값이면 만료로 단정하지 않는다 — 조용히 신뢰를 깎느니
  // 기존 상태를 유지하고 다른 경로에서 드러나게 둔다.
  return Number.isFinite(at) && at < now;
}

/**
 * 검증 상태 라벨을 돌려준다.
 *
 * `disputed` 가 참이면 검증 단계와 무관하게 충돌을 먼저 알린다.
 * 알 수 없는 상태값은 미검증과 같이 취급한다 — 화면에 원시 enum 값이 새어
 * 나가는 것보다 낫다.
 */
export function verificationLabel(
  page: VerificationLabelInput,
  now: number = Date.now(),
): string {
  if (page.disputed) return "충돌 감지";
  if (page.verification_status === "verified") {
    return isExpired(page, now) ? "검증 만료됨" : "검증됨";
  }
  if (page.verification_status === "partial") return "부분 검증";
  return "검증 필요";
}

/**
 * 검증이 살아있는 상태인지. 배지를 띄울지 말지와 **검증 개수를 셀 때** 이 술어를
 * 쓴다 — 각 화면이 `=== "verified"` 비교를 따로 들고 있으면 충돌·만료를 빠뜨린다.
 *
 * ⚠️ 만료된 검증은 검증이 아니다. `verification_status === "verified"` 로 직접
 * 세지 않는다(`0007_search_and_queue_extensions.sql` §5).
 */
export function isVerified(
  page: VerificationLabelInput,
  now: number = Date.now(),
): boolean {
  return (
    !page.disputed &&
    page.verification_status === "verified" &&
    !isExpired(page, now)
  );
}

/**
 * 검증됐지만 유효기간이 지난 상태인지. 목록 화면이 "검증됨"도 아니고 무표시도
 * 아닌 제3의 상태로 그려야 할지 판정할 때 쓴다.
 */
export function isExpiredVerification(
  page: VerificationLabelInput,
  now: number = Date.now(),
): boolean {
  return (
    !page.disputed &&
    page.verification_status === "verified" &&
    isExpired(page, now)
  );
}
