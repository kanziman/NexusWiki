import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AskLayout, buildGridTemplateColumns } from "@/components/AskLayout";

// AskLayout은 컨테이너와 인스펙터 자식의 실제 렌더 폭(getBoundingClientRect)을
// 읽어 클램프 범위를 계산한다 — jsdom은 레이아웃을 계산하지 않으므로
// 이 값들을 클래스/testid로 구분해 직접 채워 넣는다. containerWidth는
// let으로 둬 컨테이너 ResizeObserver 테스트에서 값을 바꿔치기한다.
let containerWidth = 1000;
const INITIAL_INSPECT_WIDTH = 400; // 최대치(574 = 1000-420-6)보다 여유 있게 작다
const MAX_INSPECT_WIDTH = () => containerWidth - 420 - 6;

function rect(overrides: Partial<DOMRect>): DOMRect {
  return {
    width: 0,
    height: 0,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    x: 0,
    y: 0,
    toJSON() {
      return this;
    },
    ...overrides,
  } as DOMRect;
}

// vitest.setup.ts의 전역 ResizeObserver 폴리필은 콜백을 전혀 호출하지 않는
// no-op이라(Radix 컴포넌트가 존재만 확인하면 되는 다른 테스트에는 충분하다),
// 여기서는 observe() 즉시 콜백을 한 번 실행하고, 등록된 target을 기억해
// triggerResize()로 나중에 다시 실행할 수 있게 한다 — AskLayout이 컨테이너
// 자체에도 ResizeObserver를 걸어(LNB 접기/펼치기 같은 window resize 없는
// 폭 변화를 잡으려고) 그 재계산 경로를 테스트하려면 필요하다.
type Registration = { target: Element; callback: ResizeObserverCallback };
let registrations: Registration[] = [];

class TrackingResizeObserver {
  #callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.#callback = callback;
  }

  observe(target: Element) {
    registrations.push({ target, callback: this.#callback });
    this.#callback(
      [{ contentRect: target.getBoundingClientRect() } as ResizeObserverEntry],
      this as unknown as ResizeObserver,
    );
  }

  unobserve() {}
  disconnect() {}
}

function triggerResize(target: Element) {
  // 실제 ResizeObserver 콜백은 React 이벤트 밖에서 비동기로 발화하므로,
  // fireEvent처럼 act()로 감싸지 않으면 setInspectWidth가 커밋되기 전에
  // 단언문이 먼저 실행돼 버린다.
  act(() => {
    for (const registration of registrations) {
      if (registration.target === target) {
        registration.callback(
          [
            {
              contentRect: target.getBoundingClientRect(),
            } as ResizeObserverEntry,
          ],
          {} as ResizeObserver,
        );
      }
    }
  });
}

beforeEach(() => {
  containerWidth = 1000;
  registrations = [];
  window.ResizeObserver =
    TrackingResizeObserver as unknown as typeof ResizeObserver;

  vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(
    function (this: HTMLElement) {
      if (this.classList.contains("ask-layout")) {
        return rect({ width: containerWidth, right: containerWidth });
      }
      if (this.dataset.testid === "stub-inspector") {
        return rect({
          width: INITIAL_INSPECT_WIDTH,
          right: containerWidth,
          left: containerWidth - INITIAL_INSPECT_WIDTH,
        });
      }
      return rect({});
    },
  );
});

function renderLayout() {
  return render(
    <AskLayout
      conversation={<div data-testid="stub-conversation">conv</div>}
      inspector={<div data-testid="stub-inspector">insp</div>}
    />,
  );
}

describe("AskLayout", () => {
  it("role=separator + aria-orientation=vertical로 렌더되고, 마운트 시 측정된 폭을 aria-valuenow로 노출한다", () => {
    renderLayout();

    const splitter = screen.getByTestId("ask-splitter");
    expect(splitter).toHaveAttribute("role", "separator");
    expect(splitter).toHaveAttribute("aria-orientation", "vertical");
    expect(splitter).toHaveAttribute(
      "aria-valuenow",
      String(INITIAL_INSPECT_WIDTH),
    );
    expect(splitter).toHaveAttribute("aria-valuemin", "360");
  });

  it("포인터 드래그로 폭을 조절하면 aria-valuenow가 즉시 갱신된다", () => {
    renderLayout();
    const splitter = screen.getByTestId("ask-splitter");

    fireEvent.pointerDown(splitter, { pointerId: 1, clientX: 500 });
    // 컨테이너 오른쪽 끝(1000) - clientX(500) = 인스펙터 폭 500
    fireEvent.pointerMove(splitter, { pointerId: 1, clientX: 500 });
    fireEvent.pointerUp(splitter, { pointerId: 1 });

    expect(splitter).toHaveAttribute("aria-valuenow", "500");
  });

  it("포인터 드래그가 최소 인스펙터 폭(360) 아래로는 내려가지 않는다", () => {
    renderLayout();
    const splitter = screen.getByTestId("ask-splitter");

    fireEvent.pointerDown(splitter, { pointerId: 1, clientX: 950 });
    fireEvent.pointerMove(splitter, { pointerId: 1, clientX: 950 });

    expect(splitter).toHaveAttribute("aria-valuenow", "360");
  });

  it("ArrowLeft는 인스펙터 폭을 24px 늘리고, ArrowRight는 24px 줄인다", () => {
    renderLayout();
    const splitter = screen.getByTestId("ask-splitter");

    fireEvent.keyDown(splitter, { key: "ArrowLeft" });
    expect(splitter).toHaveAttribute(
      "aria-valuenow",
      String(INITIAL_INSPECT_WIDTH + 24),
    );

    fireEvent.keyDown(splitter, { key: "ArrowRight" });
    fireEvent.keyDown(splitter, { key: "ArrowRight" });
    expect(splitter).toHaveAttribute(
      "aria-valuenow",
      String(INITIAL_INSPECT_WIDTH - 24),
    );
  });

  it("Home은 최소 폭으로, End는 최대 폭으로 이동한다", () => {
    renderLayout();
    const splitter = screen.getByTestId("ask-splitter");

    fireEvent.keyDown(splitter, { key: "Home" });
    expect(splitter).toHaveAttribute("aria-valuenow", "360");

    fireEvent.keyDown(splitter, { key: "End" });
    expect(splitter).toHaveAttribute(
      "aria-valuenow",
      String(MAX_INSPECT_WIDTH()),
    );
  });

  it("buildGridTemplateColumns는 대화 최소·스플리터·지정폭을 그대로 트랙 값으로 짠다", () => {
    expect(buildGridTemplateColumns(500)).toBe("minmax(420px, 1fr) 6px 500px");
    expect(buildGridTemplateColumns(null)).toBeUndefined();
  });

  it("컨테이너가 대화·스플리터·인스펙터 최소 합(786px) 아래로 좁아지면 지정해둔 폭을 CSS 기본값에 되돌린다", () => {
    renderLayout();
    const splitter = screen.getByTestId("ask-splitter");
    const container = splitter.parentElement as HTMLElement;

    fireEvent.pointerDown(splitter, { pointerId: 1, clientX: 500 });
    fireEvent.pointerMove(splitter, { pointerId: 1, clientX: 500 });
    expect(splitter).toHaveAttribute("aria-valuenow", "500");

    // LNB를 펼쳐 컨테이너가 window resize 없이 좁아지는 상황을 흉내낸다.
    // 420(대화 최소) + 6(스플리터) + 360(인스펙터 최소) = 786 > 700이므로
    // 이 폭에서는 두 최소를 동시에 만족할 수 없다.
    containerWidth = 700;
    triggerResize(container);

    expect(splitter).toHaveAttribute(
      "aria-valuenow",
      String(INITIAL_INSPECT_WIDTH),
    );
  });

  it("컨테이너가 좁아져도 최소 합(786px)은 넘으면 지정해둔 폭을 새 여유 폭 안으로 재클램프한다", () => {
    renderLayout();
    const splitter = screen.getByTestId("ask-splitter");
    const container = splitter.parentElement as HTMLElement;

    fireEvent.pointerDown(splitter, { pointerId: 1, clientX: 500 });
    fireEvent.pointerMove(splitter, { pointerId: 1, clientX: 500 });
    expect(splitter).toHaveAttribute("aria-valuenow", "500");

    containerWidth = 900; // 새 최대치 = 900 - 420 - 6 = 474 < 500
    triggerResize(container);

    expect(splitter).toHaveAttribute("aria-valuenow", "474");
  });

  it("pointercancel이 발생하면 dragging이 즉시 풀려 이후 pointermove가 폭을 바꾸지 않는다", () => {
    renderLayout();
    const splitter = screen.getByTestId("ask-splitter");

    fireEvent.pointerDown(splitter, { pointerId: 1, clientX: 500 });
    fireEvent.pointerCancel(splitter, { pointerId: 1 });
    fireEvent.pointerMove(splitter, { pointerId: 1, clientX: 100 });

    expect(splitter).not.toHaveAttribute("data-dragging");
    expect(splitter).toHaveAttribute(
      "aria-valuenow",
      String(INITIAL_INSPECT_WIDTH),
    );
  });
});
