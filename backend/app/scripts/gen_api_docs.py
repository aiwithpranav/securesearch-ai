"""Writes docs/api.md from the running application, so the API documentation can never drift from the code.

    docker compose exec -T backend python -m app.scripts.gen_api_docs > docs/api.md

CI regenerates the page and fails if the committed copy differs (see .github/workflows/ci.yml). The page lists every route with
who may call it (read from the route's own dependencies) and a one-line description (the first sentence of the function's
docstring, or its name). For request and response shapes see the interactive documentation at /api/docs."""
import re
import sys
from collections import defaultdict

from fastapi.routing import APIRoute

from app.main import app

# dependency function name -> who may call. A route's list is the combination of everything it depends on.
WHO = {
    "require_admin": "system administrator",
    "require_auditor": "security administrator or auditor",
    "require_gap_viewer": "system or security administrator",
    "require_manage": "MANAGE on that document (system administrators always)",
    "get_current_user": "any signed-in person",
}
ORDER = ["system administrator", "system or security administrator", "security administrator or auditor", "MANAGE on that document (system administrators always)", "any signed-in person"]
TAG_TITLES = {
    "health": "Health and status", "auth": "Sign in and sessions", "admin": "People, roles and departments", "groups": "Groups", "documents": "Documents and ingestion",
    "access": "Groups and access rules", "notifications": "Notifications", "search": "Search", "chat": "Answers", "audit": "Audit trail",
    "evaluation": "Evaluation", "dashboards": "Dashboards", "sync": "Sync sources",
}


def _dependency_names(dependant) -> set[str]:  # type: ignore[no-untyped-def]
    names: set[str] = set()
    for dep in dependant.dependencies:
        if dep.call is not None:
            names.add(getattr(dep.call, "__name__", type(dep.call).__name__))
        names |= _dependency_names(dep)
    return names


class Entry:
    """One route with the path it is served under and every dependency that applies to it (its own, its router's, the include's)."""

    def __init__(self, route: APIRoute, prefix: str, extra: list) -> None:  # type: ignore[type-arg]
        self.route = route
        self.path = prefix + route.path
        names = _dependency_names(route.dependant)
        for dep in [*getattr(route, "dependencies", []), *extra]:
            call = getattr(dep, "dependency", None)
            if call is not None:
                names.add(getattr(call, "__name__", type(call).__name__))
        self.names = names


def who_may_call(entry: Entry) -> str:
    labels = [WHO[n] for n in entry.names if n in WHO]
    if not labels:
        return "anyone (public)"
    for label in ORDER:  # the strictest requirement first
        if label in labels:
            return label
    return ", ".join(sorted(labels))


# Plain descriptions for routes whose docstring or name does not say it well (keyed by method and path as served).
OVERRIDES = {
    ("GET", "/api/v1/health"): "Is the server up (for automatic checks).",
    ("GET", "/api/v1/ready"): "Are the database and Redis reachable (503 if not).",
    ("POST", "/api/v1/search"): "Find the passages that match a question, only from documents the caller may read.",
    ("POST", "/api/v1/chat"): "Ask a question: a short answer with validated sources, or one uniform refusal.",
    ("POST", "/api/v1/chat/feedback"): "Rate an answer with a thumbs up or down.",
    ("PATCH", "/api/v1/documents/{document_id}"): "Edit a document's title, department, type, sensitivity or countries.",
    ("GET", "/api/v1/auth/me"): "The signed-in person's profile.",
    ("POST", "/api/v1/auth/login"): "Sign in with email and password.",
    ("POST", "/api/v1/auth/refresh"): "Exchange the refresh cookie for a new access token (rotates the cookie).",
    ("POST", "/api/v1/auth/logout"): "Sign out this device.",
    ("POST", "/api/v1/auth/logout-all"): "Sign out every device.",
}


def describe(route: APIRoute, method: str = "", path: str = "") -> str:
    if (method, path) in OVERRIDES:
        return OVERRIDES[(method, path)]
    doc = (route.endpoint.__doc__ or "").strip()
    first = re.split(r"(?<=[.!?])\s|\n\n", doc, maxsplit=1)[0].replace("\n", " ").strip() if doc else ""
    return first or route.name.replace("_", " ").capitalize()


def tag_of(entry: Entry) -> str:
    path = entry.path
    for start, tag in (("/api/v1/audit", "audit"), ("/api/v1/evaluation", "evaluation"), ("/api/v1/sync", "sync"), ("/api/v1/dashboards", "dashboards")):
        if path.startswith(start):
            return tag
    if path.startswith(("/api/v1/health", "/api/v1/ready", "/api/v1/status")):
        return "health"
    return str(entry.route.tags[0]) if entry.route.tags else "other"


def entries() -> list[Entry]:
    found: list[Entry] = []
    for item in app.routes:
        if type(item).__name__ == "_IncludedRouter":  # FastAPI keeps included routers whole (a type its own typing does not expose)
            router = item.original_router  # type: ignore[attr-defined]
            # the router's own prefix is already part of each route's path
            prefix = item.include_context.prefix  # type: ignore[attr-defined]
            extra = [*router.dependencies, *item.include_context.dependencies]  # type: ignore[attr-defined]
            found += [Entry(r, prefix, extra) for r in router.routes if isinstance(r, APIRoute)]
        elif isinstance(item, APIRoute):
            found.append(Entry(item, "", []))
    return [e for e in found if e.path.startswith("/api/v1")]


def render() -> str:
    groups: dict[str, list[Entry]] = defaultdict(list)
    for e in entries():
        groups[tag_of(e)].append(e)
    out = [
        "# API reference",
        "",
        "> Generated from the application by `python -m app.scripts.gen_api_docs`. Do not edit by hand: CI fails when this page is out of date.",
        "",
        "Interactive documentation with every request and response shape: `/api/docs` (Swagger UI) on a running server, and `/api/openapi.json`.",
        "",
        "## Conventions",
        "- **Base path** `/api/v1`. The API only ever grows by adding routes (the contract is frozen).",
        "- **Sign in** with `POST /api/v1/auth/login`; send the returned access token as `Authorization: Bearer <token>`. It lives 15 minutes; a rotating, httpOnly refresh cookie renews it (`POST /api/v1/auth/refresh`). Roles are always read from the database, never from the token.",
        "- **Errors** are Problem Details JSON: `type`, `title`, `status`, `detail` and a `request_id` (also sent as the `X-Request-ID` header). Error text never contains what you sent (passwords, tokens, emails). A refusal for something you may not see looks exactly like \"not found\".",
        "- **Rate limits** answer `429` with a `Retry-After` header and `retry_after_seconds`.",
        "- **Nothing returns document text except** `POST /search`, `POST /chat` (and its stream) and `GET /chunks/{id}/preview`, and only for documents the caller may read. Administrators manage documents but never receive their content.",
        "",
    ]
    for tag in [t for t in TAG_TITLES if t in groups] + sorted(set(groups) - set(TAG_TITLES)):
        out += [f"## {TAG_TITLES.get(tag, tag.capitalize())}", "", "| Method | Path | Who may call | What it does |", "|---|---|---|---|"]
        for e in sorted(groups[tag], key=lambda x: (x.path, sorted(x.route.methods or [])[0])):
            for method in sorted(m for m in (e.route.methods or set()) if m not in ("HEAD", "OPTIONS")):
                out.append(f"| {method} | `{e.path.removeprefix('/api/v1')}` | {who_may_call(e)} | {describe(e.route, method, e.path).replace('|', '/')} |")
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


if __name__ == "__main__":
    sys.stdout.write(render())
