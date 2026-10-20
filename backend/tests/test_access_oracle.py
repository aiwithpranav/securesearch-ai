"""Two independent implementations must agree.

For many random worlds we compare the SQL resolver with a plain-Python 'oracle' that follows the blueprint
rules in the simplest possible way. We also check that the three SQL entry points (the allow-list, the
single check and the step-by-step explanation) always give the same answer. A mistake in any one of them
shows up as a disagreement. Expiry times are always at least one hour away from 'now' so timing never matters."""
import random

import psycopg
import pytest

from app.access import resolver as r
from app.db.sync import SyncSession
from tests.access_world import World

DEPTS = ["Engineering", "Finance", "HR"]
ROLES = ["employee", "auditor", "system_admin", "r1"]
GROUPS = ["g1", "g2", "g3"]
COUNTRIES = ["IN", "US", "GB"]


def build_random_world(pg, seed):
    rnd = random.Random(seed)
    w = World(pg)
    users = [
        w.user(
            dept=rnd.choice(DEPTS), clearance=rnd.randint(0, 4), country=rnd.choice(COUNTRIES),
            active=rnd.random() < 0.9,
            roles=[x for x in ROLES if rnd.random() < 0.3], groups=[x for x in GROUPS if rnd.random() < 0.35],
        )
        for _ in range(7)
    ]
    docs = [
        w.doc(
            sensitivity=rnd.randint(0, 4), status=rnd.choices(["READY", "QUEUED", "FAILED"], [8, 1, 1])[0],
            countries=rnd.choice([None, None, [rnd.choice(COUNTRIES)], rnd.sample(COUNTRIES, 2)]),
            deleted=rnd.random() < 0.08,
        )
        for _ in range(14)
    ]
    for _ in range(70):
        kind = rnd.choice(["USER", "ROLE", "GROUP", "DEPARTMENT", "COMPANY"])
        who = {"USER": rnd.choice(users), "ROLE": rnd.choice(ROLES), "GROUP": rnd.choice(GROUPS),
               "DEPARTMENT": rnd.choice(DEPTS), "COMPANY": None}[kind]
        try:
            w.acl(
                rnd.choice(docs), (kind, who), effect=rnd.choices(["ALLOW", "DENY"], [7, 3])[0],
                permission=rnd.choices(["READ", "DOWNLOAD", "MANAGE"], [6, 2, 2])[0],
                expires=rnd.choice([None, None, None, "1 hour", "-1 hour", "3 days"]),
            )
        except psycopg.errors.UniqueViolation:
            pass  # the same rule twice is refused by the database
    return users, docs


def load(pg):
    """Everything the oracle needs, read with plain SQL."""
    now = pg.execute("select now()").fetchone()[0]
    users = {row[0]: row for row in pg.execute("select id, is_active, clearance_level, country, department_id from users").fetchall()}
    roles = {}
    for uid, rid in pg.execute("select user_id, role_id from user_roles").fetchall():
        roles.setdefault(uid, set()).add(str(rid))
    admin_role = pg.execute("select id from roles where name='system_admin'").fetchone()[0]
    groups = {}
    for uid, gid in pg.execute("select user_id, group_id from user_groups").fetchall():
        groups.setdefault(uid, set()).add(str(gid))
    docs = {row[0]: row for row in pg.execute("select id, status, deleted_at, sensitivity_level, allowed_countries from documents").fetchall()}
    acl = pg.execute("select document_id, principal_type, principal_id, effect, permission, expires_at from document_acl").fetchall()
    return now, users, roles, str(admin_role), groups, docs, acl


def oracle(data, user, doc, perm):
    now, users, roles, admin_role, groups, docs, acl = data
    _, active, clearance, country, dept = users[user]
    _, status, deleted_at, sensitivity, countries = docs[doc]
    if not active:
        return False

    def matches(rule):
        _, ptype, pid, _, _, _ = rule
        return (
            (ptype == "USER" and pid == str(user)) or (ptype == "ROLE" and pid in roles.get(user, set()))
            or (ptype == "GROUP" and pid in groups.get(user, set())) or (ptype == "DEPARTMENT" and pid == str(dept))
            or ptype == "COMPANY"
        )

    def live(rule, effect, permission):
        return rule[0] == doc and rule[3] == effect and rule[4] == permission and (rule[5] is None or rule[5] > now) and matches(rule)

    def grants(permission):
        return not any(live(x, "DENY", permission) for x in acl) and any(live(x, "ALLOW", permission) for x in acl)

    if perm == "MANAGE":
        if deleted_at is not None:
            return False
        return admin_role in roles.get(user, set()) or grants("MANAGE")
    can_read = (
        deleted_at is None and status == "READY" and grants("READ") and sensitivity <= clearance
        and (countries is None or country in countries)
    )
    return can_read and (perm == "READ" or grants("DOWNLOAD"))


@pytest.mark.parametrize("seed", range(8))
def test_sql_resolver_and_python_oracle_agree_in_random_worlds(pg, seed):
    users, docs = build_random_world(pg, seed)
    data = load(pg)
    checked = granted = 0
    with SyncSession() as s:
        for perm in (r.READ, r.DOWNLOAD, r.MANAGE):
            for u in users:
                listed = r.allowed_ids(s, u, perm)
                for d in docs:
                    expected = oracle(data, u, d, perm)
                    assert (d in listed) is expected, ("allow-list", perm, u, d)
                    assert r.can(s, u, d, perm) is expected, ("single check", perm, u, d)
                    assert r.explain(s, u, d, perm).allowed is expected, ("explanation", perm, u, d)
                    checked += 1
                    granted += expected
    assert checked == 3 * 7 * 14 and 0 < granted < checked  # the worlds really mix yes and no answers


# ------------------------------------------------------------------ the database refuses malformed rules

def _doc(pg):
    return World(pg).doc()


@pytest.mark.parametrize("ptype, pid, effect, perm", [
    ("COMPANY", "x", "ALLOW", "READ"),      # COMPANY must not name a principal
    ("USER", None, "ALLOW", "READ"),        # every other type must
    ("TEAM", "1", "ALLOW", "READ"),         # unknown principal type
    ("USER", "1", "MAYBE", "READ"),         # unknown effect
    ("USER", "1", "ALLOW", "SEARCH"),       # SEARCH was dropped from the design
])
def test_malformed_rules_are_rejected_by_the_database(pg, ptype, pid, effect, perm):
    d = _doc(pg)
    with pytest.raises(psycopg.errors.CheckViolation):
        pg.execute(
            "insert into document_acl (document_id, principal_type, principal_id, effect, permission)"
            " values (%s,%s,%s,%s,%s)", (d, ptype, pid, effect, perm),
        )


def test_the_same_rule_cannot_be_stored_twice_including_company_rules(pg):
    w = World(pg)
    d = w.doc()
    for principal in (("COMPANY", None), ("ROLE", "employee")):
        w.acl(d, principal)
        with pytest.raises(psycopg.errors.UniqueViolation):
            w.acl(d, principal)
    w.acl(d, ("COMPANY", None), effect="DENY")  # a different effect is a different rule


def test_deleting_a_document_removes_its_rules_and_history(pg):
    w = World(pg)
    d = w.doc()
    w.acl(d, ("COMPANY", None))
    pg.execute("insert into permission_change_events (document_id, prev_acl, new_acl) values (%s,'[]','[]')", (d,))
    pg.execute("delete from documents where id=%s", (d,))
    assert pg.execute("select count(*) from document_acl").fetchone()[0] == 0
    assert pg.execute("select count(*) from permission_change_events").fetchone()[0] == 0
