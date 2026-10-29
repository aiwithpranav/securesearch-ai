// Types, plain-English wording and API calls for the admin Users, Groups and Access screens (Phase 4C).
//
// PRIVACY RULE (admin is not reader): nothing here, and no API answer, contains document TEXT.
// Screens show people, groups, rules, reasons and counts only.
import type { Department, User } from "./api";
import { authedApi } from "./session";

export type Role = { id: number; name: string; description: string | null };
export type UserItem = User & { employment_type: string };
export type UserPage = { items: UserItem[]; total: number; limit: number; offset: number };
export type Group = { id: number; name: string; description: string | null; member_count: number };
export type Member = { id: string; email: string; full_name: string };
export type GroupDetail = Group & { members: Member[] };

export type PrincipalType = "USER" | "ROLE" | "GROUP" | "DEPARTMENT" | "COMPANY";
export type Effect = "ALLOW" | "DENY";
export type Permission = "READ" | "DOWNLOAD" | "MANAGE";

export type Rule = {
  id: string;
  principal_type: PrincipalType;
  principal_id: string | null;
  principal_name: string;
  effect: Effect;
  permission: Permission;
  expires_at: string | null;
  expired: boolean;
  granted_by: string | null;
  created_at: string;
};

export type HistoryItem = {
  id: string;
  changed_at: string;
  changed_by: Member | null;
  prev_acl: SnapshotRule[];
  new_acl: SnapshotRule[];
};
export type SnapshotRule = {
  id: string;
  principal_type: PrincipalType;
  principal_name?: string;
  principal_id: string | null;
  effect: Effect;
  permission: Permission;
  expires_at: string | null;
};

export type Decision = { allowed: boolean; code: string };
export type Preview = {
  user: { id: string; email: string; full_name: string; department: Department; clearance_level: number; country: string; is_active: boolean; roles: string[] };
  document_status: string;
  sensitivity_level: number;
  allowed_countries: string[] | null;
  read: Decision;
  download: Decision;
  manage: Decision;
  matching_rules: Rule[];
};

export const PRINCIPAL_TYPES: { value: PrincipalType; label: string }[] = [
  { value: "USER", label: "A person" },
  { value: "ROLE", label: "A role" },
  { value: "GROUP", label: "A group" },
  { value: "DEPARTMENT", label: "A department" },
  { value: "COMPANY", label: "Everyone" },
];

export const PERMISSION_LABELS: Record<Permission, string> = {
  READ: "Can read",
  DOWNLOAD: "Can download",
  MANAGE: "Can manage rules and details",
};
export const EFFECT_LABELS: Record<Effect, string> = { ALLOW: "Allow", DENY: "Deny" };

export const EMPLOYMENT_TYPES = ["full_time", "part_time", "contractor", "intern"] as const;
export const employmentLabel = (v: string): string => v.replace("_", " ").replace(/^./, (c) => c.toUpperCase());

/** One sentence for a rule, for example "Deny Shivam Suryawanshi: can read". */
export function describeRule(r: { effect: Effect; principal_name?: string; permission: Permission }): string {
  return `${EFFECT_LABELS[r.effect]} ${r.principal_name ?? "(unknown)"}: ${PERMISSION_LABELS[r.permission].toLowerCase()}`;
}

const REASONS: Record<string, string> = {
  ALLOWED: "Yes. A rule allows it and nothing blocks it.",
  NO_ALLOW_RULE: "No. No rule allows this person. Nobody has access unless a rule says so.",
  DENIED_BY_RULE: "No. A Deny rule blocks this person. A Deny always wins over an Allow.",
  CLEARANCE_TOO_LOW: "No. The person's clearance level is lower than the document's sensitivity level.",
  COUNTRY_NOT_ALLOWED: "No. The document is limited to other countries than this person's.",
  DOCUMENT_UNAVAILABLE: "No. The document is deleted or has not finished processing.",
  USER_INACTIVE: "No. This account is deactivated.",
};
export const reasonText = (code: string): string => REASONS[code] ?? "No.";

export function expiryText(rule: { expires_at: string | null; expired: boolean }): string {
  if (!rule.expires_at) return "Never expires";
  const when = new Date(rule.expires_at);
  const text = Number.isNaN(when.getTime()) ? "" : when.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  return rule.expired ? `Expired ${text}` : `Until ${text}`;
}

/** Value of an <input type="datetime-local"> (local time) to an ISO string, or null when empty. */
export function localInputToIso(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

/** Plain-English summary of what changed between two rule lists (for the history view). */
export function diffRules(prev: SnapshotRule[], next: SnapshotRule[]): { added: SnapshotRule[]; removed: SnapshotRule[]; changed: SnapshotRule[] } {
  const prevById = new Map(prev.map((r) => [r.id, r]));
  const nextById = new Map(next.map((r) => [r.id, r]));
  return {
    added: next.filter((r) => !prevById.has(r.id)),
    removed: prev.filter((r) => !nextById.has(r.id)),
    changed: next.filter((r) => {
      const old = prevById.get(r.id);
      return !!old && (old.effect !== r.effect || old.permission !== r.permission || old.expires_at !== r.expires_at);
    }),
  };
}

// ----------------------------------------------------------------------------- API calls

// The Users list pages, searches and filters on the server (Phase 10B). The old call asked for one page of 100 people,
// so with more than 100 accounts the rest could not be reached.
export const USER_PAGE_SIZE = 50;
export type UserStatus = "" | "active" | "inactive";
export type UserQuery = { limit?: number; offset?: number; q?: string; departmentId?: string; status?: UserStatus; role?: string };

/** The query string for GET /users. Blank values are left out; the search text is trimmed. */
export function usersQueryString(p: UserQuery = {}): string {
  const params = new URLSearchParams({ limit: String(p.limit ?? USER_PAGE_SIZE), offset: String(p.offset ?? 0) });
  const q = p.q?.trim();
  if (q) params.set("q", q.slice(0, 100));
  if (p.departmentId) params.set("department_id", p.departmentId);
  if (p.status === "active") params.set("is_active", "true");
  if (p.status === "inactive") params.set("is_active", "false");
  if (p.role) params.set("role", p.role);
  return `?${params.toString()}`;
}

/** "from to of total" for a page, and whether Previous and Next make sense. */
export function pageRange(offset: number, limit: number, total: number) {
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  return { from, to, hasPrevious: offset > 0, hasNext: offset + limit < total };
}

export const listUsers = (p: UserQuery = {}) => authedApi<UserPage>(`/users${usersQueryString(p)}`);
export const createUser = (body: Record<string, unknown>) => authedApi<UserItem>("/users", { method: "POST", body });
export const updateUser = (id: string, body: Record<string, unknown>) => authedApi<UserItem>(`/users/${id}`, { method: "PATCH", body });
export const setUserRoles = (id: string, roleIds: number[]) =>
  authedApi<UserItem>(`/users/${id}/roles`, { method: "POST", body: { role_ids: roleIds } });
export const deactivateUser = (id: string) => authedApi<UserItem>(`/users/${id}/deactivate`, { method: "POST" });
export const listRoles = () => authedApi<Role[]>("/roles");

export const listGroups = () => authedApi<Group[]>("/groups");
export const createGroup = (name: string, description: string | null) =>
  authedApi<Group>("/groups", { method: "POST", body: { name, description } });
export const getGroup = (id: number) => authedApi<GroupDetail>(`/groups/${id}`);
export const addMember = (groupId: number, userId: string) =>
  authedApi<GroupDetail>(`/groups/${groupId}/members`, { method: "POST", body: { user_id: userId } });
export const removeMember = (groupId: number, userId: string) =>
  authedApi<void>(`/groups/${groupId}/members?user_id=${userId}`, { method: "DELETE" });

export const listRules = (docId: string) => authedApi<Rule[]>(`/documents/${docId}/acl`);
export const addRule = (docId: string, body: Record<string, unknown>) => authedApi<Rule>(`/documents/${docId}/acl`, { method: "POST", body });
export const updateRule = (docId: string, ruleId: string, body: Record<string, unknown>) =>
  authedApi<Rule>(`/documents/${docId}/acl/${ruleId}`, { method: "PATCH", body });
export const deleteRule = (docId: string, ruleId: string) => authedApi<void>(`/documents/${docId}/acl/${ruleId}`, { method: "DELETE" });
export const ruleHistory = (docId: string) => authedApi<HistoryItem[]>(`/documents/${docId}/acl/history?limit=30`);
export const accessPreview = (docId: string, userId: string) =>
  authedApi<Preview>(`/documents/${docId}/access-preview?user_id=${userId}`);
