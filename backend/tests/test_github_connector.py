"""Phase 8C: the GitHub connector, against a fake GitHub (no network is ever used), and through the real sync engine.

Proven here: only the chosen folder and the allowed file types are imported (hidden folders never are); who may read a file
comes from the longest matching folder rule of the access file; people must be mapped to an account and, by default, be
collaborators of the repository, so removing a collaborator on GitHub removes their access at the next sync; every kind of
GitHub failure gives a fixed code word and changes nothing; and the token is only sent to GitHub's address and never appears in
a run, a log or an audit row."""
import asyncio
import base64
import hashlib
import json
import logging
import uuid

import httpx
import pytest

from app.core.config import settings
from app.sync import engine, github
from app.sync.base import SourceError
from tests.test_sync import ctx, queued, source_state  # noqa: F401  (the fixtures of the engine tests)

TOKEN = "ghp_test-token-123456"
HR_DOC = b"Salary bands for the made-up company: level one pays a made-up amount.\n"
POLICY = b"Leave policy: every employee receives twenty four days of leave.\n"
RUNBOOK = b"Runbook: restart the made-up payments service and check the dashboard.\n"
ACCESS = {"teams": {"staff": ["alice-gh", "bob-gh"], "hr": ["alice-gh", "carol-gh", "ghost-gh"]}, "access": {"": ["staff"], "hr/": ["hr"]}}
USERS = {"alice-gh": "alice@demo", "Bob-GH": "bob@demo", "carol-gh": "carol@demo"}


def sha(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()  # noqa: S324  (a git blob id is only a label here)


class FakeGitHub:
    """Answers the three GitHub calls the connector makes. Records what it was asked."""

    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.collaborators = ["alice-gh", "bob-gh", "carol-gh"]
        self.truncated = False
        self.fail_collaborators: int | None = None
        self.fail_tree: int | None = None
        self.rate_limited = False
        self.server_errors = 0  # how many 500s to answer before succeeding
        self.requests: list[httpx.Request] = []
        self.set_standard()

    def set_standard(self):
        self.files = {
            "README.md": b"Not part of the demo folder.\n",
            "docs-archive/long-archive-guide-name.md": b"Another folder, not imported.\n",
            "demo-docs/leave-policy.md": POLICY,
            "demo-docs/hr/salary-bands.md": HR_DOC,
            "demo-docs/runbooks/payments_runbook.txt": RUNBOOK,
            "demo-docs/notes.exe": b"MZ",
            "demo-docs/.hidden/secret.md": b"Hidden folder text.\n",
            "demo-docs/.securesearch/access.json": json.dumps(ACCESS).encode(),
            "demo-docs/.securesearch/users.json": json.dumps(USERS).encode(),
        }

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.headers.get("authorization") != f"Bearer {TOKEN}":
            return httpx.Response(401, json={"message": "Bad credentials"})
        if self.rate_limited:
            return httpx.Response(403, headers={"x-ratelimit-remaining": "0"}, json={"message": "rate limit"})
        if self.server_errors > 0:
            self.server_errors -= 1
            return httpx.Response(500)
        if not path.startswith("/repos/owner/docs"):
            return httpx.Response(404, json={"message": "Not Found"})
        if "/git/trees/" in path:
            if self.fail_tree:
                return httpx.Response(self.fail_tree)
            tree = [{"path": p, "type": "blob", "sha": sha(d), "size": len(d)} for p, d in self.files.items()] + [{"path": "demo-docs", "type": "tree", "sha": "t"}]
            return httpx.Response(200, json={"truncated": self.truncated, "tree": tree})
        if "/git/blobs/" in path:
            wanted = path.rsplit("/", 1)[-1]
            for d in self.files.values():
                if sha(d) == wanted:
                    return httpx.Response(200, json={"encoding": "base64", "content": base64.b64encode(d).decode(), "sha": wanted})
            return httpx.Response(404)
        if path.endswith("/collaborators"):
            if self.fail_collaborators:
                return httpx.Response(self.fail_collaborators, json={"message": "Must have push access"})
            page, per = int(request.url.params.get("page", "1")), int(request.url.params.get("per_page", "30"))
            rows = [{"login": lg, "permissions": {"pull": True, "push": False, "admin": False}} for lg in self.collaborators]
            return httpx.Response(200, json=rows[(page - 1) * per: page * per])
        return httpx.Response(404)


@pytest.fixture
def gh(monkeypatch):
    fake = FakeGitHub()
    monkeypatch.setattr(settings, "github_token", TOKEN)
    github.set_transport(httpx.MockTransport(fake))
    yield fake
    github.set_transport(None)


CFG = {"repo": "owner/docs", "branch": "main", "path": "demo-docs"}


def connector(**over):
    return github.GitHubConnector({**CFG, **over})


# ---------------------------------------------------------------- settings

@pytest.mark.parametrize("cfg, ok", [
    ({"repo": "owner/docs"}, True), ({"repo": "owner/docs", "branch": "release/1.0", "path": "demo-docs/hr"}, True),
    ({"repo": "owner/docs", "mirror_collaborators": False}, True),
    ({}, False), ({"repo": "justaname"}, False), ({"repo": "a/b/c"}, False), ({"repo": "https://evil.example/x"}, False),
    ({"repo": "owner/docs", "branch": "a..b"}, False), ({"repo": "owner/docs", "branch": "bad branch"}, False),
    ({"repo": "owner/docs", "path": "/etc"}, False), ({"repo": "owner/docs", "path": "../up"}, False),
    ({"repo": "owner/docs", "mirror_collaborators": "yes"}, False),
])
def test_settings_are_checked(cfg, ok):
    if ok:
        github.validate(cfg)
    else:
        with pytest.raises(ValueError):
            github.validate(cfg)


def test_the_longest_matching_folder_rule_wins_and_no_match_means_nobody():
    access = {"": ["staff"], "hr/": ["hr"], "hr/public/": ["hr", "staff"], "legal": ["legal"]}
    t = github.teams_for_path
    assert t("leave.md", access) == {"staff"}
    assert t("hr/salary.md", access) == {"hr"}
    assert t("hr/public/faq.md", access) == {"hr", "staff"}
    assert t("legal/contract.md", access) == {"legal"}  # a prefix without a slash still means the folder
    assert t("hrx/file.md", {"hr/": ["hr"]}) == frozenset()  # hr/ does not match hrx/
    assert t("anything.md", {}) == frozenset()


# ---------------------------------------------------------------- listing and reading

def test_only_the_chosen_folder_and_the_allowed_types_are_listed(gh):
    items = connector().list_items()
    assert [i.external_id for i in items] == ["demo-docs/hr/salary-bands.md", "demo-docs/leave-policy.md", "demo-docs/runbooks/payments_runbook.txt"]
    by = {i.external_id: i for i in items}
    assert by["demo-docs/leave-policy.md"].title == "Leave policy" and by["demo-docs/leave-policy.md"].filename == "leave-policy.md"
    assert by["demo-docs/runbooks/payments_runbook.txt"].title == "Payments runbook"
    assert by["demo-docs/leave-policy.md"].url == "https://github.com/owner/docs/blob/main/demo-docs/leave-policy.md"
    assert by["demo-docs/hr/salary-bands.md"].groups == {"hr"} and by["demo-docs/leave-policy.md"].groups == {"staff"}
    assert by["demo-docs/runbooks/payments_runbook.txt"].groups == {"staff"}


def test_the_whole_repository_can_be_the_source(gh):
    ids = {i.external_id for i in connector(path="").list_items()}
    assert "README.md" in ids and "demo-docs/leave-policy.md" in ids and not any(".securesearch" in i or ".hidden" in i for i in ids)


def test_reading_an_item_returns_its_exact_bytes(gh):
    c = connector()
    items = c.list_items()
    assert c.read(next(i for i in items if i.title == "Leave policy")) == POLICY


def test_files_that_are_too_large_are_not_listed(gh):
    gh.files["demo-docs/huge.pdf"] = b"x"
    original = gh.__call__

    def big(request):
        r = original(request)
        if "/git/trees/" in request.url.path:
            data = r.json()
            for e in data["tree"]:
                if e["path"].endswith("huge.pdf"):
                    e["size"] = github.MAX_FILE_BYTES + 1
            return httpx.Response(200, json=data)
        return r

    github.set_transport(httpx.MockTransport(big))
    assert "demo-docs/huge.pdf" not in {i.external_id for i in connector().list_items()}


def test_a_damaged_access_file_is_refused_not_guessed(gh):
    gh.files["demo-docs/.securesearch/access.json"] = b"{ not json"
    with pytest.raises(SourceError) as e:
        connector().list_items()
    assert e.value.code == "BAD_ACCESS_FILE"
    gh.files["demo-docs/.securesearch/access.json"] = json.dumps({"access": {"": "staff"}}).encode()
    with pytest.raises(SourceError) as e:
        connector().list_items()
    assert e.value.code == "BAD_ACCESS_FILE"


def test_without_an_access_file_nobody_may_read(gh):
    del gh.files["demo-docs/.securesearch/access.json"]
    assert all(i.groups == frozenset() for i in connector().list_items())


# ---------------------------------------------------------------- members

def test_members_are_mapped_to_accounts_and_must_be_collaborators(gh):
    c = connector()
    c.list_items()
    assert c.members() == {"staff": {"alice@demo", "bob@demo"}, "hr": {"alice@demo", "carol@demo"}}  # ghost-gh has no account; case ignored
    gh.collaborators = ["alice-gh"]  # bob and carol were removed on GitHub
    assert c.members() == {"staff": {"alice@demo"}, "hr": {"alice@demo"}}


def test_without_mirroring_the_collaborator_list_is_not_asked_for(gh):
    c = connector(mirror_collaborators=False)
    c.list_items()
    gh.collaborators = []
    assert c.members()["staff"] == {"alice@demo", "bob@demo"}
    assert not any(r.url.path.endswith("/collaborators") for r in gh.requests)


def test_more_than_one_page_of_collaborators_is_read(gh):
    gh.collaborators = [f"user{i}" for i in range(150)] + ["alice-gh"]
    c = connector()
    c.list_items()
    assert "alice@demo" in c.members()["staff"]


# ---------------------------------------------------------------- failures give code words

@pytest.mark.parametrize("setup, code", [
    (lambda g, m: setattr(g, "truncated", True), "TREE_TOO_LARGE"),
    (lambda g, m: setattr(g, "rate_limited", True), "RATE_LIMITED"),
    (lambda g, m: setattr(g, "fail_tree", 404), "NOT_FOUND"),
    (lambda g, m: setattr(g, "fail_tree", 418), "SOURCE_UNREACHABLE"),
    (lambda g, m: m.setattr(settings, "github_token", "wrong-token"), "BAD_CREDENTIALS"),
    (lambda g, m: m.setattr(settings, "github_token", ""), "TOKEN_MISSING"),
])
def test_every_kind_of_failure_has_a_fixed_code_and_never_shows_the_token(gh, monkeypatch, setup, code):
    setup(gh, monkeypatch)
    with pytest.raises(SourceError) as e:
        connector().list_items()
    assert e.value.code == code and TOKEN not in str(e.value) and "wrong-token" not in str(e.value)


def test_a_repository_that_does_not_exist_is_not_found(gh):
    with pytest.raises(SourceError) as e:
        github.GitHubConnector({"repo": "owner/missing", "path": "x"}).list_items()
    assert e.value.code == "NOT_FOUND"


def test_a_missing_permission_to_read_collaborators_is_its_own_code(gh):
    gh.fail_collaborators = 403
    c = connector()
    c.list_items()
    with pytest.raises(SourceError) as e:
        c.members()
    assert e.value.code == "PERMISSIONS_UNAVAILABLE"


def test_one_server_error_is_retried_once_and_two_are_not(gh):
    gh.server_errors = 1
    assert len(connector().list_items()) == 3
    gh.server_errors = 2
    with pytest.raises(SourceError) as e:
        connector().list_items()
    assert e.value.code == "SOURCE_UNREACHABLE"


def test_a_network_failure_is_unreachable(monkeypatch):
    monkeypatch.setattr(settings, "github_token", TOKEN)

    def boom(request):
        raise httpx.ConnectError("no route")

    github.set_transport(httpx.MockTransport(boom))
    try:
        with pytest.raises(SourceError) as e:
            connector().list_items()
        assert e.value.code == "SOURCE_UNREACHABLE"
    finally:
        github.set_transport(None)


def test_the_token_goes_only_to_the_github_address_from_the_environment(gh):
    connector().list_items()
    assert gh.requests and {r.url.host for r in gh.requests} == {"api.github.com"}
    assert all(r.headers["authorization"] == f"Bearer {TOKEN}" for r in gh.requests)
    # the repository comes from saved settings, but only as a checked owner/name, never as an address
    with pytest.raises(ValueError):
        github.validate({"repo": "https://evil.example/x"})


# ---------------------------------------------------------------- through the real sync engine

def create_github_source(ctx, **config):
    r = ctx.api.request("POST", "/sync/sources", token=ctx.admin, json={"name": "docs", "kind": "github", "config": {**CFG, "department_id": 1, "document_type": "POLICY", "sensitivity_level": 1, **config}})
    assert r.status_code == 201, r.text
    ctx.source_id = r.json()["id"]
    return r.json()


def readable_titles(ctx, name):
    return {p.rsplit("/", 1)[-1] for p in ctx.readable(name)}


def test_a_github_source_can_be_created_with_checked_settings_and_no_secrets(ctx, gh):
    api = ctx.api
    base = {"name": "x", "kind": "github", "config": {"department_id": 1, "document_type": "POLICY", "sensitivity_level": 1}}
    assert api.request("POST", "/sync/sources", token=ctx.admin, json={**base, "config": {**base["config"], "repo": "not a repo"}}).status_code == 422
    assert api.request("POST", "/sync/sources", token=ctx.admin, json={**base, "config": {**base["config"], "repo": "owner/docs", "token": TOKEN}}).status_code == 422
    assert api.request("POST", "/sync/sources", token=ctx.admin, json={**base, "config": {**base["config"], "repo": "owner/docs", "path": "demo-docs"}}).status_code == 201
    assert TOKEN not in json.dumps(api.request("GET", "/sync/sources", token=ctx.admin).json())


def test_the_first_run_imports_the_folder_and_gives_access_by_team_and_collaborator(ctx, gh):
    create_github_source(ctx)
    run = ctx.sync()
    assert run["status"] == "DONE" and {k: v for k, v in run["counts"].items() if v} == {"items": 3, "new": 3, "members_added": 4}
    ctx.settle()
    assert readable_titles(ctx, "alice") == {"leave-policy.md", "salary-bands.md", "payments_runbook.txt"}
    assert readable_titles(ctx, "bob") == {"leave-policy.md", "payments_runbook.txt"}
    assert readable_titles(ctx, "carol") == {"salary-bands.md"}
    assert ctx.pg.execute("select count(*) from documents where external_source = 'github:docs' and source_url like 'https://github.com/owner/docs/blob/main/%'").fetchone()[0] == 3
    assert sorted(r[0] for r in ctx.pg.execute("select name from groups").fetchall()) == ["github:docs:hr", "github:docs:staff"]


def test_removing_a_collaborator_on_github_removes_access_at_the_next_sync(ctx, gh):
    create_github_source(ctx)
    ctx.sync()
    ctx.settle()
    gh.collaborators = ["alice-gh", "bob-gh"]  # carol was removed on GitHub; no file changed
    run = ctx.sync()
    assert run["counts"].get("members_removed") == 1 and run["counts"].get("unchanged") == 3
    assert readable_titles(ctx, "carol") == set() and readable_titles(ctx, "alice") == {"leave-policy.md", "salary-bands.md", "payments_runbook.txt"}


def test_changing_the_access_file_moves_a_document_without_re_indexing(ctx, gh):
    create_github_source(ctx)
    ctx.sync()
    ctx.settle()
    jobs = len(ctx.jobs)
    new_access = {**ACCESS, "access": {"": ["staff"], "hr/": ["hr", "staff"]}}
    gh.files["demo-docs/.securesearch/access.json"] = json.dumps(new_access).encode()
    run = ctx.sync()
    assert run["counts"].get("permission_only") == 1 and len(ctx.jobs) == jobs
    assert "salary-bands.md" in readable_titles(ctx, "bob")


def test_an_edited_file_is_a_new_version_and_a_removed_file_is_soft_deleted(ctx, gh):
    create_github_source(ctx)
    ctx.sync()
    ctx.settle()
    gh.files["demo-docs/leave-policy.md"] = POLICY + b"A new paragraph about carry over days.\n"
    del gh.files["demo-docs/runbooks/payments_runbook.txt"]
    run = ctx.sync()
    assert run["counts"].get("changed") == 1 and run["counts"].get("deleted") == 1 and run["status"] == "DONE"
    ctx.settle()
    assert readable_titles(ctx, "alice") == {"leave-policy.md", "salary-bands.md"}
    assert ctx.pg.execute("select count(*) from document_versions v join documents d on d.id = v.document_id where d.external_id = 'demo-docs/leave-policy.md'").fetchone()[0] == 2


def test_a_second_run_with_nothing_changed_skips_everything(ctx, gh):
    create_github_source(ctx)
    ctx.sync()
    ctx.settle()
    jobs = len(ctx.jobs)
    run = ctx.sync()
    assert {k: v for k, v in run["counts"].items() if v} == {"items": 3, "unchanged": 3} and len(ctx.jobs) == jobs


def test_without_permission_to_read_collaborators_the_run_stops_and_changes_nothing(ctx, gh):
    create_github_source(ctx)
    ctx.sync()
    ctx.settle()
    gh.fail_collaborators = 403
    run = ctx.sync()
    assert run["status"] == "FAILED" and run["error_code"] == "PERMISSIONS_UNAVAILABLE"
    assert readable_titles(ctx, "carol") == {"salary-bands.md"} and ctx.pg.execute("select count(*) from documents where deleted_at is not null").fetchone()[0] == 0


def test_a_source_can_skip_the_collaborator_check(ctx, gh):
    gh.fail_collaborators = 403
    gh.collaborators = []
    create_github_source(ctx, mirror_collaborators=False)
    run = ctx.sync()
    assert run["status"] == "DONE"
    ctx.settle()
    assert readable_titles(ctx, "bob") == {"leave-policy.md", "payments_runbook.txt"}


@pytest.mark.parametrize("setup, code", [
    (lambda g, m: m.setattr(settings, "github_token", ""), "TOKEN_MISSING"),
    (lambda g, m: setattr(g, "rate_limited", True), "RATE_LIMITED"),
    (lambda g, m: setattr(g, "fail_tree", 404), "NOT_FOUND"),
])
def test_github_problems_close_the_run_with_a_code_and_change_nothing(ctx, gh, monkeypatch, setup, code):
    create_github_source(ctx)
    setup(gh, monkeypatch)
    run = ctx.sync()
    assert run["status"] == "FAILED" and run["error_code"] == code and ctx.pg.execute("select count(*) from documents").fetchone()[0] == 0


def test_the_token_never_appears_in_a_run_a_log_or_an_audit_row(ctx, gh, caplog):
    create_github_source(ctx)
    caplog.set_level(logging.DEBUG)
    ok = ctx.sync()
    gh.fail_tree = 404
    bad = ctx.sync()
    everything = json.dumps([ok, bad, ctx.api.request("GET", "/sync/sources", token=ctx.admin).json()])
    audit = json.dumps([list(r) for r in ctx.pg.execute("select detail::text from access_events").fetchall()])
    assert TOKEN not in everything and TOKEN not in audit and TOKEN not in caplog.text
    assert "Salary bands for the made-up company" not in everything + audit + caplog.text  # nor any document text
