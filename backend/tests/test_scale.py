"""The scale demo helpers (Phase 10): classification, cleaning, people, canaries and the fast oracle.

Everything except the oracle test is pure Python. The oracle test compares the fast oracle with the SQL resolver in
random worlds, exactly like the Phase 4 test does for the first oracle."""
import pytest

from app.access import resolver as r
from app.db.sync import SyncSession
from app.scale.corpus import (
    CANARY_PREFIX,
    DEPARTMENT_RULE,
    MIN_BODY_CHARS,
    canary_for,
    classify,
    clean_markdown,
    fallback_title,
    rules_for,
    unique_filename,
    wants_canary,
    with_canary,
)
from app.scale.oracle import FastOracle
from app.scale.people import DEPARTMENT_ROLE, make_people
from tests.test_access_oracle import build_random_world

# ------------------------------------------------------------------ classification

@pytest.mark.parametrize("path, department, sensitivity", [
    ("kubernetes/concepts/overview/index.md", "Engineering", 1),
    ("docker/engine/install.md", "Engineering", 1),
    ("gitlab/people-group/onboarding/index.md", "HR", 2),
    ("gitlab/finance/expenses.md", "Finance", 2),
    ("gitlab/legal/contracts.md", "Legal", 2),
    ("gitlab/security/standards/index.md", "Security", 3),
    ("gitlab/engineering/handbook.md", "Engineering", 1),
    ("gitlab/company/mission.md", "Company-wide", 0),
    ("gitlab/board-meetings/2024/minutes.md", "Legal", 3),
    ("gitlab/people-policies/leave/index.md", "HR", 2),
    ("gitlab/customer-experience/handbook/index.md", "Customer Support", 1),
    ("gitlab/something-new/page.md", "Company-wide", 0),
    ("other/x.md", "Company-wide", 0),
])
def test_files_are_placed_by_their_path(path, department, sensitivity):
    p = classify(path)
    assert (p.department, p.sensitivity) == (department, sensitivity)


def test_tasks_and_troubleshooting_pages_are_runbooks_and_policies_are_policies():
    assert classify("kubernetes/tasks/run-application/x.md").document_type == "RUNBOOK"
    assert classify("kubernetes/concepts/x.md").document_type == "OTHER"
    assert classify("gitlab/people-group/vacation-policy.md").document_type == "POLICY"


def test_every_placement_has_a_rule_and_restricted_ones_also_open_to_executives():
    for path in ("kubernetes/a/b.md", "gitlab/security/a.md", "gitlab/company/a.md", "gitlab/legal/a.md"):
        p = classify(path)
        rules = rules_for(p)
        assert rules[0] == (DEPARTMENT_RULE[p.department], "ALLOW", "READ")
        executive_rule = (("ROLE", "executive"), "ALLOW", "READ")
        if p.sensitivity >= 2:
            assert executive_rule in rules
        else:
            assert rules == [rules[0]]


def test_the_system_admin_is_never_given_access_through_a_department():
    """He sits in Engineering, so Engineering documents must be opened by a role, not by the department."""
    assert DEPARTMENT_RULE["Engineering"][0] == "ROLE"


# ------------------------------------------------------------------ cleaning

def test_yaml_front_matter_is_removed_and_its_title_is_used():
    raw = "---\ntitle: \"Pods\"\nweight: 10\n---\n\n# Pods\n\nA Pod is the smallest unit.\n"
    title, body = clean_markdown(raw, "fallback")
    assert title == "Pods" and body.startswith("# Pods") and "weight" not in body


def test_toml_front_matter_shortcodes_and_comments_are_removed():
    raw = "+++\ntitle = 'Install'\n+++\n{{< note >}}Careful{{< /note >}}\n<!-- hidden -->\nText {{% include \"x.md\" %}} here\n\n\n\nEnd"
    title, body = clean_markdown(raw, "fallback")
    assert title == "Install"
    assert "{{" not in body and "hidden" not in body and "Careful" in body and "\n\n\n" not in body


def test_a_page_without_front_matter_uses_the_fallback_title_and_windows_line_endings_are_unified():
    title, body = clean_markdown("Line one\r\nLine two", "My Page")
    assert title == "My Page" and body == "Line one\nLine two"


def test_titles_from_file_names_and_unique_file_names():
    assert fallback_title("gitlab/people-group/onboarding/index.md") == "Onboarding"
    assert fallback_title("kubernetes/concepts/pod-lifecycle.md") == "Pod Lifecycle"
    a, b = unique_filename("kubernetes/a/index.md"), unique_filename("docker/a/index.md")
    assert a != b and a.endswith(".md") and unique_filename("kubernetes/a/index.md") == a
    assert len(unique_filename("x/" + "y" * 500 + ".md")) < 120


def test_the_minimum_body_length_is_a_sensible_cut_off():
    assert 100 <= MIN_BODY_CHARS <= 1000


# ------------------------------------------------------------------ canaries

def test_canaries_are_stable_unique_and_recognisable():
    assert canary_for("a/b.md") == canary_for("a/b.md") != canary_for("a/c.md")
    c = canary_for("a/b.md")
    assert c.startswith(CANARY_PREFIX) and len(c) == len(CANARY_PREFIX) + 8
    assert c in with_canary("Body text", c)


def test_every_restricted_document_has_a_canary_and_some_open_ones_too():
    assert all(wants_canary(f"gitlab/security/{n}.md", 3) for n in range(50))
    open_with = sum(wants_canary(f"kubernetes/{n}.md", 1) for n in range(2000))
    assert 50 < open_with < 200  # about one in twenty


# ------------------------------------------------------------------ people

def test_people_are_deterministic_and_reasonably_spread():
    a, b = make_people(500), make_people(500)
    assert a == b and make_people(500, seed=11) != a
    assert len({p.email for p in a}) == 500 and a[0].email == "big0001@demo"
    depts = {p.department for p in a}
    assert depts == {"Engineering", "Sales", "Customer Support", "Company-wide", "Finance", "HR", "Security", "Legal"}
    assert {p.clearance for p in a} == {0, 1, 2, 3, 4}
    assert all("employee" in p.roles for p in a)
    for p in a:
        if p.department in DEPARTMENT_ROLE:
            assert DEPARTMENT_ROLE[p.department] in p.roles
    assert 0 < sum("executive" in p.roles for p in a) < 40


# ------------------------------------------------------------------ the fast oracle

@pytest.mark.parametrize("seed", range(6))
def test_fast_oracle_agrees_with_the_sql_resolver_in_random_worlds(pg, seed):
    users, docs = build_random_world(pg, seed)
    checked = granted = 0
    with SyncSession() as s:
        oracle = FastOracle(s)
        for u in users:
            allowed = r.allowed_ids(s, u, r.READ)
            assert oracle.readable(u) == set(allowed), ("allow-list", u)
            for d in docs:
                checked += 1
                granted += oracle.can_read(u, d)
    assert checked == 7 * 14 and 0 < granted < checked
