import { describe, expect, it } from "vitest";
import { describeRule, diffRules, employmentLabel, expiryText, localInputToIso, pageRange, reasonText, usersQueryString, USER_PAGE_SIZE, type SnapshotRule } from "./access";

const rule = (id: string, effect: "ALLOW" | "DENY" = "ALLOW", permission: "READ" | "DOWNLOAD" | "MANAGE" = "READ", expires: string | null = null): SnapshotRule => ({
  id, principal_type: "GROUP", principal_name: "HR Team", principal_id: "1", effect, permission, expires_at: expires,
});

describe("reasonText", () => {
  it("explains every code the server can return in plain English", () => {
    for (const code of ["ALLOWED", "NO_ALLOW_RULE", "DENIED_BY_RULE", "CLEARANCE_TOO_LOW", "COUNTRY_NOT_ALLOWED", "DOCUMENT_UNAVAILABLE", "USER_INACTIVE"]) {
      expect(reasonText(code).length).toBeGreaterThan(10);
      expect(reasonText(code)).not.toContain("_");
    }
    expect(reasonText("ALLOWED").startsWith("Yes")).toBe(true);
    expect(reasonText("DENIED_BY_RULE")).toContain("always wins");
  });
  it("never shows a raw unknown code", () => {
    expect(reasonText("SOMETHING_NEW")).toBe("No.");
  });
});

describe("describeRule", () => {
  it("writes one readable sentence", () => {
    expect(describeRule({ effect: "DENY", principal_name: "Shivam Suryawanshi", permission: "READ" })).toBe("Deny Shivam Suryawanshi: can read");
    expect(describeRule({ effect: "ALLOW", principal_name: "Everyone", permission: "MANAGE" })).toBe("Allow Everyone: can manage rules and details");
  });
});

describe("expiryText", () => {
  it("handles no expiry, a future expiry and an expired rule", () => {
    expect(expiryText({ expires_at: null, expired: false })).toBe("Never expires");
    expect(expiryText({ expires_at: "2099-01-01T00:00:00Z", expired: false }).startsWith("Until ")).toBe(true);
    expect(expiryText({ expires_at: "2000-01-01T00:00:00Z", expired: true }).startsWith("Expired ")).toBe(true);
  });
});

describe("localInputToIso", () => {
  it("returns null when empty and an ISO string otherwise", () => {
    expect(localInputToIso("")).toBeNull();
    expect(localInputToIso("not a date")).toBeNull();
    expect(localInputToIso("2099-05-01T10:30")).toMatch(/^2099-05-01T\d\d:\d\d:00\.000Z$/);
  });
});

describe("diffRules", () => {
  it("finds added, removed and changed rules", () => {
    const prev = [rule("a"), rule("b"), rule("c")];
    const next = [rule("a"), rule("c", "DENY"), rule("d")];
    const d = diffRules(prev, next);
    expect(d.added.map((r) => r.id)).toEqual(["d"]);
    expect(d.removed.map((r) => r.id)).toEqual(["b"]);
    expect(d.changed.map((r) => r.id)).toEqual(["c"]);
  });
  it("notices an expiry change and ignores identical lists", () => {
    expect(diffRules([rule("a")], [rule("a", "ALLOW", "READ", "2099-01-01T00:00:00Z")]).changed).toHaveLength(1);
    expect(diffRules([rule("a")], [rule("a")])).toEqual({ added: [], removed: [], changed: [] });
  });
});

describe("employmentLabel", () => {
  it("makes the stored word readable", () => {
    expect(employmentLabel("full_time")).toBe("Full time");
  });
});

describe("usersQueryString", () => {
  it("asks for one page with the default size and no filters", () => {
    expect(usersQueryString()).toBe(`?limit=${USER_PAGE_SIZE}&offset=0`);
  });
  it("adds only the filters that are set and trims the search", () => {
    const qs = new URLSearchParams(usersQueryString({ limit: 50, offset: 100, q: "  meera ", departmentId: "3", status: "inactive", role: "auditor" }));
    expect(Object.fromEntries(qs)).toEqual({ limit: "50", offset: "100", q: "meera", department_id: "3", is_active: "false", role: "auditor" });
  });
  it("maps the status choices to true and false and leaves 'all' out", () => {
    expect(new URLSearchParams(usersQueryString({ status: "active" })).get("is_active")).toBe("true");
    expect(new URLSearchParams(usersQueryString({ status: "" })).has("is_active")).toBe(false);
  });
  it("leaves out a blank search and a blank role, and cuts a very long search at 100 characters", () => {
    expect(usersQueryString({ q: "   ", role: "" })).toBe(`?limit=${USER_PAGE_SIZE}&offset=0`);
    expect(new URLSearchParams(usersQueryString({ q: "x".repeat(300) })).get("q")).toHaveLength(100);
  });
  it("encodes special characters, so they cannot change the query", () => {
    const qs = new URLSearchParams(usersQueryString({ q: "a&is_active=false#%" }));
    expect(qs.get("q")).toBe("a&is_active=false#%");
    expect(qs.has("is_active")).toBe(false);
  });
});

describe("pageRange", () => {
  it("shows 'from to of total' and the buttons that make sense", () => {
    expect(pageRange(0, 50, 1009)).toEqual({ from: 1, to: 50, hasPrevious: false, hasNext: true });
    expect(pageRange(1000, 50, 1009)).toEqual({ from: 1001, to: 1009, hasPrevious: true, hasNext: false });
  });
  it("handles an empty result and a single page", () => {
    expect(pageRange(0, 50, 0)).toEqual({ from: 0, to: 0, hasPrevious: false, hasNext: false });
    expect(pageRange(0, 50, 50)).toEqual({ from: 1, to: 50, hasPrevious: false, hasNext: false });
  });
});
