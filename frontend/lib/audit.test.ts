import { describe, expect, it } from "vitest";
import { dayEndExclusive, dayStart, pageRange, personLabel, queryString, statusLabel } from "./audit";

describe("queryString", () => {
  it("keeps only filled-in values", () => expect(queryString({ kind: "CHAT", q: "", status: undefined, limit: 25, offset: 0 })).toBe("?kind=CHAT&limit=25&offset=0"));
  it("is empty when nothing is set", () => expect(queryString({ a: "", b: null })).toBe(""));
  it("encodes text safely", () => expect(queryString({ q: "a&b=c" })).toBe("?q=a%26b%3Dc"));
  it("trims spaces", () => expect(queryString({ q: "  leave " })).toBe("?q=leave"));
});

describe("dates", () => {
  it("starts a day at midnight UTC", () => expect(dayStart("2026-10-22")).toBe("2026-10-22T00:00:00Z"));
  it("ends a day at the start of the next one, month ends included", () => {
    expect(dayEndExclusive("2026-10-22")).toBe("2026-10-23T00:00:00.000Z");
    expect(dayEndExclusive("2026-10-31")).toBe("2026-11-01T00:00:00.000Z");
  });
  it("leaves an empty date out", () => {
    expect(dayStart("")).toBeUndefined();
    expect(dayEndExclusive("")).toBeUndefined();
  });
});

describe("labels", () => {
  it("turns statuses into words and keeps unknown ones", () => {
    expect(statusLabel("REFUSED_LOW_CONFIDENCE")).toBe("Refused: weak evidence");
    expect(statusLabel("NEW_THING")).toBe("NEW_THING");
  });
  it("never shows a blank person", () => {
    expect(personLabel({ id: "abcdef12-0000", full_name: "Asha", email: "a@x" })).toBe("Asha");
    expect(personLabel({ id: "abcdef12-0000", full_name: null, email: null })).toBe("Former user (abcdef12)");
    expect(personLabel(null)).toBe("–");
  });
  it("describes the page", () => {
    expect(pageRange(25, 25, 80)).toBe("26–50 of 80");
    expect(pageRange(0, 0, 0)).toBe("No records");
  });
});
