// Who sees which management screens. This only decides what the menu SHOWS: the API checks the role on every request.
export type MenuLink = { href: string; label: string };

const has = (roles: string[], ...wanted: string[]) => wanted.some((r) => roles.includes(r));

export const canSeeAudit = (roles: string[]) => has(roles, "security_admin", "auditor");
export const canSeeGaps = (roles: string[]) => has(roles, "system_admin", "security_admin");

/** The links under the "Manage" menu for this person, in a fixed order. Empty when they manage nothing. */
export function manageLinks(roles: string[]): MenuLink[] {
  const links: MenuLink[] = [];
  if (has(roles, "system_admin")) {
    links.push(
      { href: "/admin/overview", label: "Overview" },
      { href: "/admin/documents", label: "Documents" },
      { href: "/admin/users", label: "Users" },
      { href: "/admin/groups", label: "Groups" },
    );
  }
  if (canSeeGaps(roles)) links.push({ href: "/gaps", label: "Knowledge gaps" });
  if (canSeeAudit(roles)) links.push({ href: "/audit", label: "Audit" });
  if (has(roles, "system_admin")) links.push({ href: "/admin/evaluation", label: "Evaluation" });
  return links;
}
