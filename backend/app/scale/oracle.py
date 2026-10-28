"""An independent, fast answer to "which documents may this person read?" for the scale check.

Like app/eval/oracle.py it follows the blueprint rules in plain Python over raw rows and does NOT use the SQL resolver.
Unlike it, the rules are indexed by document, so it stays quick with thousands of documents and rules."""
from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class FastOracle:
    def __init__(self, session: Session) -> None:
        q = lambda sql: session.execute(text(sql)).all()  # noqa: E731
        self.now: datetime = session.execute(text("select now()")).scalar()  # type: ignore[assignment]
        self.users = {r.id: r for r in q("select id, email, is_active, clearance_level, country, department_id from users")}
        self.by_email = {u.email: u.id for u in self.users.values()}
        self.role_names = {r.id: r.name for r in q("select id, name from roles")}
        self.user_roles: dict[UUID, set[str]] = defaultdict(set)
        for r in q("select user_id, role_id from user_roles"):
            self.user_roles[r.user_id].add(str(r.role_id))
        self.user_groups: dict[UUID, set[str]] = defaultdict(set)
        for r in q("select user_id, group_id from user_groups"):
            self.user_groups[r.user_id].add(str(r.group_id))
        self.docs = {
            r.id: r for r in q("select id, status, deleted_at, sensitivity_level, allowed_countries from documents")
        }
        self.acl: dict[UUID, list] = defaultdict(list)
        for r in q("select document_id, principal_type, principal_id, effect, permission, expires_at from document_acl"):
            if r.permission == "READ" and (r.expires_at is None or r.expires_at > self.now):
                self.acl[r.document_id].append(r)

    def can_read(self, user_id: UUID, doc_id: UUID) -> bool:
        u, doc = self.users[user_id], self.docs.get(doc_id)
        if doc is None or not u.is_active or doc.deleted_at is not None or doc.status != "READY":
            return False
        if doc.sensitivity_level > u.clearance_level:
            return False
        if doc.allowed_countries is not None and u.country not in doc.allowed_countries:
            return False
        roles, groups = self.user_roles[user_id], self.user_groups[user_id]

        def matches(rule) -> bool:  # noqa: ANN001
            t, pid = rule.principal_type, rule.principal_id
            return (
                t == "COMPANY" or (t == "USER" and pid == str(u.id)) or (t == "DEPARTMENT" and pid == str(u.department_id))
                or (t == "GROUP" and pid in groups) or (t == "ROLE" and pid in roles)
            )

        live = [r for r in self.acl.get(doc_id, []) if matches(r)]
        return any(r.effect == "ALLOW" for r in live) and not any(r.effect == "DENY" for r in live)

    def readable(self, user_id: UUID) -> set[UUID]:
        return {d for d in self.docs if self.can_read(user_id, d)}
