"""Phase 9B: operations. Audit retention and its guarded purge, the status page and health checks, the service counters, the
cleanup of old passages, and the file archive used by backup and restore.

Proven here: only audit rows past the retention are purged, the table stays append-only for everything else (a flag alone cannot
delete a recent row, a delete without the flag fails), the purge is recorded with counts only; the status page tells the truth about
each part and never reveals a host, a version or an error; the counters count real traffic and never break a request; old passages
of old versions are removed but active passages and original files never are; and the archive round-trips and refuses damage."""
import io
import json
import tarfile
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError

from app.audit import retention
from app.core import metrics, status
from app.core.config import Settings, settings
from app.ingest import cleanup
from app.ingest.pipeline import run_ingestion
from app.scripts import maintenance, storage_archive
from app.storage import get_storage

V = [f"Version {i} of the leave policy. Employees receive {20 + i} days of paid leave every year.\n".encode() for i in range(1, 7)]


# ---------------------------------------------------------------- helpers

def add_query(pg, days_old, text_="a question"):
    return pg.execute(
        "insert into query_audit_logs (user_id, kind, query_text, allowed_doc_count, response_status, latency_ms, created_at) "
        "values (%s, 'CHAT', %s, 1, 'ANSWERED', 100, now() - make_interval(days => %s)) returning id", (uuid.uuid4(), text_, days_old)
    ).fetchone()[0]


def add_answer(pg, query_id, days_old):
    pg.execute(
        "insert into answer_audit_logs (query_audit_id, model, prompt_version, llm_calls, input_tokens, output_tokens, answer_chars, created_at) "
        "values (%s, 'm', 'p', 1, 1, 1, 1, now() - make_interval(days => %s))", (query_id, days_old)
    )


def add_event(pg, days_old, event="auth.login_ok"):
    pg.execute("insert into access_events (event, created_at) values (%s, now() - make_interval(days => %s))", (event, days_old))


def count(pg, table):
    return pg.execute(f"select count(*) from {table}").fetchone()[0]


@pytest.fixture
def history(pg):
    """Old and recent audit rows: an old answered question, a recent one, an in-between one, and events."""
    old, mid, new = add_query(pg, 400), add_query(pg, 200), add_query(pg, 5)
    for q, d in ((old, 400), (mid, 200), (new, 5)):
        add_answer(pg, q, d)
    add_event(pg, 500)
    add_event(pg, 100)
    return old, mid, new


# ---------------------------------------------------------------- audit retention

def test_a_purge_removes_only_rows_older_than_the_retention_and_keeps_answers_with_their_questions(pg, history):
    c = retention.run(365)
    assert (c.queries, c.answers, c.events) == (1, 1, 1)
    assert count(pg, "query_audit_logs") == 2 and count(pg, "answer_audit_logs") == 2
    assert pg.execute("select count(*) from query_audit_logs where created_at < now() - interval '365 days'").fetchone()[0] == 0
    assert pg.execute("select count(*) from access_events where event <> 'audit.purge'").fetchone()[0] == 1  # the 100-day-old event stays


def test_a_purge_is_recorded_with_counts_only(pg, history):
    retention.run(365)
    (detail,) = [r[0] for r in pg.execute("select detail from access_events where event = 'audit.purge'").fetchall()]
    assert detail == {"queries": 1, "answers": 1, "events": 1, "older_than_days": 365}
    assert "question" not in json.dumps(detail)


def test_a_dry_run_counts_and_changes_nothing(pg, history):
    before = (count(pg, "query_audit_logs"), count(pg, "answer_audit_logs"), count(pg, "access_events"))
    c = retention.run(365, dry_run=True)
    assert (c.queries, c.answers, c.events) == (1, 1, 1)
    assert (count(pg, "query_audit_logs"), count(pg, "answer_audit_logs"), count(pg, "access_events")) == before


def test_a_second_purge_does_nothing_and_leaves_no_second_event(pg, history):
    retention.run(365)
    assert retention.run(365).total == 0
    assert pg.execute("select count(*) from access_events where event = 'audit.purge'").fetchone()[0] == 1


def test_a_shorter_retention_removes_more(pg, history):
    assert retention.run(180).queries == 2 and count(pg, "query_audit_logs") == 1


def test_nothing_younger_than_30_days_can_ever_be_purged(pg, history):
    with pytest.raises(DBAPIError):
        retention.run(10)
    assert count(pg, "query_audit_logs") == 3
    with pytest.raises(psycopg.errors.Error):
        pg.execute("select * from audit_purge(29)")


def test_the_tables_are_still_append_only_for_everything_else(pg, history):
    old = pg.execute("select id from query_audit_logs order by created_at limit 1").fetchone()[0]
    with pytest.raises(psycopg.errors.Error):
        pg.execute("delete from query_audit_logs where id = %s", (old,))  # no purge flag
    with pytest.raises(psycopg.errors.Error):
        pg.execute("update query_audit_logs set query_text = 'changed' where id = %s", (old,))
    with pytest.raises(psycopg.errors.Error):
        pg.execute("update access_events set event = 'x'")
    assert count(pg, "query_audit_logs") == 3


def test_the_purge_flag_alone_cannot_delete_a_recent_row(pg, history):
    with pg.transaction():
        pg.execute("select set_config('app.audit_purge', 'on', true)")
        with pytest.raises(psycopg.errors.Error):
            pg.execute("delete from query_audit_logs where created_at > now() - interval '30 days'")
    assert count(pg, "query_audit_logs") == 3


def test_retention_zero_keeps_everything(pg, history, monkeypatch):
    monkeypatch.setattr(settings, "audit_retention_days", 0)
    assert retention.run().total == 0 and count(pg, "query_audit_logs") == 3


def test_the_settings_refuse_a_retention_under_30_days_and_zero_versions():
    assert Settings(audit_retention_days=0).audit_retention_days == 0 and Settings(audit_retention_days=30).audit_retention_days == 30
    assert Settings().audit_retention_days == 365 and Settings().keep_versions == 3
    for bad in (1, 29, -5):
        with pytest.raises(ValidationError):
            Settings(audit_retention_days=bad)
    with pytest.raises(ValidationError):
        Settings(keep_versions=0)


def test_the_command_line_counts_purges_and_guards_production(pg, history, capsys, monkeypatch):
    assert maintenance.main(["audit-purge", "--dry-run"]) == 0
    assert "Would remove (older than 365 days): 1 questions, 1 answers, 1 security events." in capsys.readouterr().out
    assert count(pg, "query_audit_logs") == 3
    monkeypatch.setattr(settings, "app_env", "production")
    assert maintenance.main(["audit-purge"]) == 3 and count(pg, "query_audit_logs") == 3
    assert maintenance.main(["audit-purge", "--yes"]) == 0 and count(pg, "query_audit_logs") == 2


def test_the_overview_shows_how_many_records_are_past_retention_and_the_service_numbers(api, admin, pg, history):
    body = api.request("GET", "/dashboards/admin-overview", token=admin).json()
    assert body["audit_retention"] == {"days": 365, "records_due": 3}
    assert set(body["service_24h"]) == {"requests", "errors_5xx", "rate_limited"} and body["service_24h"]["requests"] >= 1
    assert "question" not in json.dumps(body["audit_retention"])


# ---------------------------------------------------------------- status page

def beat(redis_client):
    redis_client.set(status.HEARTBEAT_KEY, 1, ex=60)


def test_the_status_page_is_public_plain_and_not_cached(client, redis_client):
    beat(redis_client)
    r = client.get("/api/v1/status")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert set(body) == {"status", "components", "checked_at"} and body["status"] == "operational"
    assert [c["name"] for c in body["components"]] == ["Database", "Redis", "File storage", "Background worker"]
    assert all(set(c) == {"name", "status"} and c["status"] == "up" for c in body["components"])


def test_without_a_worker_heartbeat_the_service_is_degraded_not_down(client):
    body = client.get("/api/v1/status").json()
    assert body["status"] == "degraded" and {c["name"]: c["status"] for c in body["components"]}["Background worker"] == "down"


@pytest.mark.parametrize("name, patch", [("Database", "async_session"), ("Redis", "get_redis"), ("File storage", "get_storage")])
def test_a_failing_critical_part_means_down_and_the_reason_is_never_shown(client, redis_client, monkeypatch, name, patch):
    beat(redis_client)

    def boom(*a, **k):
        raise RuntimeError("secret detail postgresql://user:pw@host/db")

    monkeypatch.setattr(status, patch, boom)
    r = client.get("/api/v1/status")
    body = r.json()
    assert r.status_code == 200 and body["status"] == "down" and {c["name"]: c["status"] for c in body["components"]}[name] == "down"
    assert "secret detail" not in r.text and "postgresql" not in r.text


def test_the_status_page_shows_no_address_version_or_setting(client, redis_client):
    beat(redis_client)
    text = client.get("/api/v1/status").text
    for private in (settings.database_url, settings.redis_url, settings.s3_endpoint_url, settings.postgres_password, "postgres:5432", "redis:6379"):
        assert private and private not in text


def test_the_status_page_is_rate_limited_per_address(client):
    codes = [client.get("/api/v1/status").status_code for _ in range(62)]
    assert codes[:60] == [200] * 60 and 429 in codes[60:]


def test_the_worker_heartbeat_expires_by_itself(redis_client):
    status.record_heartbeat()
    assert 0 < redis_client.ttl(status.HEARTBEAT_KEY) <= status.HEARTBEAT_TTL


def test_health_and_ready_are_unchanged(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    assert client.get("/api/v1/ready").status_code == 200


# ---------------------------------------------------------------- counters

def totals(redis_client):
    now = datetime.now(timezone.utc)
    h = redis_client.hgetall(metrics._bucket(now))
    return {f: int(h.get(f, 0)) for f in metrics.FIELDS}


def test_real_requests_are_counted_but_health_and_status_are_not(client, redis_client):
    client.get("/api/v1/documents")  # 401
    client.get("/api/v1/no-such-route")  # 404
    client.get("/api/v1/health")
    client.get("/api/v1/ready")
    client.get("/api/v1/status")
    assert totals(redis_client) == {"requests": 2, "errors_5xx": 0, "rate_limited": 0}


def test_server_errors_and_too_many_requests_are_counted_separately(client, redis_client):
    for code in (200, 500, 500, 429, 404):
        client.portal.call(metrics.record, code)
    assert totals(redis_client) == {"requests": 5, "errors_5xx": 2, "rate_limited": 1}
    assert client.portal.call(metrics.last_24_hours) == {"requests": 5, "errors_5xx": 2, "rate_limited": 1}


def test_the_last_24_hours_add_up_hour_by_hour_and_ignore_older_hours(client, redis_client):
    now = datetime.now(timezone.utc)
    for hours_ago, n in ((0, 3), (5, 4), (23, 5), (30, 100)):
        redis_client.hset(metrics._bucket(now.replace(microsecond=0) - timedelta(hours=hours_ago)), "requests", n)
    assert client.portal.call(metrics.last_24_hours)["requests"] == 12


def test_counting_never_breaks_a_request_when_redis_is_down(client, monkeypatch):
    def boom():
        raise ConnectionError("redis down")

    monkeypatch.setattr(metrics, "get_redis", boom)
    assert client.get("/api/v1/documents").status_code == 401  # still answered normally
    assert client.portal.call(metrics.last_24_hours) == {"requests": 0, "errors_5xx": 0, "rate_limited": 0}


def test_counters_hold_numbers_only(client, redis_client):
    client.get("/api/v1/documents?email=someone@example.com")
    dumped = json.dumps([redis_client.hgetall(k) for k in redis_client.scan_iter(f"{metrics.PREFIX}*")])
    assert "someone" not in dumped and "/documents" not in dumped


# ---------------------------------------------------------------- cleanup of old passages

def upload(api, admin, data, name="leave.txt"):
    r = api.upload(admin, name, data)
    assert r.status_code == 202, r.text
    d = r.json()
    return d["id"], uuid.UUID(d["latest_job"]["id"])


def add_version(api, admin, doc_id, data):
    r = api.request("POST", f"/documents/{doc_id}/versions", token=admin, files={"file": ("leave.txt", data, "text/plain")})
    assert r.status_code == 202, r.text
    return uuid.UUID(r.json()["document"]["latest_job"]["id"])


def passages(pg, doc_id):
    rows = pg.execute(
        "select v.version_no, c.is_active, count(*) from document_chunks c join document_versions v on v.id = c.document_version_id where c.document_id = %s group by 1, 2 order by 1",
        (doc_id,),
    ).fetchall()
    return {(v, a): n for v, a, n in rows}


@pytest.fixture
def five_versions(api, admin, enqueued, pg):
    doc, job = upload(api, admin, V[0])
    run_ingestion(job)
    for data in V[1:5]:
        run_ingestion(add_version(api, admin, doc, data))
    return doc


def test_old_passages_of_old_versions_are_removed_and_the_newest_ones_kept(five_versions, pg):
    assert sorted(passages(pg, five_versions)) == [(1, False), (2, False), (3, False), (4, False), (5, True)]
    assert cleanup.run(3) == 2  # versions 1 and 2 had one passage each
    assert sorted(passages(pg, five_versions)) == [(3, False), (4, False), (5, True)]
    assert cleanup.run(3) == 0  # nothing left to do
    assert cleanup.run(1) == 2 and sorted(passages(pg, five_versions)) == [(5, True)]


def test_active_passages_and_original_files_are_never_removed(api, admin, enqueued, pg):
    doc, job = upload(api, admin, V[0])
    run_ingestion(job)
    for n in range(2, 6):  # four newer versions exist but were never indexed, so searches still use version 1
        pg.execute(
            "insert into document_versions (document_id, version_no, content_hash, storage_path, size_bytes, content_type) values (%s, %s, %s, %s, 1, 'text/plain')",
            (doc, n, f"hash{n}", f"documents/{doc}/v{n}/x"),
        )
    keys = get_storage().list_keys("documents/")
    assert cleanup.run(1) == 0
    assert passages(pg, doc) == {(1, True): 1}  # version 1 is the one searches use: untouched
    assert get_storage().list_keys("documents/") == keys


def test_deleted_documents_and_other_documents_are_left_alone(api, admin, enqueued, pg, five_versions):
    other, job = upload(api, admin, V[5], "other.txt")
    run_ingestion(job)
    api.request("DELETE", f"/documents/{five_versions}", token=admin)
    assert cleanup.run(1) == 0  # the deleted document keeps its old passages
    assert passages(pg, other) == {(1, True): 1}


def test_cleanup_needs_at_least_one_version_and_the_default_is_three(five_versions, pg):
    with pytest.raises(ValueError):
        cleanup.run(0)
    assert cleanup.run() == 2  # KEEP_VERSIONS defaults to 3


def test_the_command_line_reports_the_cleanup(five_versions, capsys):
    assert maintenance.main(["cleanup"]) == 0 and "Removed 2 old passage(s); the newest 3 version(s)" in capsys.readouterr().out


# ---------------------------------------------------------------- the file archive (backup and restore)

def archive_of(api, admin, enqueued):
    upload(api, admin, V[0], "a.txt")
    upload(api, admin, V[1], "b.txt")
    buf = io.BytesIO()
    assert storage_archive.export_files(buf) == 2
    return buf.getvalue()


def test_the_archive_round_trips_every_original_file(api, admin, enqueued):
    data = archive_of(api, admin, enqueued)
    storage = get_storage()
    keys = sorted(storage.list_keys("documents/"))
    originals = {k: storage.get_bytes(k) for k in keys}
    for k in keys:
        storage.delete(k)
    assert storage.list_keys("documents/") == []
    assert storage_archive.import_files(io.BytesIO(data)) == 2
    assert {k: storage.get_bytes(k) for k in storage.list_keys("documents/")} == originals


def test_a_damaged_archive_is_refused(api, admin, enqueued):
    data = archive_of(api, admin, enqueued)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        members = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    name = next(n for n in members if n != storage_archive.MANIFEST)

    def rebuild(files):
        out = io.BytesIO()
        with tarfile.open(fileobj=out, mode="w") as tar:
            for n, b in files.items():
                info = tarfile.TarInfo(n)
                info.size = len(b)
                tar.addfile(info, io.BytesIO(b))
        return io.BytesIO(out.getvalue())

    with pytest.raises(ValueError, match="do not match"):
        storage_archive.import_files(rebuild({**members, name: members[name] + b"x"}))  # a changed file
    with pytest.raises(ValueError, match="do not match"):
        storage_archive.import_files(rebuild({k: v for k, v in members.items() if k != name}))  # a missing file
    with pytest.raises(ValueError, match="no manifest"):
        storage_archive.import_files(rebuild({k: v for k, v in members.items() if k != storage_archive.MANIFEST}))  # cut short
    with pytest.raises(ValueError, match="unexpected path"):
        storage_archive.import_files(rebuild({"../evil": b"x", storage_archive.MANIFEST: b"{}"}))


def test_listing_more_keys_than_one_page_returns_them_all(monkeypatch):
    from app.storage import s3

    storage = get_storage()
    for i in range(8):
        storage.put_bytes(f"documents/page-test/{i}", b"x", "text/plain")
    monkeypatch.setattr(s3, "PAGE_SIZE", 3)
    assert len(storage.list_keys("documents/page-test/")) == 8
    assert len(storage.list_keys("documents/page-test/", limit=5)) == 5
    assert storage.list_keys("documents/none/") == []


def test_the_archive_command_line_reports_usage_and_failure(capsys):
    assert storage_archive.main([]) == 2 and storage_archive.main(["bogus"]) == 2
    assert "Usage" in capsys.readouterr().err
