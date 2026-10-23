"""Creates demo groups, group members and access rules for the 12 synthetic documents.

Run inside the backend container (users and documents must exist first):
    docker compose exec backend python -m app.scripts.seed_access

Safe to run twice: groups, members and rules that already exist are skipped. Each document whose rules
change gets a history row. Synthetic data only; refuses to run when APP_ENV is production.

What the rules express (blueprint personas):
- Company-wide documents: everybody (subject to the clearance gate).
- HR salary bands: the HR Team group and HR managers; the CEO is denied (the "everything except one" case).
- Finance forecast: the Finance Managers group and executives. The finance ANALYST is in the group but his
  clearance (2) is below the document's sensitivity (3), so the clearance gate stops him.
- Engineering and support runbooks: the engineer role and the SRE group (not a whole department, so the
  system administrator, who sits in Engineering, does NOT read them: admin is not reader).
- The auditor reads only company-wide documents (metadata only for the rest)."""
import sys

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.sync import SyncSession
from app.models import Department, Document, DocumentAcl, Group, PermissionChangeEvent, Role, User, user_groups

GROUPS: dict[str, list[str]] = {
    "Finance Managers": ["pranav@demo"],
    "HR Team": ["dhanashree@demo"],
    "SRE": ["swara@demo"],
    "Security Team": ["sanjana@demo"],
    "Sales Leads": ["akshay@demo"],
    "Legal Reviewers": [],  # empty on purpose: the auditor must not read contract content
}

COMPANY = ("COMPANY", None)
EXEC = ("ROLE", "executive")

# filename -> list of (principal, effect, permission)
RULES: dict[str, list[tuple[tuple[str, str | None], str, str]]] = {
    "holiday-calendar-2026.txt": [(COMPANY, "ALLOW", "READ")],
    "leave-policy.md": [(COMPANY, "ALLOW", "READ")],
    "onboarding-guide.txt": [(COMPANY, "ALLOW", "READ")],
    "security-awareness.pdf": [(COMPANY, "ALLOW", "READ")],
    "salary-bands-2026.docx": [
        (("GROUP", "HR Team"), "ALLOW", "READ"), (("ROLE", "hr_manager"), "ALLOW", "READ"),
        (EXEC, "ALLOW", "READ"), (("USER", "shivam@demo"), "DENY", "READ"),
    ],
    "fy2026-budget-forecast.pdf": [(("GROUP", "Finance Managers"), "ALLOW", "READ"), (EXEC, "ALLOW", "READ")],
    "payments-runbook.md": [(("ROLE", "engineer"), "ALLOW", "READ"), (("GROUP", "SRE"), "ALLOW", "READ")],
    "pricing-playbook.docx": [
        (("DEPARTMENT", "Sales"), "ALLOW", "READ"), (("GROUP", "Sales Leads"), "ALLOW", "READ"), (EXEC, "ALLOW", "READ"),
    ],
    "incident-report-2026-07.pdf": [
        (("GROUP", "Security Team"), "ALLOW", "READ"), (("ROLE", "security_admin"), "ALLOW", "READ"), (EXEC, "ALLOW", "READ"),
    ],
    "vendor-contract-summary.docx": [(("GROUP", "Legal Reviewers"), "ALLOW", "READ"), (EXEC, "ALLOW", "READ")],
    "support-escalation.md": [(("DEPARTMENT", "Customer Support"), "ALLOW", "READ"), (("GROUP", "SRE"), "ALLOW", "READ")],
    "poisoned-note.txt": [(("ROLE", "engineer"), "ALLOW", "READ")],
}


def _principal_id(s: Session, ptype: str, who: str | None) -> str | None:
    if ptype == "COMPANY":
        return None
    model_lookup = {
        "USER": (User, User.email), "ROLE": (Role, Role.name), "GROUP": (Group, Group.name), "DEPARTMENT": (Department, Department.name),
    }[ptype]
    row = s.scalar(select(model_lookup[0]).where(model_lookup[1] == who))
    if row is None:
        raise LookupError(f"{ptype} '{who}' does not exist")
    return str(row.id)  # type: ignore[attr-defined]


def _snapshot(s: Session, document_id) -> list[dict]:  # type: ignore[no-untyped-def]
    rules = s.scalars(select(DocumentAcl).where(DocumentAcl.document_id == document_id).order_by(DocumentAcl.created_at, DocumentAcl.id)).all()
    return [
        {"id": str(x.id), "principal_type": x.principal_type, "principal_id": x.principal_id, "effect": x.effect, "permission": x.permission,
         "expires_at": x.expires_at.isoformat() if x.expires_at else None}
        for x in rules
    ]


def apply(s: Session) -> dict[str, int]:
    """Applies the demo groups and rules inside the given session (the caller commits). Returns counts."""
    counts = {"groups": 0, "members": 0, "rules": 0, "documents_missing": 0}
    for name, emails in GROUPS.items():
        group = s.scalar(select(Group).where(Group.name == name))
        if group is None:
            group = Group(name=name, description="Demo group")
            s.add(group)
            s.flush()
            counts["groups"] += 1
        for email in emails:
            user = s.scalar(select(User).where(User.email == email))
            if user is None:
                continue
            exists = s.execute(select(user_groups).where(user_groups.c.user_id == user.id, user_groups.c.group_id == group.id)).first()
            if not exists:
                s.execute(user_groups.insert().values(user_id=user.id, group_id=group.id))
                counts["members"] += 1

    # The sales executive needs clearance 2 to read the CONFIDENTIAL pricing playbook.
    s.execute(update(User).where(User.email == "akshay@demo", User.clearance_level < 2).values(clearance_level=2))

    for filename, rules in RULES.items():
        doc = s.scalar(select(Document).where(Document.original_filename == filename, Document.deleted_at.is_(None)))
        if doc is None:
            counts["documents_missing"] += 1
            continue
        before = _snapshot(s, doc.id)
        added = 0
        for (ptype, who), effect, permission in rules:
            pid = _principal_id(s, ptype, who)
            existing = s.scalar(
                select(DocumentAcl).where(
                    DocumentAcl.document_id == doc.id, DocumentAcl.principal_type == ptype,
                    DocumentAcl.principal_id.is_(None) if pid is None else DocumentAcl.principal_id == pid,
                    DocumentAcl.effect == effect, DocumentAcl.permission == permission,
                )
            )
            if existing is None:
                s.add(DocumentAcl(document_id=doc.id, principal_type=ptype, principal_id=pid, effect=effect, permission=permission))
                added += 1
        if added:
            s.flush()
            s.add(PermissionChangeEvent(document_id=doc.id, prev_acl=before, new_acl=_snapshot(s, doc.id), changed_by=None))
            counts["rules"] += added
    return counts


def main() -> int:
    if settings.app_env == "production":
        print("Refusing to seed demo access rules when APP_ENV is production.")
        return 1
    with SyncSession.begin() as s:
        try:
            counts = apply(s)
        except LookupError as exc:
            print(f"Missing data: {exc}. Run the seed scripts first (seed_users, load_synthetic_docs).")
            return 1
    print(
        f"Access seed done: {counts['groups']} group(s), {counts['members']} member(s), {counts['rules']} rule(s) added"
        + (f"; {counts['documents_missing']} demo document(s) not found (run load_synthetic_docs)." if counts["documents_missing"] else ".")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
