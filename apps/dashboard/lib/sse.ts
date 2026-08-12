/**
 * 범용 `event:`/`data:` SSE 프레임 파서.
 *
 * 관련 태스크: 06-04-PLAN.md 두 번째 항목
 * 설계 근거: `apps/api/src/api/routers/`의 `_format_sse` 헬퍼
 *   (`f"event: {name}\ndata: {json.dumps(payload)}\n\n"`가 이 파서가 소비하는 정확한 형태)
 *
 * 이 모듈은 특정 화면에 특화되지 않은 순수 인프라다 — 06-06 플랜의 대화형 컴포넌트가
 * 이번 페이즈의 유일한 소비자지만, 그 사실을 여기 들이지 않는다. `EventSource`를 쓰지
 * 않는 이유는 `Authorization` 헤더를 실을 수 없기 때문이다(05-CONTEXT.md D-02) —
 * `fetch` + `ReadableStream`으로 직접 프레임을 재조립한다.
 */
export type SseEvent = { event: string; data: unknown };

export async function* parseSseStream(
  response: Response,
): AsyncGenerator<SseEvent> {
  if (response.body === null) {
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    let done = false;
    while (!done) {
      const chunk = await reader.read();
      done = chunk.done;
      if (chunk.value) {
        buffer += decoder.decode(chunk.value, { stream: true });
      }

      // 하나의 `read()` 청크 안에 여러 프레임이 들어올 수 있으므로 완결된 프레임을
      // 전부 소비할 때까지 반복한다. 마지막에 남는 미완결 조각은 버퍼에 그대로 두고
      // 다음 `read()`에서 이어붙인다 — 청크 경계에서 프레임이 잘리는 경우를 여기서
      // 흡수한다.
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);

        const parsed = parseFrame(frame);
        if (parsed) {
          yield parsed;
        }

        boundary = buffer.indexOf("\n\n");
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * 프레임 하나(`event: <name>\ndata: <json>`)를 파싱한다.
 *
 * SSE 스펙 자체는 프레임 하나에 `data:` 줄이 여러 개일 수 있다고 허용하지만, 이
 * 프로젝트의 `_format_sse`는 항상 정확히 하나만 낸다 — 첫 `data:` 줄만 파싱하고 여러
 * 줄을 이어붙이는 일반화는 하지 않는다. 백엔드가 절대 만들지 않는 형태의 손상된
 * 프레임까지 조용히 받아들이게 되기 때문이다.
 */
function parseFrame(frame: string): SseEvent | null {
  let event: string | null = null;
  let dataLine: string | null = null;

  for (const line of frame.split("\n")) {
    if (event === null && line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (dataLine === null && line.startsWith("data:")) {
      dataLine = line.slice("data:".length).trim();
    }
  }

  if (event === null || dataLine === null) {
    return null;
  }

  return { event, data: JSON.parse(dataLine) as unknown };
}
