import { describe, expect, it } from "vitest";
import { codeText, countsText, githubSourceBody, intervalText, isRunning, runVerdict, sourceLink, validateGithubForm, type GithubForm, type SyncRun } from "./sync";

const form = (o: Partial<GithubForm> = {}): GithubForm => ({
  name: "demo docs", repo: "aiwithpranav/securesearch-ai", branch: "main", path: "demo-docs", departmentId: "1",
  documentType: "POLICY", sensitivity: "1", interval: "15", mirror: true, ...o,
});

describe("countsText", () => {
  it("lists only what happened, in a fixed order", () => {
    expect(countsText({ items: 6, unchanged: 2, new: 3, changed: 1 })).toBe("3 new, 1 changed, 2 unchanged");
  });
  it("says so when there was nothing to do", () => expect(countsText({ items: 0 })).toBe("Nothing to do"));
  it("names people changes and failures", () => {
    expect(countsText({ members_removed: 1, failed: 2 })).toBe("2 failed, 1 people removed from teams");
  });
});

describe("codeText", () => {
  it("explains the important codes in plain words", () => {
    expect(codeText("TOKEN_MISSING")).toContain("GITHUB_TOKEN");
    expect(codeText("EMPTY_LISTING")).toContain("safety stop");
  });
  it("tidies an unknown code and shows nothing for none", () => {
    expect(codeText("SOMETHING_NEW")).toBe("Something new");
    expect(codeText(null)).toBe("");
  });
});

describe("runVerdict", () => {
  const s = (status: SyncRun["status"]) => runVerdict({ status });
  it("maps every status", () => {
    expect([s("RUNNING"), s("DONE"), s("PARTIAL"), s("FAILED")]).toEqual(["RUNNING", "OK", "WARN", "FAIL"]);
  });
  it("sees a source that is running", () => {
    expect(isRunning([{ last_run: null }, { last_run: { status: "RUNNING" } as SyncRun }])).toBe(true);
    expect(isRunning([{ last_run: { status: "DONE" } as SyncRun }])).toBe(false);
  });
});

describe("intervalText", () => {
  it("speaks in minutes, hours and days", () => {
    expect([intervalText(5), intervalText(60), intervalText(360), intervalText(1440)]).toEqual(["every 5 minutes", "every hour", "every 6 hours", "every day"]);
  });
});

describe("validateGithubForm", () => {
  it("accepts a good form", () => expect(validateGithubForm(form())).toEqual({}));
  it.each([
    [{ repo: "just-a-name" }, "repo"], [{ repo: "https://github.com/a/b" }, "repo"], [{ repo: "a/b/c" }, "repo"],
    [{ branch: "a..b" }, "branch"], [{ branch: "has space" }, "branch"], [{ path: "/etc" }, "path"], [{ path: "../up" }, "path"],
    [{ name: "" }, "name"], [{ name: "bad:name" }, "name"], [{ departmentId: "" }, "departmentId"],
  ])("refuses %j", (over, field) => expect(Object.keys(validateGithubForm(form(over as Partial<GithubForm>)))).toContain(field));
});

describe("githubSourceBody", () => {
  it("builds the request without a token and with trimmed settings", () => {
    const b = githubSourceBody(form({ name: "  demo docs ", path: "/demo-docs/", branch: "", interval: "60", mirror: false }));
    expect(b).toEqual({
      name: "demo docs", kind: "github", interval_minutes: 60,
      config: { repo: "aiwithpranav/securesearch-ai", branch: "main", path: "demo-docs", mirror_collaborators: false, department_id: 1, document_type: "POLICY", sensitivity_level: 1 },
    });
    expect(JSON.stringify(b).toLowerCase()).not.toContain("token");
  });
});

describe("sourceLink", () => {
  it("links a plain owner/name repository", () => {
    expect(sourceLink({ kind: "GITHUB", config: { repo: "a/b", branch: "dev", path: "docs" } })).toBe("https://github.com/a/b/tree/dev/docs");
    expect(sourceLink({ kind: "GITHUB", config: { repo: "a/b" } })).toBe("https://github.com/a/b/tree/main");
  });
  it("never links anything else", () => {
    expect(sourceLink({ kind: "GITHUB", config: { repo: "https://evil.example/x" } })).toBeNull();
    expect(sourceLink({ kind: "FAKE", config: { repo: "a/b" } })).toBeNull();
    expect(sourceLink({ kind: "GITHUB", config: {} })).toBeNull();
  });
});
