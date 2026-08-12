import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());

// jsdom은 Pointer Capture API/scrollIntoView/ResizeObserver를 구현하지 않는다
// (jsdom 30 실측 확인). Radix UI 프리미티브(DropdownMenu/Tooltip/Select 등,
// 06-UI-SPEC.md Design System 표)는 내부적으로 이들을 호출하므로, 폴리필이
// 없으면 "not a function" 에러로 Radix 기반 컴포넌트 전체의 테스트가 깨진다.
// 06-02가 처음 Radix 컴포넌트를 테스트하지만 06-03 이후 모든 Phase 6 플랜이
// 같은 문제를 겪으므로 전역 setup에 한 번만 추가한다.
if (typeof Element.prototype.hasPointerCapture !== "function") {
  Element.prototype.hasPointerCapture = () => false;
}
if (typeof Element.prototype.setPointerCapture !== "function") {
  Element.prototype.setPointerCapture = () => {};
}
if (typeof Element.prototype.releasePointerCapture !== "function") {
  Element.prototype.releasePointerCapture = () => {};
}
if (typeof Element.prototype.scrollIntoView !== "function") {
  Element.prototype.scrollIntoView = () => {};
}
if (typeof window.ResizeObserver === "undefined") {
  window.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
