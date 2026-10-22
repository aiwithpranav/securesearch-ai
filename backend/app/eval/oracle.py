"""An independent answer to "may this person read this document?" for the evaluation.

It follows the blueprint rules in the plainest possible Python, reading raw rows, and does NOT use the SQL resolver.
The runner uses it to decide which documents a person must NOT receive (so the canary scanner knows what to look
for), and to check that every case is set up sensibly."""
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


class Oracle:
    def __init__(self, session: Session) -> None:
        q = lambda sql: session.execute(text(sql)).all()  # noqa: E731
        self.now: datetime = session.execute(text("select now()")).scalar()  # type: ignore[assignment]
        self.users = {r.email: r for r in q("select id, email, is_active, clearance_level, country, department_id from users")}
        self.roles: dict = {}
        for r in q("select ur.user_id, r.name from user_roles ur join roles r on r.id = ur.role_id"):
            self.roles.setdefault(r.user_id, set()).add(r.name)
        self.role_ids = {r.name: str(r.id) for r in q("select id, name from roles")}
        self.groups: dict = {}
        for r in q("select user_id, group_id from user_groups"):
            self.groups.setdefault(r.user_id, set()).add(str(r.group_id))
        self.docs = {
            r.title: r for r in q("select id, title, status, deleted_at, sensitivity_level, allowed_countries from documents")
        }
        self.acl = q("select document_id, principal_type, principal_id, effect, permission, expires_at from document_acl")

    def can_read(self, email: str, title: str) -> bool:
        u = self.users[email]
        doc = self.docs.get(title)
        if doc is None or not u.is_active:
            return False

        def matches(rule) -> bool:  # noqa: ANN001
            t, pid = rule.principal_type, rule.principal_id
            return (
                t == "COMPANY" or (t == "USER" and pid == str(u.id)) or (t == "DEPARTMENT" and pid == str(u.department_id))
                or (t == "GROUP" and pid in self.groups.get(u.id, set()))
                or (t == "ROLE" and pid in {self.role_ids[n] for n in self.roles.get(u.id, set())})
            )

        def live(rule, effect: str) -> bool:  # noqa: ANN001
            return (
                rule.document_id == doc.id and rule.permission == "READ" and rule.effect == effect
                and (rule.expires_at is None or rule.expires_at > self.now) and matches(rule)
            )

        return (
            doc.deleted_at is None and doc.status == "READY"
            and not any(live(r, "DENY") for r in self.acl) and any(live(r, "ALLOW") for r in self.acl)
            and doc.sensitivity_level <= u.clearance_level
            and (doc.allowed_countries is None or u.country in doc.allowed_countries)
        )

    def forbidden_titles(self, email: str) -> set[str]:
        return {t for t in self.docs if not self.can_read(email, t)}
