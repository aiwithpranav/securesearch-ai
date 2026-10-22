import { describe, expect, it } from "vitest";
import { barHeights, dayLabel, msText, percentText, reasonText, sum } from "./dashboards";

describe("percentText", () => {
  it("rounds to a whole percent", () => expect(percentText(0.256)).toBe("26%"));
  it("shows a dash when there is nothing to measure", () => {
    expect(percentText(null)).toBe("–");
    expect(percentText(undefined)).toBe("–");
  });
  it("keeps a real zero", () => expect(percentText(0)).toBe("0%"));
});

describe("msText", () => {
  it("uses milliseconds under a second and seconds above", () => {
    expect(msText(320)).toBe("320 ms");
    expect(msText(999)).toBe("999 ms");
    expect(msText(2040)).toBe("2.0 s");
  });
  it("shows a dash when missing", () => expect(msText(null)).toBe("–"));
});

describe("barHeights", () => {
  it("scales to the tallest bar", () => expect(barHeights([0, 5, 10], 100)).toEqual([0, 50, 100]));
  it("keeps an all-zero series flat", () => expect(barHeights([0, 0, 0], 100)).toEqual([0, 0, 0]));
  it("lets a second series share the scale", () => expect(barHeights([5], 100, 10)).toEqual([50]));
  it("handles an empty series", () => expect(barHeights([], 100)).toEqual([]));
});

describe("labels", () => {
  it("names the weekday without shifting across time zones", () => expect(dayLabel("2026-10-22")).toBe("Thu"));
  it("turns code words into plain words", () => {
    expect(reasonText("WEAK_EVIDENCE")).toBe("Passages were too weak");
    expect(reasonText("SOMETHING_NEW")).toBe("Something new");
  });
  it("adds up", () => expect(sum([1, 2, 3])).toBe(6));
});
