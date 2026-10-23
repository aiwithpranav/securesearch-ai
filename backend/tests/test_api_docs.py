"""Phase 9C: the API reference is generated from the application. Proven here: every route is listed, public routes are marked
public, administrator routes say so, and nothing is listed that does not exist. (CI also fails when docs/api.md is out of date.)"""
import re

from app.scripts import gen_api_docs


def rows():
    out = {}
    for line in gen_api_docs.render().splitlines():
        m = re.match(r"\| ([A-Z]+) \| `([^`]+)` \| ([^|]+) \| (.+) \|$", line)
        if m:
            out[(m.group(1), m.group(2))] = (m.group(3).strip(), m.group(4))
    return out


def test_every_route_of_the_application_is_listed_once(client):
    spec = client.get("/api/openapi.json").json()["paths"]
    wanted = {(m.upper(), p.removeprefix("/api/v1")) for p, ops in spec.items() if p.startswith("/api/v1") for m in ops if m in ("get", "post", "put", "patch", "delete")}
    assert set(rows()) == wanted and len(wanted) >= 60


def test_public_signed_in_and_administrator_routes_are_labelled_correctly():
    r = rows()
    assert r[("POST", "/auth/login")][0] == "anyone (public)" and r[("GET", "/status")][0] == "anyone (public)"
    assert r[("POST", "/search")][0] == "any signed-in person" and r[("GET", "/auth/me")][0] == "any signed-in person"
    assert r[("POST", "/documents/upload")][0] == "system administrator" and r[("GET", "/sync/sources")][0] == "system administrator"
    assert r[("GET", "/audit/queries")][0] == "security administrator or auditor"
    assert r[("GET", "/dashboards/knowledge-gaps")][0] == "system or security administrator"
    assert r[("GET", "/documents/{document_id}/acl")][0].startswith("MANAGE on that document")


def test_no_admin_route_is_ever_listed_as_public():
    for (method, path), (who, _) in rows().items():
        if who == "anyone (public)":
            assert path in {"/health", "/ready", "/status", "/auth/login", "/auth/logout", "/auth/refresh", "/auth/forgot-password", "/auth/reset-password"} or path.startswith("/auth/"), (method, path)


def test_the_page_says_it_is_generated_and_where_the_details_are():
    text = gen_api_docs.render()
    assert "Do not edit by hand" in text and "/api/docs" in text and text.endswith("\n")
