import { createClient } from "@/lib/supabase/client";

/**
 * apps/api 호출 하나가 던지는 타입 오류.
 *
 * 관련 태스크: 06-04-PLAN.md Task 1
 * 설계 근거: apps/api/src/api/errors.py (본문 `detail` 토큰 어휘의 단일 출처)
 *
 * status/detail로만 분기하고 문장(prose)으로 분기하지 않는다 — `detail`은 라우터 쪽에서
 * 이미 "기계 판독 가능한 짧은 토큰"으로 설계되어 있고(`errors.py` InvalidSourceInput
 * 주석), 이 클래스는 그 계약을 그대로 옮겨 담을 뿐 새 토큰을 만들지 않는다.
 */
export class ApiError extends Error {
  status: number;
  detail: string;
  extra?: Record<string, unknown>;

  constructor(status: number, detail: string, extra?: Record<string, unknown>) {
    super(`apiFetch failed: ${status} ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.extra = extra;
  }
}

export type ApiFetchInit = {
  method?: string;
  body?: unknown;
  /**
   * `body`가 `Uint8Array`/`Blob`일 때만 쓰인다 — sources.py의 파일 업로드 엔드포인트가
   * multipart가 아니라 원시 바이트 본문을 받기 때문에(D-P11), 그 경로에서는 호출자가
   * 파일의 실제 MIME 타입을 직접 지정해야 한다.
   */
  contentType?: string;
};

/**
 * 요청자 자신의 Supabase 액세스 토큰을 매 호출마다 새로 실어 apps/api를 호출한다.
 *
 * ⚠️ 토큰은 모듈 레벨에 캐시하지 않고 매 호출마다 `createClient().auth.getSession()`으로
 * 새로 읽는다 — `apps/api/src/api/routers/sources.py`의 `_user_db` 팩토리가 매 요청마다
 * `credentials.credentials`(요청자 JWT)를 새로 받는 것과 같은 이유다. 세션이 없으면
 * 네트워크 호출을 시작하기 전에 던진다 — Authorization 헤더가 비거나 없는 요청을
 * 절대 내보내지 않는다.
 */
export async function apiFetch<T>(
  path: string,
  init?: ApiFetchInit,
): Promise<T> {
  const {
    data: { session },
  } = await createClient().auth.getSession();

  if (!session) {
    throw new Error("apiFetch called without an active session");
  }

  const headers: Record<string, string> = {
    Authorization: `Bearer ${session.access_token}`,
  };

  let body: BodyInit | undefined;
  if (init?.body !== undefined) {
    if (init.body instanceof Uint8Array || init.body instanceof Blob) {
      // TS 5.9의 lib.dom.d.ts에서 Uint8Array가 제네릭(Uint8Array<ArrayBufferLike>)이
      // 되면서 BodyInit 유니언에 구조적으로 안 맞는다고 오판한다 — 런타임의 fetch는
      // ArrayBufferView를 그대로 받아들이므로(Blob 분기와 동일하게 동작 변경 없음)
      // 타입 단언만으로 좁힌다.
      body = init.body as BodyInit;
      if (init.contentType) {
        headers["Content-Type"] = init.contentType;
      }
    } else {
      body = JSON.stringify(init.body);
      headers["Content-Type"] = "application/json";
    }
  }

  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${path}`, {
    method: init?.method ?? "GET",
    headers,
    body,
  });

  if (!response.ok) {
    const errorBody = await parseJsonBody(response);
    const { detail, ...extraFields } = errorBody;
    const extra = Object.keys(extraFields).length > 0 ? extraFields : undefined;
    throw new ApiError(
      response.status,
      typeof detail === "string" ? detail : "unknown_error",
      extra,
    );
  }

  // 202/204처럼 본문이 없는 성공 응답도 있다(취소 엔드포인트 등) — 빈 본문은
  // 그대로 undefined로 돌려준다. 있으면 파싱해서 감싸지 않고 그대로 반환한다.
  const text = await response.text();
  return text.length > 0 ? (JSON.parse(text) as T) : (undefined as T);
}

/**
 * 응답 본문을 방어적으로 JSON 파싱한다.
 *
 * ⚠️ 본문이 JSON이 아니거나 파싱에 실패해도 예외를 밖으로 던지지 않고 고정된
 * `unknown_error` 토큰으로 대체한다 — 파싱되지 않은 원본 응답 본문을 그대로 밖으로
 * 흘리면 콘솔/에러 바운더리로 새어나갈 수 있다(threat T-06-13).
 */
async function parseJsonBody(
  response: Response,
): Promise<Record<string, unknown>> {
  try {
    const text = await response.text();
    if (text.length === 0) {
      return { detail: "unknown_error" };
    }
    const parsed: unknown = JSON.parse(text);
    if (
      parsed !== null &&
      typeof parsed === "object" &&
      !Array.isArray(parsed)
    ) {
      return parsed as Record<string, unknown>;
    }
    return { detail: "unknown_error" };
  } catch {
    return { detail: "unknown_error" };
  }
}
