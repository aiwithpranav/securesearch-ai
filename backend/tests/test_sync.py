"""Phase 8B: the sync engine and its API, with a fake source (a plain in-memory list).

Proven here: new items are uploaded and given the source's teams as readers; unchanged items are skipped (nothing read again,
nothing queued); a changed file becomes a new version; a permission-only change updates the rules without re-indexing; a person
removed from a team loses access at the next query; items that leave the source are soft deleted and restored if they return;
rules an administrator added by hand are never touched; a broken or empty source cannot wipe the index; one bad item does not
stop the run; one run per source; the scheduler starts only sources that are due; settings hold no secrets; and a run never
carries document text."""
import asyncio
import json
import uuid
from datetime import timedelta

import pytest

from app.access.resolver import readable_ids_stmt
from app.db.sync import SyncSession
from app.ingest.pipeline import run_ingestion
from app.sync import engine
from app.sync.base import REGISTRY, ConnectorSpec, SourceItem, find_secret_key, permission_hash
from tests.access_world import World

A = b"Alpha policy text about parental leave and public holidays.\n"
B = b"Beta runbook text about deployment steps and rollbacks.\n"
C = b"Gamma finance text about budgets and quarterly forecasts.\n"
CONFIG = {"department_id": 1, "document_type": "POLICY", "sensitivity_level": 1}


class State:
    """What the fake source currently holds."""

    def __init__(self):
        self.items: dict[str, tuple[bytes, frozenset[str], str]] = {}
        self.members: dict[str, set[str]] = {}
        self.fail = False
        self.extra: list[SourceItem] = []
        self.reads = 0

    def put(self, ext_id, data, groups=(), filename=None):
        self.items[ext_id] = (data, frozenset(groups), filename or f"{ext_id}.txt")


class FakeConnector:
    def __init__(self, state):
        self.s = state

    def list_items(self):
        if self.s.fail:
            raise ConnectionError("source down")
        return [SourceItem(k, k.title(), fn, g) for k, (_, g, fn) in self.s.items.items()] + self.s.extra

    def read(self, item):
        self.s.reads += 1
        return self.s.items[item.external_id][0]

    def members(self):
        return {k: set(v) for k, v in self.s.members.items()}


@pytest.fixture
def source_state():
    st = State()
    REGISTRY["FAKE"] = ConnectorSpec(build=lambda cfg: FakeConnector(st), validate=lambda cfg: None)
    yield st
    REGISTRY.pop("FAKE", None)


@pytest.fixture
def queued(monkeypatch):
    """Replaces 'send the run to the worker' with a list; tests run the engine themselves."""
    runs: list = []

    async def fake(run_id):
        runs.append(run_id)

    monkeypatch.setattr(engine, "enqueue_run", fake)
    return runs


@pytest.fixture
def ctx(api, admin, enqueued, queued, source_state, make_user, pg):
    class Ctx:
        pass

    c = Ctx()
    c.api, c.admin, c.jobs, c.st, c.pg = api, admin, enqueued, source_state, pg
    c.done_jobs = 0
    c.users = {n: make_user(f"{n}@demo") for n in ("alice", "bob", "carol")}
    c.source_id = None

    def create(name="repo", config=None, **extra):
        r = api.request("POST", "/sync/sources", token=admin, json={"name": name, "kind": "fake", "config": config or CONFIG, **extra})
        assert r.status_code == 201, r.text
        c.source_id = r.json()["id"]
        return r.json()

    def sync(source_id=None):
        sid = source_id or c.source_id
        r = api.request("POST", f"/sync/sources/{sid}/run", token=admin)
        assert r.status_code == 202, r.text
        run_id = uuid.UUID(r.json()["id"])
        asyncio.run(engine.execute_run(run_id))
        return api.request("GET", f"/sync/runs/{run_id}", token=admin).json()

    def settle():
        """Indexes every document that is waiting (the worker's job)."""
        while c.done_jobs < len(enqueued):
            run_ingestion(enqueued[c.done_jobs])
            c.done_jobs += 1

    def readable(name):
        with SyncSession() as s:
            ids = set(s.scalars(readable_ids_stmt(c.users[name])).all())
        return {pg.execute("select external_id from documents where id = %s", (i,)).fetchone()[0] for i in ids}

    c.create, c.sync, c.settle, c.readable = create, sync, settle, readable
    return c


def seed_three(ctx):
    st = ctx.st
    st.put("alpha", A, ["hr"])
    st.put("beta", B, ["eng"])
    st.put("gamma", C, ["hr", "eng"])
    st.members = {"hr": {"alice@demo"}, "eng": {"bob@demo", "ALICE@demo"}}
    ctx.create()


def versions(pg, ext):
    return pg.execute("select count(*) from document_versions v join documents d on d.id = v.document_id where d.external_id = %s", (ext,)).fetchone()[0]


# ---------------------------------------------------------------- small pure pieces

def test_the_permission_hash_ignores_order_and_changes_with_the_set():
    assert permission_hash({"a", "b"}) == permission_hash(frozenset({"b", "a"}))
    assert permission_hash({"a"}) != permission_hash({"a", "b"}) != permission_hash(set())


@pytest.mark.parametrize("cfg, found", [
    ({"repo": "x/y"}, None), ({"token": "abc"}, "token"), ({"nested": {"API_Key": "x"}}, "nested.API_Key"),
    ({"list": [{"password": "x"}]}, "list.0.password"), ({"github_token_name": "x"}, "github_token_name"),
])
def test_settings_that_look_like_secrets_are_found(cfg, found):
    assert find_secret_key(cfg) == found


# ---------------------------------------------------------------- the API

def test_every_sync_route_needs_sign_in_and_the_admin_role(api, make_user):
    make_user("aisha@demo", roles=("employee",))
    make_user("meera@demo", roles=("employee", "security_admin"))
    nil = "00000000-0000-0000-0000-000000000000"
    routes = [("GET", "/sync/sources"), ("POST", "/sync/sources"), ("PATCH", f"/sync/sources/{nil}"), ("POST", f"/sync/sources/{nil}/run"),
              ("GET", f"/sync/sources/{nil}/runs"), ("GET", f"/sync/runs/{nil}")]
    for method, path in routes:
        assert api.request(method, path, json={} if method in ("POST", "PATCH") else None).status_code == 401, (method, path)
    for email in ("aisha@demo", "meera@demo"):
        token = api.signed_in(email)[0]
        for method, path in routes:
            assert api.request(method, path, token=token, json={} if method in ("POST", "PATCH") else None).status_code == 403, (email, method, path)


SECRET_TOKEN = "tok-not-a-real-secret"
SECRET_PASSWORD = "pw-not-a-real-secret"


@pytest.mark.parametrize("body, status", [
    ({"name": "x", "kind": "nothing", "config": CONFIG}, 422),
    ({"name": "x", "kind": "fake", "config": {**CONFIG, "token": SECRET_TOKEN}}, 422),
    ({"name": "x", "kind": "fake", "config": {**CONFIG, "nested": {"password": SECRET_PASSWORD}}}, 422),
    ({"name": "x", "kind": "fake", "config": {"document_type": "POLICY"}}, 422),
    ({"name": "x", "kind": "fake", "config": {**CONFIG, "department_id": 999}}, 422),
    ({"name": "x", "kind": "fake", "config": {**CONFIG, "document_type": "MEME"}}, 422),
    ({"name": "x", "kind": "fake", "config": {**CONFIG, "sensitivity_level": 9}}, 422),
    ({"name": "bad:name", "kind": "fake", "config": CONFIG}, 422),
    ({"name": "x", "kind": "fake", "config": CONFIG, "interval_minutes": 0}, 422),
    ({"name": "x", "kind": "fake", "config": CONFIG, "interval_minutes": 5000}, 422),
])
def test_a_source_is_only_created_with_valid_settings_and_no_secrets(api, admin, source_state, pg, body, status):
    r = api.request("POST", "/sync/sources", token=admin, json=body)
    assert r.status_code == status
    assert pg.execute("select count(*) from sync_sources").fetchone()[0] == 0
    # The secrets are not hex-like text: an error body carries a random request id (a UUID), which can contain a short
    # hex word such as "abc" by chance and used to make this test fail about one run in a hundred.
    assert SECRET_TOKEN not in r.text and SECRET_PASSWORD not in r.text


def test_source_names_are_unique_and_a_source_can_be_switched_off_and_retimed(ctx):
    src = ctx.create("repo")
    assert src["kind"] == "FAKE" and src["enabled"] is True and src["interval_minutes"] == 15 and src["last_run"] is None
    assert ctx.api.request("POST", "/sync/sources", token=ctx.admin, json={"name": "repo", "kind": "fake", "config": CONFIG}).status_code == 409
    r = ctx.api.request("PATCH", f"/sync/sources/{src['id']}", token=ctx.admin, json={"enabled": False, "interval_minutes": 60})
    assert r.status_code == 200 and r.json()["enabled"] is False and r.json()["interval_minutes"] == 60
    assert ctx.api.request("PATCH", f"/sync/sources/{src['id']}", token=ctx.admin, json={"interval_minutes": 0}).status_code == 422
    assert ctx.api.request("PATCH", f"/sync/sources/{uuid.uuid4()}", token=ctx.admin, json={}).status_code == 404
    assert [s["name"] for s in ctx.api.request("GET", "/sync/sources", token=ctx.admin).json()] == ["repo"]


# ---------------------------------------------------------------- the first run

def test_the_first_run_uploads_items_creates_teams_and_gives_the_teams_read_access(ctx):
    seed_three(ctx)
    run = ctx.sync()
    assert run["status"] == "DONE" and run["trigger"] == "MANUAL" and run["error_code"] is None and run["errors"] == []
    assert {k: v for k, v in run["counts"].items() if v} == {"items": 3, "new": 3, "members_added": 3}
    assert sorted(r[0] for r in ctx.pg.execute("select name from groups").fetchall()) == ["fake:repo:eng", "fake:repo:hr"]
    ctx.settle()
    assert ctx.readable("alice") == {"alpha", "beta", "gamma"}  # alice is in both teams (the e-mail case does not matter)
    assert ctx.readable("bob") == {"beta", "gamma"}
    assert ctx.readable("carol") == set()  # in no team: deny by default
    row = ctx.pg.execute("select external_source, title, department_id, document_type, sensitivity_level from documents where external_id = 'alpha'").fetchone()
    assert row == ("fake:repo", "Alpha", 1, "POLICY", 1)
    ev = ctx.pg.execute("select detail from access_events where event = 'admin.sync_run_finished'").fetchone()[0]
    assert ev["source_id"] == ctx.source_id and ev["run_id"] == run["id"]


def test_a_run_never_carries_document_text(ctx):
    seed_three(ctx)
    run = ctx.sync()
    everything = json.dumps([run, ctx.api.request("GET", "/sync/sources", token=ctx.admin).json(), ctx.api.request("GET", f"/sync/sources/{ctx.source_id}/runs", token=ctx.admin).json()])
    assert "Alpha policy text" not in everything and "parental leave" not in everything


# ---------------------------------------------------------------- the second run: nothing to do

def test_a_second_run_with_nothing_changed_skips_everything(ctx):
    seed_three(ctx)
    ctx.sync()
    ctx.settle()
    jobs_before, versions_before = len(ctx.jobs), ctx.pg.execute("select count(*) from document_versions").fetchone()[0]
    run = ctx.sync()
    assert {k: v for k, v in run["counts"].items() if v} == {"items": 3, "unchanged": 3}
    assert len(ctx.jobs) == jobs_before and ctx.pg.execute("select count(*) from document_versions").fetchone()[0] == versions_before
    assert ctx.pg.execute("select count(*) from permission_change_events").fetchone()[0] == 3  # only the three from the first run


# ---------------------------------------------------------------- changes

def test_a_changed_file_becomes_a_new_version_and_the_others_are_untouched(ctx):
    seed_three(ctx)
    ctx.sync()
    ctx.settle()
    ctx.st.put("beta", B + b"A new paragraph about hotfixes.\n", ["eng"])
    run = ctx.sync()
    assert {k: v for k, v in run["counts"].items() if v} == {"items": 3, "changed": 1, "unchanged": 2}
    assert (versions(ctx.pg, "alpha"), versions(ctx.pg, "beta"), versions(ctx.pg, "gamma")) == (1, 2, 1)
    assert ctx.readable("bob") == {"beta", "gamma"}  # still readable while the new version is indexed
    ctx.settle()
    assert ctx.pg.execute("select count(*) from document_chunks c join documents d on d.id = c.document_id where d.external_id = 'beta' and c.is_active and c.content like '%hotfixes%'").fetchone()[0] == 1


def test_a_permission_only_change_updates_the_rules_without_re_indexing(ctx):
    seed_three(ctx)
    ctx.sync()
    ctx.settle()
    jobs_before, reads_before = len(ctx.jobs), ctx.st.reads
    ctx.st.put("beta", B, ["eng", "hr"])  # same file, one more team
    run = ctx.sync()
    assert {k: v for k, v in run["counts"].items() if v} == {"items": 3, "permission_only": 1, "unchanged": 2}
    assert len(ctx.jobs) == jobs_before  # no new indexing job: the text was not embedded again
    assert versions(ctx.pg, "beta") == 1
    assert ctx.readable("alice") == {"alpha", "beta", "gamma"} and ctx.readable("bob") == {"beta", "gamma"}
    assert ctx.pg.execute("select count(*) from permission_change_events").fetchone()[0] == 4
    ctx.st.put("beta", B, ["hr"])  # now only hr: bob loses beta, immediately
    ctx.sync()
    assert ctx.readable("bob") == {"gamma"} and ctx.readable("alice") == {"alpha", "beta", "gamma"}
    assert ctx.st.reads > reads_before


def test_a_change_of_file_and_readers_together_is_one_new_version_with_the_new_readers(ctx):
    seed_three(ctx)
    ctx.sync()
    ctx.settle()
    ctx.st.put("alpha", A + b"Extra.\n", ["eng"])
    run = ctx.sync()
    assert run["counts"].get("changed") == 1 and not run["counts"].get("permission_only")
    ctx.settle()
    assert ctx.readable("bob") == {"alpha", "beta", "gamma"}


def test_a_person_removed_from_a_team_loses_access_at_the_next_query(ctx):
    seed_three(ctx)
    ctx.sync()
    ctx.settle()
    assert ctx.readable("bob") == {"beta", "gamma"}
    ctx.st.members["eng"] = {"alice@demo"}  # bob leaves the team; no document changed at all
    run = ctx.sync()
    assert run["counts"].get("members_removed") == 1 and run["counts"].get("unchanged") == 3
    assert ctx.readable("bob") == set() and ctx.readable("alice") == {"alpha", "beta", "gamma"}
    ctx.st.members["eng"] = {"alice@demo", "carol@demo"}
    ctx.sync()
    assert ctx.readable("carol") == {"beta", "gamma"}


def test_a_team_that_disappears_from_the_source_ends_up_empty_and_its_rules_go(ctx):
    seed_three(ctx)
    ctx.sync()
    ctx.settle()
    del ctx.st.members["hr"]
    ctx.st.put("alpha", A, [])
    ctx.st.put("gamma", C, ["eng"])
    ctx.sync()
    assert ctx.pg.execute("select count(*) from user_groups ug join groups g on g.id = ug.group_id where g.name = 'fake:repo:hr'").fetchone()[0] == 0
    assert ctx.readable("alice") == {"beta", "gamma"}  # alpha now has no team: nobody may read it


def test_people_the_source_names_but_who_have_no_account_are_ignored_and_counted(ctx):
    ctx.st.put("alpha", A, ["hr"])
    ctx.st.members = {"hr": {"alice@demo", "ghost@elsewhere.example", "  "}}
    ctx.create()
    run = ctx.sync()
    assert run["counts"].get("members_added") == 1 and run["counts"].get("unknown_members") == 1
    assert ctx.pg.execute("select count(*) from users where email like 'ghost%'").fetchone()[0] == 0


# ---------------------------------------------------------------- items that leave and come back

def test_an_item_that_leaves_the_source_is_soft_deleted_and_restored_when_it_returns(ctx):
    seed_three(ctx)
    ctx.sync()
    ctx.settle()
    del ctx.st.items["gamma"]
    run = ctx.sync()
    assert run["counts"].get("deleted") == 1 and run["status"] == "DONE"
    assert ctx.readable("alice") == {"alpha", "beta"}
    assert ctx.pg.execute("select deleted_at is not null from documents where external_id = 'gamma'").fetchone()[0] is True
    ctx.st.put("gamma", C, ["hr", "eng"])
    run = ctx.sync()
    assert run["counts"].get("restored") == 1
    ctx.settle()
    assert ctx.readable("alice") == {"alpha", "beta", "gamma"}
    assert ctx.pg.execute("select count(*) from documents where external_id = 'gamma'").fetchone()[0] == 1  # the same document, not a new one


# ---------------------------------------------------------------- what the sync must never touch

def test_rules_an_administrator_added_by_hand_are_never_touched(ctx):
    seed_three(ctx)
    ctx.sync()
    ctx.settle()
    doc = ctx.pg.execute("select id from documents where external_id = 'beta'").fetchone()[0]
    w = World(ctx.pg)
    w.acl(doc, ("USER", ctx.users["carol"]))  # a hand-made ALLOW for carol
    w.acl(doc, ("USER", ctx.users["bob"]), effect="DENY")  # a hand-made DENY for bob
    w.acl(doc, ("GROUP", "manual-team"))  # a hand-made ALLOW for a team that is not the source's
    manual = ctx.pg.execute("select principal_type, principal_id, effect, permission from document_acl where document_id = %s and principal_type <> 'GROUP' or principal_id = %s order by 1, 2", (doc, str(w.group_id("manual-team")))).fetchall()
    ctx.st.put("beta", B, ["hr"])  # the source's teams change
    ctx.sync()
    after = ctx.pg.execute("select principal_type, principal_id, effect, permission from document_acl where document_id = %s and principal_type <> 'GROUP' or principal_id = %s order by 1, 2", (doc, str(w.group_id("manual-team")))).fetchall()
    assert after == manual
    assert ctx.readable("carol") >= {"beta"} and "beta" not in ctx.readable("bob")  # the DENY still wins


def test_a_team_made_by_hand_with_the_same_look_is_not_managed(ctx):
    seed_three(ctx)
    World(ctx.pg).group_id("fake:other:eng")  # a group of someone else's, not this source's
    uid = ctx.users["carol"]
    ctx.pg.execute("insert into user_groups (user_id, group_id) select %s, id from groups where name = 'fake:other:eng'", (uid,))
    ctx.sync()
    assert ctx.pg.execute("select count(*) from user_groups ug join groups g on g.id = ug.group_id where g.name = 'fake:other:eng'").fetchone()[0] == 1


def test_a_managed_team_cannot_be_edited_by_hand_but_other_teams_can(ctx):
    seed_three(ctx)
    ctx.sync()
    gid = ctx.pg.execute("select id from groups where name = 'fake:repo:hr'").fetchone()[0]
    r = ctx.api.request("POST", f"/groups/{gid}/members", token=ctx.admin, json={"user_id": str(ctx.users["carol"])})
    assert r.status_code == 409 and "managed by a sync source" in r.json()["detail"]
    assert ctx.api.request("DELETE", f"/groups/{gid}/members?user_id={ctx.users['alice']}", token=ctx.admin).status_code == 409
    mine = ctx.api.request("POST", "/groups", token=ctx.admin, json={"name": "fake:repository"}).json()["id"]  # looks similar, is not managed
    assert ctx.api.request("POST", f"/groups/{mine}/members", token=ctx.admin, json={"user_id": str(ctx.users["carol"])}).status_code == 200


# ---------------------------------------------------------------- a broken source cannot wipe the index

def test_an_unreachable_source_changes_nothing(ctx):
    seed_three(ctx)
    ctx.sync()
    ctx.settle()
    ctx.st.fail = True
    run = ctx.sync()
    assert run["status"] == "FAILED" and run["error_code"] == "SOURCE_UNREACHABLE"
    assert ctx.readable("alice") == {"alpha", "beta", "gamma"} and ctx.pg.execute("select count(*) from documents where deleted_at is not null").fetchone()[0] == 0


def test_an_empty_listing_stops_the_run_before_anything_changes(ctx):
    seed_three(ctx)
    ctx.sync()
    ctx.settle()
    ctx.st.items.clear()
    ctx.st.members = {}
    run = ctx.sync()
    assert run["status"] == "FAILED" and run["error_code"] == "EMPTY_LISTING"
    assert ctx.pg.execute("select count(*) from documents where deleted_at is not null").fetchone()[0] == 0
    assert ctx.pg.execute("select count(*) from user_groups").fetchone()[0] == 3  # members were not emptied either


def test_removing_most_of_the_documents_at_once_stops_the_run(ctx):
    for i in range(5):
        ctx.st.put(f"doc{i}", f"Document number {i} has its own distinct words.\n".encode(), ["hr"])
    ctx.st.members = {"hr": {"alice@demo"}}
    ctx.create()
    ctx.sync()
    ctx.settle()
    for i in range(3):
        del ctx.st.items[f"doc{i}"]  # 3 of 5 is more than half
    run = ctx.sync()
    assert run["status"] == "FAILED" and run["error_code"] == "TOO_MANY_DELETES"
    assert ctx.pg.execute("select count(*) from documents where deleted_at is not null").fetchone()[0] == 0
    del ctx.st.items["doc3"]  # now doc2 and doc3 are gone and doc0 and doc1 are back: 2 of 5 is within the limit
    ctx.st.put("doc0", b"Document number 0 has its own distinct words.\n", ["hr"])
    ctx.st.put("doc1", b"Document number 1 has its own distinct words.\n", ["hr"])
    run = ctx.sync()
    assert run["status"] == "DONE" and run["counts"].get("deleted") == 2


def test_the_guard_can_be_switched_off_for_a_source_that_really_empties(ctx):
    ctx.st.put("a", A, ["hr"])
    ctx.create(config={**CONFIG, "allow_mass_delete": True})
    ctx.sync()
    ctx.st.items.clear()
    run = ctx.sync()
    assert run["status"] == "DONE" and run["counts"].get("deleted") == 1


# ---------------------------------------------------------------- bad items

def test_one_bad_item_does_not_stop_the_run(ctx):
    ctx.st.put("alpha", A, ["hr"])
    ctx.st.put("virus", b"MZ....", ["hr"], filename="virus.exe")
    ctx.st.put("empty", b"", ["hr"], filename="empty.txt")
    ctx.st.put("beta", B, ["hr"])
    ctx.st.members = {"hr": {"alice@demo"}}
    ctx.create()
    run = ctx.sync()
    assert run["status"] == "PARTIAL" and run["counts"]["new"] == 2 and run["counts"]["failed"] == 2
    assert sorted((e["item"], e["code"]) for e in run["errors"]) == [("empty", "EMPTY"), ("virus", "UNSUPPORTED_TYPE")]
    ctx.settle()
    assert ctx.readable("alice") == {"alpha", "beta"}


def test_two_items_with_the_same_content_fail_one_of_them_with_a_clear_code(ctx):
    ctx.st.put("one", A, ["hr"])
    ctx.st.put("two", A, ["hr"])
    ctx.create()
    run = ctx.sync()
    assert run["status"] == "PARTIAL" and run["counts"]["new"] == 1 and [e["code"] for e in run["errors"]] == ["DUPLICATE_CONTENT"]


def test_a_listing_that_repeats_an_id_is_refused(ctx):
    ctx.st.put("one", A, ["hr"])
    ctx.st.extra = [SourceItem("one", "Again", "again.txt", frozenset())]
    ctx.create()
    run = ctx.sync()
    assert run["status"] == "FAILED" and run["error_code"] == "BAD_LISTING" and ctx.pg.execute("select count(*) from documents").fetchone()[0] == 0


def test_a_source_kind_that_no_longer_exists_fails_the_run(ctx):
    seed_three(ctx)
    REGISTRY.pop("FAKE")
    run = ctx.sync()
    assert run["status"] == "FAILED" and run["error_code"] == "UNKNOWN_KIND"


# ---------------------------------------------------------------- runs and the scheduler

def test_only_one_run_per_source_and_a_stale_one_is_replaced(ctx, queued):
    seed_three(ctx)
    first = ctx.api.request("POST", f"/sync/sources/{ctx.source_id}/run", token=ctx.admin)
    assert first.status_code == 202 and len(queued) == 1
    assert ctx.api.request("POST", f"/sync/sources/{ctx.source_id}/run", token=ctx.admin).status_code == 409
    ctx.pg.execute("update sync_runs set started_at = now() - interval '2 hours'")
    assert ctx.api.request("POST", f"/sync/sources/{ctx.source_id}/run", token=ctx.admin).status_code == 202
    statuses = sorted(r[0] for r in ctx.pg.execute("select status from sync_runs").fetchall())
    assert statuses == ["FAILED", "RUNNING"]
    assert ctx.pg.execute("select error_code from sync_runs where status = 'FAILED'").fetchone()[0] == "STALE"


def test_a_run_that_is_already_finished_is_not_run_again(ctx):
    seed_three(ctx)
    run = ctx.sync()
    jobs = len(ctx.jobs)
    asyncio.run(engine.execute_run(uuid.UUID(run["id"])))
    assert len(ctx.jobs) == jobs and ctx.pg.execute("select count(*) from documents").fetchone()[0] == 3


def test_when_the_queue_is_down_the_run_is_closed_and_the_answer_is_503(ctx, monkeypatch):
    seed_three(ctx)

    async def down(run_id):
        raise ConnectionError("queue down")

    monkeypatch.setattr(engine, "enqueue_run", down)
    r = ctx.api.request("POST", f"/sync/sources/{ctx.source_id}/run", token=ctx.admin)
    assert r.status_code == 503
    assert ctx.pg.execute("select status, error_code from sync_runs").fetchone() == ("FAILED", "QUEUE_UNAVAILABLE")


def test_the_scheduler_starts_only_sources_that_are_due(ctx, queued):
    ctx.create("never-run")
    off = ctx.create("switched-off")
    ctx.api.request("PATCH", f"/sync/sources/{off['id']}", token=ctx.admin, json={"enabled": False})
    recent = ctx.create("recent")
    ctx.pg.execute("update sync_sources set last_run_at = now() - interval '5 minutes' where id = %s", (recent["id"],))
    old = ctx.create("old")
    ctx.pg.execute("update sync_sources set last_run_at = now() - interval '20 minutes' where id = %s", (old["id"],))
    assert asyncio.run(engine.tick()) == 2  # never-run and old (15-minute interval)
    started = {r[0] for r in ctx.pg.execute("select s.name from sync_runs r join sync_sources s on s.id = r.source_id where r.trigger = 'SCHEDULE'").fetchall()}
    assert started == {"never-run", "old"}
    assert asyncio.run(engine.tick()) == 0  # both are running now


def test_a_finished_run_makes_its_source_not_due_until_the_interval_has_passed(ctx, queued):
    seed_three(ctx)
    ctx.sync()
    assert asyncio.run(engine.tick()) == 0
    ctx.pg.execute("update sync_sources set last_run_at = now() - interval '16 minutes'")
    assert asyncio.run(engine.tick()) == 1
    assert [r[0] for r in ctx.pg.execute("select trigger from sync_runs order by started_at").fetchall()] == ["MANUAL", "SCHEDULE"]
    assert ctx.pg.execute("select started_by from sync_runs where trigger = 'SCHEDULE'").fetchone()[0] is None


def test_runs_are_listed_newest_first_and_a_source_shows_its_last_run(ctx):
    seed_three(ctx)
    ctx.sync()
    ctx.st.put("delta", b"Delta text about something entirely different.\n", ["hr"])
    second = ctx.sync()
    runs = ctx.api.request("GET", f"/sync/sources/{ctx.source_id}/runs", token=ctx.admin).json()
    assert [r["id"] for r in runs][0] == second["id"] and len(runs) == 2
    assert ctx.api.request("GET", "/sync/sources", token=ctx.admin).json()[0]["last_run"]["id"] == second["id"]
    assert ctx.api.request("GET", f"/sync/runs/{uuid.uuid4()}", token=ctx.admin).status_code == 404
    assert ctx.api.request("GET", f"/sync/sources/{uuid.uuid4()}/runs", token=ctx.admin).status_code == 404


def test_the_run_does_not_widen_access_a_source_without_teams_gives_nobody_access(ctx):
    ctx.st.put("alpha", A, [])
    ctx.create()
    ctx.sync()
    ctx.settle()
    assert ctx.readable("alice") == set() and ctx.pg.execute("select count(*) from document_acl").fetchone()[0] == 0
