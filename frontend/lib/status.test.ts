import { afterEach, describe, expect, it, vi } from "vitest";
import { checkedText, componentHint, EXPLAIN, fetchStatus, HEADLINE, viewOf, type ServiceStatus } from "./status";

const ok: ServiceStatus = { status: "operational", components: [{ name: "Database", status: "up" }], checked_at: "2026-10-23T08:00:00Z" };

describe("viewOf", () => {
  it("shows the server's own word", () => {
    expect(viewOf(ok)).toBe("operational");
    expect(viewOf({ ...ok, status: "degraded" })).toBe("degraded");
    expect(viewOf({ ...ok, status: "down" })).toBe("down");
  });
  it("treats an unreachable server as its own state, never as operational", () => expect(viewOf(null)).toBe("unreachable"));
});

describe("texts", () => {
  it("has a headline and an explanation for every state", () => {
    for (const v of ["operational", "degraded", "down", "unreachable"] as const) {
      expect(HEADLINE[v].length).toBeGreaterThan(5);
      expect(EXPLAIN[v].length).toBeGreaterThan(10);
    }
  });
  it("says what each part does and stays silent about unknown ones", () => {
    expect(componentHint("Database")).toContain("documents");
    expect(componentHint("Something else")).toBe("");
  });
});

describe("checkedText", () => {
  const t = Date.parse("2026-10-23T08:00:00Z");
  it("speaks in seconds then minutes", () => {
    expect(checkedText("2026-10-23T08:00:00Z", t + 2000)).toBe("just now");
    expect(checkedText("2026-10-23T08:00:00Z", t + 30000)).toBe("30 s ago");
    expect(checkedText("2026-10-23T08:00:00Z", t + 180000)).toBe("3 min ago");
  });
  it("is empty without a time", () => expect(checkedText(undefined)).toBe(""));
});

describe("fetchStatus", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("returns the status when the server answers", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ok }));
    expect(await fetchStatus()).toEqual(ok);
  });
  it("returns null when the server answers with an error or the network fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, json: async () => ({}) }));
    expect(await fetchStatus()).toBeNull();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    expect(await fetchStatus()).toBeNull();
  });
  it("asks without any sign-in header and never from the cache", async () => {
    const f = vi.fn().mockResolvedValue({ ok: true, json: async () => ok });
    vi.stubGlobal("fetch", f);
    await fetchStatus();
    const [url, init] = f.mock.calls[0];
    expect(String(url)).toMatch(/\/status$/);
    expect(init).toEqual({ cache: "no-store", signal: undefined });
  });
});
