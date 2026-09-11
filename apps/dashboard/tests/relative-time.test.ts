/**
 * 날짜 표기 2종의 경계 계약.
 *
 * ⚠️ 이 파일이 지키는 것 하나: `formatRelativeTime`은 30일이 넘으면 `formatDate`와
 * **같은 문자열**을 돌려준다. 두 표기를 나란히 놓는 화면은 `hasRelativeForm`으로
 * 먼저 물어야 하며, 묻지 않으면 같은 날짜가 두 번 찍힌다. 폴백이 조용해서 30일이
 * 지나기 전까지는 아무도 눈치채지 못한다.
 */

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  formatDate,
  formatRelativeTime,
  hasRelativeForm,
} from "@/lib/relative-time";

const NOW = new Date("2026-09-11T12:00:00Z");

function daysAgo(days: number): string {
  return new Date(NOW.getTime() - days * 86_400_000).toISOString();
}

afterEach(() => {
  vi.useRealTimers();
});

function freeze() {
  vi.useFakeTimers();
  vi.setSystemTime(NOW);
}

describe("formatRelativeTime", () => {
  it("30일 미만은 상대 표기를 돌려준다", () => {
    freeze();
    expect(formatRelativeTime(daysAgo(3))).toBe("3일 전");
    expect(formatRelativeTime(daysAgo(29))).toBe("29일 전");
  });

  it("30일부터는 절대 날짜로 접힌다", () => {
    freeze();
    const old = daysAgo(30);
    expect(formatRelativeTime(old)).toBe(formatDate(old));
  });
});

describe("hasRelativeForm", () => {
  it("상대 표기가 살아 있는 구간과 접힌 구간을 가른다", () => {
    freeze();
    expect(hasRelativeForm(daysAgo(29))).toBe(true);
    expect(hasRelativeForm(daysAgo(30))).toBe(false);
    expect(hasRelativeForm(daysAgo(365))).toBe(false);
  });

  it("경계가 formatRelativeTime의 폴백 시점과 정확히 같다", () => {
    freeze();
    // ⚠️ 두 함수가 서로 다른 임계값을 갖게 되면 화면은 다시 같은 날짜를 두 번
    //    찍거나, 반대로 절대 일자를 통째로 잃는다.
    for (const days of [0, 1, 29, 30, 31, 90]) {
      const iso = daysAgo(days);
      const foldedToAbsolute = formatRelativeTime(iso) === formatDate(iso);
      expect(hasRelativeForm(iso)).toBe(!foldedToAbsolute);
    }
  });
});
