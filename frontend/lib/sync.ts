// Sync sources and runs (Phase 8C). Settings hold no secrets: the GitHub token lives in the server's .env, never on a screen.
import { authedApi } from "./session";

export type SyncCounts = Record<string, number>;
export type SyncRun = {
  id: string;
  source_id: string;
  status: "RUNNING" | "DONE" | "PARTIAL" | "FAILED";
  trigger: "SCHEDULE" | "MANUAL";
  started_at: string;
  finished_at: string | null;
  counts: SyncCounts;
  errors: { item: string; code: string }[];
  error_code: string | null;
};
export type SyncSource = {
  id: string;
  name: string;
  kind: string;
  config: Record<string, unknown>;
  enabled: boolean;
  interval_minutes: number;
  last_run_at: string | null;
  created_at: string;
  last_run: SyncRun | null;
};
export type GithubForm = {
  name: string;
  repo: string;
  branch: string;
  path: string;
  departmentId: string;
  documentType: string;
  sensitivity: string;
  interval: string;
  mirror: boolean;
};

export const INTERVALS = [5, 15, 30, 60, 360, 1440] as const;

export const listSources = () => authedApi<SyncSource[]>("/sync/sources");
export const createSource = (body: unknown) => authedApi<SyncSource>("/sync/sources", { method: "POST", body });
export const updateSource = (id: string, body: { enabled?: boolean; interval_minutes?: number }) =>
  authedApi<SyncSource>(`/sync/sources/${id}`, { method: "PATCH", body });
export const runSource = (id: string) => authedApi<SyncRun>(`/sync/sources/${id}/run`, { method: "POST" });
export const listRuns = (id: string) => authedApi<SyncRun[]>(`/sync/sources/${id}/runs?limit=10`);

/** Plain words for the fixed code words of a failed run or item. An unknown code is shown tidied, never hidden. */
const CODES: Record<string, string> = {
  TOKEN_MISSING: "The server has no GitHub token. Add GITHUB_TOKEN to the .env file and restart the worker.",
  BAD_CREDENTIALS: "GitHub did not accept the token. It may have expired or been deleted.",
  NOT_FOUND: "The repository, branch or folder was not found, or the token cannot see it.",
  PERMISSIONS_UNAVAILABLE: "GitHub would not list the repository's collaborators. Give the token that permission, or turn off the collaborator check.",
  RATE_LIMITED: "GitHub's request limit was reached. The next run will try again.",
  TREE_TOO_LARGE: "The repository has too many files to list in one go. Choose a smaller folder.",
  BAD_ACCESS_FILE: "The access file in .securesearch is damaged or has the wrong shape.",
  SOURCE_UNREACHABLE: "The source could not be reached.",
  EMPTY_LISTING: "The source listed nothing, so nothing was changed (a safety stop).",
  TOO_MANY_DELETES: "The run would have removed most of the documents, so nothing was changed (a safety stop).",
  BAD_LISTING: "The source listed the same item twice, so nothing was changed.",
  UNKNOWN_KIND: "This kind of source is not available.",
  QUEUE_UNAVAILABLE: "The background worker was not available.",
  STALE: "The run was stuck and was closed.",
  INTERRUPTED: "The worker stopped while the run was going.",
  TIMEOUT: "The run took too long and was stopped.",
  DUPLICATE_CONTENT: "Another document already has identical content.",
  UNSUPPORTED_TYPE: "The file type is not supported.",
  EMPTY: "The file is empty.",
  NO_TEXT: "No readable text was found.",
  TOO_LARGE: "The file is too large.",
  INTERNAL: "An unexpected error occurred.",
};
export const codeText = (code: string | null | undefined): string =>
  !code ? "" : CODES[code] ?? code.toLowerCase().replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

export type RunVerdict = "RUNNING" | "OK" | "WARN" | "FAIL";
export const runVerdict = (run: Pick<SyncRun, "status">): RunVerdict =>
  run.status === "RUNNING" ? "RUNNING" : run.status === "DONE" ? "OK" : run.status === "PARTIAL" ? "WARN" : "FAIL";
export const verdictLabel: Record<RunVerdict, string> = { RUNNING: "Running…", OK: "Synced", WARN: "Synced with problems", FAIL: "Failed" };

const COUNT_WORDS: [string, string][] = [
  ["new", "new"], ["changed", "changed"], ["permission_only", "access updated"], ["restored", "restored"], ["deleted", "removed"],
  ["unchanged", "unchanged"], ["failed", "failed"], ["members_added", "people added to teams"], ["members_removed", "people removed from teams"],
];
/** "3 new, 1 changed, 2 unchanged". Zero counts are left out; a run with nothing to say says so. */
export function countsText(counts: SyncCounts): string {
  const parts = COUNT_WORDS.filter(([k]) => (counts[k] ?? 0) > 0).map(([k, w]) => `${counts[k]} ${w}`);
  return parts.length ? parts.join(", ") : "Nothing to do";
}

export function intervalText(minutes: number): string {
  if (minutes === 60) return "every hour";
  if (minutes === 1440) return "every day";
  if (minutes % 60 === 0) return `every ${minutes / 60} hours`;
  return `every ${minutes} minutes`;
}

export const isRunning = (sources: Pick<SyncSource, "last_run">[]): boolean => sources.some((s) => s.last_run?.status === "RUNNING");

const REPO = /^[A-Za-z0-9_.-]{1,100}\/[A-Za-z0-9_.-]{1,100}$/;
const BRANCH = /^[A-Za-z0-9._/-]{1,100}$/;
const NAME = /^[A-Za-z0-9][A-Za-z0-9 _.\-/]{0,59}$/;

/** The same checks the server makes, so mistakes are shown before sending. The server stays the real gate. */
export function validateGithubForm(f: GithubForm): Partial<Record<keyof GithubForm, string>> {
  const e: Partial<Record<keyof GithubForm, string>> = {};
  if (!NAME.test(f.name.trim())) e.name = "Use letters, numbers, spaces, dots, dashes or slashes (up to 60), starting with a letter or number.";
  if (!REPO.test(f.repo.trim())) e.repo = "Write the repository as owner/name, for example aiwithpranav/securesearch-ai.";
  if (!BRANCH.test(f.branch.trim()) || f.branch.includes("..")) e.branch = "That branch name is not valid.";
  const p = f.path.trim();
  if (p.startsWith("/") || p.split("/").includes("..") || p.length > 200) e.path = "Write a folder inside the repository, such as demo-docs.";
  if (!f.departmentId) e.departmentId = "Choose a department for new documents.";
  return e;
}

/** The request body for a new GitHub source. No token is ever part of it. */
export function githubSourceBody(f: GithubForm) {
  return {
    name: f.name.trim(),
    kind: "github",
    interval_minutes: Number(f.interval),
    config: {
      repo: f.repo.trim(), branch: f.branch.trim() || "main", path: f.path.trim().replace(/^\/+|\/+$/g, ""), mirror_collaborators: f.mirror,
      department_id: Number(f.departmentId), document_type: f.documentType, sensitivity_level: Number(f.sensitivity),
    },
  };
}

/** A link to the folder on GitHub (settings come from the server; only a plain owner/name repository is linked). */
export function sourceLink(source: Pick<SyncSource, "kind" | "config">): string | null {
  if (source.kind !== "GITHUB") return null;
  const { repo, branch, path } = source.config as { repo?: string; branch?: string; path?: string };
  if (typeof repo !== "string" || !REPO.test(repo)) return null;
  return `https://github.com/${repo}/tree/${branch || "main"}${path ? `/${path}` : ""}`;
}
