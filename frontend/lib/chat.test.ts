import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { ageText, answersUnavailable, chatErrorText, parseSse, splitAnswer, statusText, UNAVAILABLE_TEXT } from "./chat";

describe("parseSse", () => {
  it("reads complete events and keeps the unfinished rest", () => {
    const text = 'event: stage\ndata: {"id":"search"}\n\nevent: result\ndata: {"status":"ANSWERED"}\n\nevent: stage\ndata: {"id"';
    const { events, rest } = parseSse(text);
    expect(events).toEqual([{ event: "stage", data: { id: "search" } }, { event: "result", data: { status: "ANSWERED" } }]);
    expect(rest).toBe('event: stage\ndata: {"id"');
  });
  it("completes an event that arrives in two pieces", () => {
    const first = parseSse('event: stage\ndata: {"id":"a');
    expect(first.events).toEqual([]);
    const second = parseSse(first.rest + '"}\n\n');
    expect(second.events).toEqual([{ event: "stage", data: { id: "a" } }]);
  });
  it("ignores damaged messages and blocks without data", () => {
    const { events } = parseSse("event: stage\ndata: {not json}\n\n: comment only\n\nevent: result\ndata: {\"ok\":true}\n\n");
    expect(events).toEqual([{ event: "result", data: { ok: true } }]);
  });
  it("defaults the event name", () => {
    expect(parseSse('data: {"x":1}\n\n').events).toEqual([{ event: "message", data: { x: 1 } }]);
  });
});

describe("splitAnswer", () => {
  it("turns known [S#] markers into citation parts", () => {
    expect(splitAnswer("Leave is 24 days [S1]. Carry over 5 [S2].", ["S1", "S2"])).toEqual([
      { kind: "text", value: "Leave is 24 days " }, { kind: "cite", id: "S1" },
      { kind: "text", value: ". Carry over 5 " }, { kind: "cite", id: "S2" }, { kind: "text", value: "." },
    ]);
  });
  it("leaves markers that are not citations as plain text and handles answers without markers", () => {
    expect(splitAnswer("Use [S9] carefully", ["S1"])).toEqual([{ kind: "text", value: "Use [S9] carefully" }]);
    expect(splitAnswer("Plain answer.", ["S1"])).toEqual([{ kind: "text", value: "Plain answer." }]);
    expect(splitAnswer("", [])).toEqual([{ kind: "text", value: "" }]);
  });
});

describe("chatErrorText", () => {
  it("tells how long to wait", () => {
    expect(chatErrorText(new ApiError(429, "x", "x", undefined, 20))).toBe("Too many questions. Try again in 20 seconds.");
    expect(chatErrorText(new ApiError(429, "x", "x", undefined, 1))).toBe("Too many questions. Try again in 1 second.");
    expect(chatErrorText(new ApiError(429, "x", "x"))).toBe("Too many questions. Try again shortly.");
  });
  it("uses one friendly sentence when answers are unavailable and never shows raw details", () => {
    expect(chatErrorText(new ApiError(503, "x", "key missing details"))).toBe(UNAVAILABLE_TEXT);
    expect(chatErrorText(new ApiError(500, "x", "stack trace"))).not.toContain("stack trace");
    expect(chatErrorText(new ApiError(0, "x", "x"))).toContain("Can't reach the server");
    expect(chatErrorText(new Error("boom"))).toContain("could not be completed");
  });
  it("knows when plain search should be offered", () => {
    expect(answersUnavailable(new ApiError(503, "x", "x"))).toBe(true);
    expect(answersUnavailable(new ApiError(429, "x", "x"))).toBe(false);
    expect(answersUnavailable(new Error("x"))).toBe(false);
  });
});

describe("ageText and statusText", () => {
  const now = new Date("2026-10-22T12:00:00Z").getTime();
  it("describes how long ago in plain words", () => {
    expect(ageText("2026-10-22T11:59:40Z", now)).toBe("just now");
    expect(ageText("2026-10-22T11:55:00Z", now)).toBe("5 min ago");
    expect(ageText("2026-10-22T09:00:00Z", now)).toBe("3 h ago");
    expect(ageText("2026-10-21T10:00:00Z", now)).toBe("1 day ago");
    expect(ageText("2026-10-19T10:00:00Z", now)).toBe("3 days ago");
    expect(ageText("2026-09-01T10:00:00Z", now)).toMatch(/^1 Sep[a-z]* 2026$/);
    expect(ageText("2026-10-23T10:00:00Z", now)).toBe("just now"); // a clock a little ahead is not negative
  });
  it("words for the status", () => {
    expect(statusText("ANSWERED")).toBe("Answered");
    expect(statusText("REFUSED_LOW_CONFIDENCE")).toBe("No answer");
    expect(statusText("REFUSED_NO_ACCESS_EVIDENCE")).toBe("No answer");
  });
});
