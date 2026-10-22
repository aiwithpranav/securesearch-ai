import { describe, expect, it } from "vitest";
import { isRunning, modeText, verdict } from "./evaluation";

const run = (o: Partial<{ status: string; total: number; passed: number; leak_count: number }>) => ({ status: "DONE", total: 62, passed: 62, leak_count: 0, ...o });

describe("verdict", () => {
  it("passes only when every case passed", () => expect(verdict(run({}))).toBe("PASS"));
  it("fails when some case failed", () => expect(verdict(run({ passed: 60 }))).toBe("FAIL"));
  it("a leak wins over a pass count", () => expect(verdict(run({ leak_count: 1 }))).toBe("LEAK"));
  it("a run that is still going is running", () => expect(verdict(run({ status: "RUNNING", total: 0, passed: 0 }))).toBe("RUNNING"));
  it("a crashed run is an error, not a pass", () => expect(verdict(run({ status: "FAILED", total: 0, passed: 0 }))).toBe("ERROR"));
  it("an empty finished run is not a pass", () => expect(verdict(run({ total: 0, passed: 0 }))).toBe("FAIL"));
});

describe("helpers", () => {
  it("names the model mode", () => {
    expect(modeText("LIVE_MODEL")).toBe("Real model");
    expect(modeText("FAKE_MODEL")).toContain("free");
  });
  it("sees a running run", () => {
    expect(isRunning([{ status: "DONE" }, { status: "RUNNING" }])).toBe(true);
    expect(isRunning([])).toBe(false);
  });
});
