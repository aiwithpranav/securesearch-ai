import { describe, expect, it } from "vitest";
import { canSeeAudit, canSeeGaps, manageLinks } from "./roles";

const labels = (roles: string[]) => manageLinks(roles).map((l) => l.label);

describe("manageLinks", () => {
  it("shows nothing to an ordinary employee", () => {
    expect(manageLinks(["employee"])).toEqual([]);
  });
  it("gives the system administrator the management screens but not the audit trail", () => {
    expect(labels(["employee", "system_admin"])).toEqual(["Overview", "Documents", "Users", "Groups", "Knowledge gaps", "Evaluation"]);
    expect(canSeeAudit(["system_admin"])).toBe(false);
  });
  it("gives the security administrator the audit trail and the gaps, not user management", () => {
    expect(labels(["employee", "security_admin"])).toEqual(["Knowledge gaps", "Audit"]);
  });
  it("gives the auditor only the audit trail", () => {
    expect(labels(["employee", "auditor"])).toEqual(["Audit"]);
    expect(canSeeGaps(["auditor"])).toBe(false);
  });
  it("combines roles without repeating a link", () => {
    const l = labels(["system_admin", "security_admin", "auditor"]);
    expect(new Set(l).size).toBe(l.length);
    expect(l).toContain("Audit");
    expect(l).toContain("Overview");
  });
});
