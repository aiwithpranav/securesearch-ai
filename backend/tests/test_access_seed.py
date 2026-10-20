"""The demo access rules: who can read what, per persona. This is the 'proof' table for Phase 4."""
from app.access import resolver as r
from app.db.sync import SyncSession
from app.scripts import synthetic_docs as sd
from app.scripts.seed_access import RULES, apply
from app.scripts.seed_users import DEPARTMENTS, USERS
from tests.access_world import World

COMPANY = {"holiday-calendar-2026.txt", "leave-policy.md", "onboarding-guide.txt", "security-awareness.pdf"}

EXPECTED = {
    "swara@demo": COMPANY | {"payments-runbook.md", "support-escalation.md", "poisoned-note.txt"},
    "pranav@demo": COMPANY,  # in Finance Managers, but clearance 2 is below the forecast's 3
    "dhanashree@demo": COMPANY | {"salary-bands-2026.docx"},
    "akshay@demo": COMPANY | {"pricing-playbook.docx"},
    "sanjana@demo": COMPANY | {"incident-report-2026-07.pdf"},
    "shivam@demo": COMPANY | {"fy2026-budget-forecast.pdf", "pricing-playbook.docx", "incident-report-2026-07.pdf",
                              "vendor-contract-summary.docx"},  # the CEO: everything except the salary bands
    "prashant@demo": COMPANY,  # the administrator: not a reader of anything beyond company-wide documents
    "karunesh@demo": COMPANY,  # the auditor: metadata only for the rest
    "former@demo": set(),      # deactivated
}


def build(pg):
    w = World(pg)
    for name in DEPARTMENTS:
        if not pg.execute("select 1 from departments where name=%s", (name,)).fetchone():
            pg.execute("insert into departments (name) values (%s)", (name,))
    users = {}
    for email, name, dept, clearance, country, employment, roles, active in USERS:
        users[email] = w.user(email, dept=dept, clearance=clearance, country=country, active=active, roles=roles)
    docs = {}
    for s in sd.SAMPLES:
        docs[s.filename] = w.doc(sensitivity=s.sensitivity, dept=s.department, filename=s.filename, document_type=s.document_type)
    return users, docs


def readable_files(users, docs):
    by_id = {v: k for k, v in docs.items()}
    out = {}
    with SyncSession() as s:
        for email, uid in users.items():
            out[email] = {by_id[d] for d in r.allowed_ids(s, uid)}
    return out


def test_before_the_seed_nobody_can_read_anything(pg):
    users, docs = build(pg)
    assert all(files == set() for files in readable_files(users, docs).values())  # deny by default


def test_each_persona_reads_exactly_what_they_should(pg):
    users, docs = build(pg)
    with SyncSession.begin() as s:
        counts = apply(s)
    assert counts["groups"] == 6 and counts["documents_missing"] == 0
    assert readable_files(users, docs) == EXPECTED


def test_the_clearance_gate_and_the_ceo_exception_are_visible_in_the_explanations(pg):
    users, docs = build(pg)
    with SyncSession.begin() as s:
        apply(s)
    with SyncSession() as s:
        assert r.explain(s, users["pranav@demo"], docs["fy2026-budget-forecast.pdf"]).code == r.CLEARANCE_TOO_LOW
        assert r.explain(s, users["shivam@demo"], docs["salary-bands-2026.docx"]).code == r.DENIED_BY_RULE
        assert r.explain(s, users["prashant@demo"], docs["salary-bands-2026.docx"]).code == r.NO_ALLOW_RULE
        assert r.can(s, users["prashant@demo"], docs["salary-bands-2026.docx"], r.MANAGE) is True  # manage, never read


def test_the_seed_is_safe_to_run_twice_and_records_history(pg):
    users, docs = build(pg)
    with SyncSession.begin() as s:
        first = apply(s)
    with SyncSession.begin() as s:
        second = apply(s)
    assert first["rules"] == sum(len(v) for v in RULES.values()) and second == {"groups": 0, "members": 0, "rules": 0, "documents_missing": 0}
    assert pg.execute("select count(*) from document_acl").fetchone()[0] == first["rules"]
    assert pg.execute("select count(*) from permission_change_events").fetchone()[0] == len(RULES)
    assert readable_files(users, docs) == EXPECTED
