"""Test setup for the backend (run INSIDE the container: docker compose exec backend pytest -q).

What happens here, in plain words:
1. We create a throw-away database "<POSTGRES_DB>_test" so tests never touch dev data.
2. We run the real Alembic migrations on it (this also tests the migrations).
3. Before each test we empty the tables and Redis counters.
4. Tests call the real app through FastAPI's TestClient, with real Postgres, Redis and Mailpit.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
import pytest
import redis as redis_sync

BACKEND_DIR = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("DATABASE_URL", "")


def _with_db_name(url: str, name: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path="/" + name))


def _prepare_test_database() -> str:
    admin_url = _with_db_name(BASE_URL, "postgres")
    test_name = urlsplit(BASE_URL).path.lstrip("/") + "_test"
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{test_name}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{test_name}"')
    test_url = _with_db_name(BASE_URL, test_name)
    env = {**os.environ, "DATABASE_URL": test_url}
    out = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise RuntimeError("Alembic migration failed on the test database:\n" + out.stderr[-2000:])
    return test_url


# Must happen BEFORE the app is imported by any test module.
if BASE_URL and BASE_URL != "CHANGE_ME":
    TEST_DATABASE_URL = _prepare_test_database()
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    # Tests use their own storage bucket too, so they never touch uploaded dev files.
    os.environ["S3_BUCKET"] = os.environ.get("S3_BUCKET", "securesearch-documents") + "-test"
    os.environ["SEARCH_WARMUP"] = "false"  # tests load models only when a test needs them
else:  # pragma: no cover
    TEST_DATABASE_URL = ""

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.storage import get_storage  # noqa: E402

from tests.constants import TEST_PASSWORD  # noqa: E402
_TEST_HASH = hash_password(TEST_PASSWORD)  # hash once; Argon2 is deliberately slow


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def pg():
    conn = psycopg.connect(TEST_DATABASE_URL, autocommit=True)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def redis_client():
    r = redis_sync.Redis.from_url(settings.redis_url, decode_responses=True)
    yield r
    r.close()


def _mailpit(path: str, method: str = "GET"):
    url = f"http://{settings.smtp_host}:8025/api/v1/{path}"
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read()
    try:
        return json.loads(body)
    except ValueError:  # e.g. DELETE answers with plain "ok"
        return None


@pytest.fixture(autouse=True)
def clean_state(pg, redis_client):
    """Empty tables, reload reference data, clear rate-limit counters and Mailpit."""
    pg.execute(
        "TRUNCATE auth_tokens, user_roles, users, roles, departments, groups, answer_audit_logs, query_audit_logs, access_events RESTART IDENTITY CASCADE"
    )
    for name in ("Engineering", "Finance", "HR"):
        pg.execute("INSERT INTO departments (name) VALUES (%s)", (name,))
    for name in ("employee", "system_admin", "auditor", "security_admin"):
        pg.execute("INSERT INTO roles (name) VALUES (%s)", (name,))
    for key in redis_client.scan_iter("ss:*"):
        redis_client.delete(key)
    _mailpit("messages", "DELETE")
    storage = get_storage()  # empty the test bucket
    storage.ensure_bucket()
    for key in storage.list_keys("", limit=1000):
        storage.delete(key)
    yield


@pytest.fixture(scope="session")
def client(pg):
    from fastapi.testclient import TestClient
    from app.main import app

    # "with" keeps ONE event loop for the whole test session (and runs startup/shutdown).
    with TestClient(app) as c:
        yield c


@pytest.fixture
def make_user(pg):
    def _make(email: str, roles=("employee",), active=True, clearance=1, password_hash=None):
        row = pg.execute(
            "INSERT INTO users (email, full_name, password_hash, department_id, clearance_level,"
            " country, is_active) VALUES (%s, %s, %s, (SELECT id FROM departments WHERE name='Engineering'),"
            " %s, 'IN', %s) RETURNING id",
            (email, email.split("@")[0].title(), password_hash or _TEST_HASH, clearance, active),
        ).fetchone()
        user_id = row[0]
        for role in roles:
            pg.execute(
                "INSERT INTO user_roles (user_id, role_id) SELECT %s, id FROM roles WHERE name=%s",
                (user_id, role),
            )
        return str(user_id)

    return _make


class Api:
    """Tiny helper around the TestClient. It never keeps cookies between calls, so each
    'device' is just a refresh-token string we pass explicitly."""

    def __init__(self, client):
        self.c = client

    def request(self, method, url, refresh=None, token=None, **kw):
        headers = kw.pop("headers", {})
        if refresh:
            headers["Cookie"] = f"refresh_token={refresh}"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = self.c.request(method, f"/api/v1{url}", headers=headers, **kw)
        self.c.cookies.clear()
        return resp

    def login(self, email, password=TEST_PASSWORD, remember=False):
        return self.request("POST", "/auth/login",
                            json={"email": email, "password": password, "remember_me": remember})

    @staticmethod
    def refresh_cookie(resp) -> str:
        for h in resp.headers.get_list("set-cookie"):
            if h.startswith("refresh_token="):
                return h.split(";", 1)[0].split("=", 1)[1]
        raise AssertionError("no refresh_token cookie in response")

    def signed_in(self, email, **kw):
        resp = self.login(email, **kw)
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"], self.refresh_cookie(resp)

    def get_mail(self, to: str, timeout: float = 5.0) -> str:
        """Wait for an email to `to` in Mailpit and return its text body."""
        end = time.time() + timeout
        while time.time() < end:
            msgs = _mailpit("messages")["messages"]
            for m in msgs:
                if any(t["Address"] == to for t in m["To"]):
                    return _mailpit(f"message/{m['ID']}")["Text"]
            time.sleep(0.2)
        raise AssertionError(f"no email for {to} arrived in Mailpit")

    def upload(self, token, filename, data, content_type="application/octet-stream", **fields):
        """POST /documents/upload as multipart. Defaults are valid metadata; override with fields."""
        meta = {"department_id": "1", "document_type": "POLICY", "sensitivity_level": "1"}
        meta.update({k: str(v) for k, v in fields.items() if v is not None})
        return self.request("POST", "/documents/upload", token=token,
                            files={"file": (filename, data, content_type)}, data=meta)

    def clear_mail(self) -> None:
        _mailpit("messages", "DELETE")

    def mail_count(self) -> int:
        return len(_mailpit("messages")["messages"])


@pytest.fixture
def api(client):
    return Api(client)


@pytest.fixture
def enqueued(monkeypatch):
    """Replaces 'send the job to the worker' with a list, so tests decide when a job runs.
    (The real worker container uses the development database, not the test database.)"""
    from app.services import document_service

    jobs: list = []

    async def fake_enqueue(job_id):
        jobs.append(job_id)

    monkeypatch.setattr(document_service, "_enqueue", fake_enqueue)
    return jobs


@pytest.fixture
def admin(api, make_user):
    """A signed-in system_admin. Returns the access token."""
    make_user("admin@demo", roles=("employee", "system_admin"))
    token, _ = api.signed_in("admin@demo")
    return token
