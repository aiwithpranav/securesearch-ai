"""The access resolver, tested table by table. This is the most security-critical code in the project:
a mistake here is a data leak. Each case describes one situation and the expected answer.

Rules under test (blueprint 9.2): deny by default; a matching DENY beats any ALLOW; expired rules are
ignored; clearance >= sensitivity; country list empty or containing the user's country; the document
must be READY and not deleted; admin is never a reader."""
import pytest

from app.access import resolver as r
from app.db.sync import SyncSession
from tests.access_world import World


@pytest.fixture
def w(pg):
    return World(pg)


def check(user, doc, perm=r.READ):
    """Fresh session and fresh query every time: nothing is remembered between calls."""
    with SyncSession() as s:
        return r.can(s, user, doc, perm)


def why(user, doc, perm=r.READ):
    with SyncSession() as s:
        return r.explain(s, user, doc, perm)


PRINCIPALS = {
    "USER": lambda u: ("USER", u),
    "ROLE": lambda u: ("ROLE", "finance_role"),
    "GROUP": lambda u: ("GROUP", "finance_group"),
    "DEPARTMENT": lambda u: ("DEPARTMENT", "Finance"),
    "COMPANY": lambda u: ("COMPANY", None),
}


def member(w, **kw):
    """A user who matches every kind of principal above."""
    return w.user(dept="Finance", roles=("finance_role",), groups=("finance_group",), **kw)


# ------------------------------------------------------------------ deny by default, allow by principal

def test_a_document_without_any_rule_is_invisible_to_everybody(w):
    d = w.doc()
    for u in (member(w), w.user(roles=("system_admin",)), w.user(clearance=4)):
        assert check(u, d) is False
        assert why(u, d).code == r.NO_ALLOW_RULE


@pytest.mark.parametrize("kind", list(PRINCIPALS))
def test_an_allow_rule_for_each_kind_of_principal_grants_read(w, kind):
    u, d = member(w), w.doc()
    w.acl(d, PRINCIPALS[kind](u))
    assert check(u, d) is True and why(u, d).code == r.ALLOWED


@pytest.mark.parametrize("principal", [
    ("USER", "00000000-0000-0000-0000-000000000001"), ("ROLE", "other_role"), ("GROUP", "other_group"),
    ("DEPARTMENT", "HR"),
])
def test_an_allow_rule_for_somebody_else_grants_nothing(w, principal):
    u, d = member(w), w.doc()
    w.acl(d, principal)
    assert check(u, d) is False


# ------------------------------------------------------------------ deny beats allow

@pytest.mark.parametrize("allow", list(PRINCIPALS))
@pytest.mark.parametrize("deny", list(PRINCIPALS))
def test_a_matching_deny_beats_any_allow(w, allow, deny):
    u, d = member(w), w.doc()
    w.acl(d, PRINCIPALS[allow](u), effect="ALLOW")
    w.acl(d, PRINCIPALS[deny](u), effect="DENY")
    assert check(u, d) is False
    assert why(u, d).code == r.DENIED_BY_RULE


def test_a_deny_for_somebody_else_does_not_matter(w):
    u, d = member(w), w.doc()
    w.acl(d, ("COMPANY", None))
    w.acl(d, ("GROUP", "other_group"), effect="DENY")
    w.acl(d, ("USER", w.user()), effect="DENY")
    assert check(u, d) is True


def test_allow_through_one_group_and_deny_through_another_denies(w):
    u = w.user(groups=("g_allow", "g_deny"))
    d = w.doc()
    w.acl(d, ("GROUP", "g_allow"))
    w.acl(d, ("GROUP", "g_deny"), effect="DENY")
    assert check(u, d) is False


def test_ceo_scenario_reads_everything_except_one_denied_document(w):
    ceo = w.user("ceo@w", clearance=4, roles=("executive",))
    normal, secret = w.doc(), w.doc(sensitivity=3)
    for doc in (normal, secret):
        w.acl(doc, ("ROLE", "executive"))
    w.acl(secret, ("USER", ceo), effect="DENY")
    assert check(ceo, normal) is True
    assert check(ceo, secret) is False


# ------------------------------------------------------------------ expiry

@pytest.mark.parametrize("effect, expires, expected", [
    ("ALLOW", None, True),
    ("ALLOW", "1 hour", True),
    ("ALLOW", "5 seconds", True),
    ("ALLOW", "-1 second", False),
    ("ALLOW", "-1 day", False),
])
def test_allow_rules_stop_working_when_they_expire(w, effect, expires, expected):
    u, d = w.user(), w.doc()
    w.acl(d, ("USER", u), effect=effect, expires=expires)
    assert check(u, d) is expected


def test_an_expired_deny_no_longer_blocks_and_a_live_deny_still_does(w):
    u, d1, d2 = w.user(), w.doc(), w.doc()
    for d in (d1, d2):
        w.acl(d, ("COMPANY", None))
    w.acl(d1, ("USER", u), effect="DENY", expires="-1 hour")
    w.acl(d2, ("USER", u), effect="DENY", expires="1 hour")
    assert check(u, d1) is True
    assert check(u, d2) is False


# ------------------------------------------------------------------ clearance gate

@pytest.mark.parametrize("clearance, sensitivity, expected", [
    (0, 0, True), (1, 1, True), (2, 1, True), (4, 4, True), (3, 4, False), (1, 2, False), (0, 1, False),
])
def test_clearance_must_be_at_least_the_sensitivity(w, clearance, sensitivity, expected):
    u, d = w.user(clearance=clearance), w.doc(sensitivity=sensitivity)
    w.acl(d, ("COMPANY", None))
    assert check(u, d) is expected
    if not expected:
        assert why(u, d).code == r.CLEARANCE_TOO_LOW


# ------------------------------------------------------------------ country gate

@pytest.mark.parametrize("user_country, countries, expected", [
    ("IN", None, True),
    ("IN", ["IN"], True),
    ("IN", ["US", "IN", "GB"], True),
    ("IN", ["US"], False),
    ("IN", ["US", "GB"], False),
    ("IN", [], False),
])
def test_country_must_be_in_the_list_when_there_is_one(w, user_country, countries, expected):
    u, d = w.user(country=user_country), w.doc(countries=countries)
    w.acl(d, ("COMPANY", None))
    assert check(u, d) is expected
    if not expected:
        assert why(u, d).code == r.COUNTRY_NOT_ALLOWED


# ------------------------------------------------------------------ document state and user state

@pytest.mark.parametrize("status, deleted, expected", [
    ("READY", False, True), ("QUEUED", False, False), ("PROCESSING", False, False),
    ("FAILED", False, False), ("READY", True, False),
])
def test_only_ready_and_not_deleted_documents_can_be_read(w, status, deleted, expected):
    u, d = w.user(), w.doc(status=status, deleted=deleted)
    w.acl(d, ("COMPANY", None))
    assert check(u, d) is expected
    if not expected:
        assert why(u, d).code == r.DOCUMENT_UNAVAILABLE


def test_a_deactivated_user_reads_nothing(w):
    u, d = w.user(active=False), w.doc()
    w.acl(d, ("COMPANY", None))
    assert check(u, d) is False and why(u, d).code == r.USER_INACTIVE


def test_an_unknown_user_reads_nothing(w):
    import uuid
    d = w.doc()
    w.acl(d, ("COMPANY", None))
    assert check(uuid.uuid4(), d) is False


# ------------------------------------------------------------------ permissions are separate

def test_download_and_manage_rules_do_not_grant_read(w):
    u = w.user()
    d1, d2 = w.doc(), w.doc()
    w.acl(d1, ("USER", u), permission="DOWNLOAD")
    w.acl(d2, ("USER", u), permission="MANAGE")
    assert check(u, d1) is False and check(u, d2) is False


# ------------------------------------------------------------------ admin is not reader

def test_system_admin_does_not_get_read_access_from_the_role(w):
    admin = w.user("admin@w", clearance=4, roles=("system_admin",))
    d = w.doc()
    assert check(admin, d) is False
    w.acl(d, ("ROLE", "employee"))  # a rule for a role the admin does not hold
    assert check(admin, d) is False


def test_system_admin_can_manage_but_that_is_not_read(w):
    admin = w.user("admin@w", roles=("system_admin",))
    d = w.doc()
    assert check(admin, d, r.MANAGE) is True and check(admin, d, r.READ) is False


# ------------------------------------------------------------------ revocation is instant

def test_removing_a_user_from_a_group_cuts_access_on_the_next_check(w):
    u, d = w.user(groups=("finance_managers",)), w.doc()
    w.acl(d, ("GROUP", "finance_managers"))
    assert check(u, d) is True
    w.remove_from_group(u, "finance_managers")
    assert check(u, d) is False


def test_changing_department_changes_access_on_the_next_check(w):
    u, d = w.user(dept="Finance"), w.doc()
    w.acl(d, ("DEPARTMENT", "Finance"))
    assert check(u, d) is True
    w.move_to_department(u, "HR")
    assert check(u, d) is False


def test_deleting_a_rule_deactivating_the_user_or_deleting_the_document_cuts_access(w, pg):
    u, d = w.user(), w.doc()
    w.acl(d, ("COMPANY", None))
    assert check(u, d) is True
    pg.execute("update users set is_active=false where id=%s", (u,))
    assert check(u, d) is False
    pg.execute("update users set is_active=true where id=%s", (u,))
    assert check(u, d) is True
    pg.execute("update documents set deleted_at=now() where id=%s", (d,))
    assert check(u, d) is False
    pg.execute("update documents set deleted_at=null where id=%s", (d,))
    pg.execute("delete from document_acl where document_id=%s", (d,))
    assert check(u, d) is False


# ------------------------------------------------------------------ MANAGE

def test_manage_rules(w):
    admin = w.user(roles=("system_admin",))
    manager = w.user()
    reader = w.user()
    d = w.doc(sensitivity=4, countries=["US"], status="FAILED")  # failed uploads can still be fixed
    w.acl(d, ("USER", manager), permission="MANAGE")
    w.acl(d, ("USER", reader), permission="READ")
    assert check(admin, d, r.MANAGE) is True
    assert check(manager, d, r.MANAGE) is True  # not limited by clearance or country
    assert check(reader, d, r.MANAGE) is False  # READ does not imply MANAGE


def test_a_deny_manage_blocks_a_manager_but_never_locks_out_the_admin(w):
    admin = w.user(roles=("system_admin",))
    manager = w.user()
    d = w.doc()
    w.acl(d, ("USER", manager), permission="MANAGE")
    w.acl(d, ("USER", manager), permission="MANAGE", effect="DENY")
    w.acl(d, ("COMPANY", None), permission="MANAGE", effect="DENY")
    assert check(manager, d, r.MANAGE) is False
    assert check(admin, d, r.MANAGE) is True


def test_deleted_documents_and_inactive_users_cannot_be_managed(w):
    admin, inactive_admin = w.user(roles=("system_admin",)), w.user(roles=("system_admin",), active=False)
    d, gone = w.doc(), w.doc(deleted=True)
    assert check(admin, d, r.MANAGE) and not check(admin, gone, r.MANAGE) and not check(inactive_admin, d, r.MANAGE)


# ------------------------------------------------------------------ DOWNLOAD

def test_download_needs_read_and_an_explicit_download_rule(w):
    u = w.user()
    both, read_only, download_only, denied_read, denied_dl = (w.doc() for _ in range(5))
    w.acl(both, ("USER", u)); w.acl(both, ("USER", u), permission="DOWNLOAD")
    w.acl(read_only, ("USER", u))
    w.acl(download_only, ("USER", u), permission="DOWNLOAD")
    w.acl(denied_read, ("USER", u)); w.acl(denied_read, ("USER", u), permission="DOWNLOAD"); w.acl(denied_read, ("USER", u), effect="DENY")
    w.acl(denied_dl, ("USER", u)); w.acl(denied_dl, ("USER", u), permission="DOWNLOAD"); w.acl(denied_dl, ("COMPANY", None), permission="DOWNLOAD", effect="DENY")
    assert [check(u, x, r.DOWNLOAD) for x in (both, read_only, download_only, denied_read, denied_dl)] == [True, False, False, False, False]


# ------------------------------------------------------------------ allow-list and explanations agree

def test_allow_list_contains_exactly_the_readable_documents(w):
    u = w.user(clearance=2, groups=("g",))
    ok1, ok2 = w.doc(), w.doc(sensitivity=2)
    no_rule, too_secret, wrong_country = w.doc(), w.doc(sensitivity=3), w.doc(countries=["US"])
    unprocessed = w.doc(status="PROCESSING")
    for d in (ok1, too_secret, wrong_country, unprocessed):
        w.acl(d, ("COMPANY", None))
    w.acl(ok2, ("GROUP", "g"))
    with SyncSession() as s:
        assert r.allowed_ids(s, u) == {ok1, ok2}
    assert no_rule not in {ok1, ok2}


def test_every_denial_has_a_clear_reason_code(w):
    u = w.user(clearance=1)
    d_ok = w.doc()
    w.acl(d_ok, ("COMPANY", None))
    assert why(u, d_ok) == r.Decision(True, "ALLOWED")
    assert why(w.user(active=False), d_ok).code == "USER_INACTIVE"
    assert why(u, w.doc(status="QUEUED")).code == "DOCUMENT_UNAVAILABLE"
    assert why(u, w.doc()).code == "NO_ALLOW_RULE"
    denied = w.doc()
    w.acl(denied, ("COMPANY", None)); w.acl(denied, ("USER", u), effect="DENY")
    assert why(u, denied).code == "DENIED_BY_RULE"


def test_matching_rules_helper_lists_only_live_matching_rules(w):
    u, d = member(w), w.doc()
    w.acl(d, ("USER", u)); w.acl(d, ("GROUP", "finance_group"), effect="DENY")
    w.acl(d, ("DEPARTMENT", "HR")); w.acl(d, ("ROLE", "finance_role"), expires="-1 hour")
    with SyncSession() as s:
        ids = s.scalars(r.matching_rules_stmt(u, d, r.READ)).all()
    assert len(ids) == 2  # the user rule and the group deny; not HR, not the expired one
