"""The GitHub connector (Phase 8C): documents come from a folder of a repository, and who may read them comes from
a small access file in that folder plus, optionally, the repository's real list of collaborators.

Settings of a source (saved, never secret): {"repo": "owner/name", "branch": "main", "path": "demo-docs",
"mirror_collaborators": true}. The token is read from the environment (GITHUB_TOKEN) of the WORKER only. It is
sent only to the GitHub address from the environment (api.github.com), never to an address from saved settings.

Files in the folder: .md, .txt, .pdf and .docx (the usual upload rules apply). Anything in a hidden folder (a name
that starts with a dot) is ignored, so `.securesearch/` is never imported as a document.

`<path>/.securesearch/access.json` says who may read what:
    {"teams": {"hr": ["priya-gh", "aisha-gh"], "eng": ["rahul-gh"]},
     "access": {"": ["eng"], "hr/": ["hr"], "hr/public/": ["hr", "eng"]}}
A file belongs to the teams of the LONGEST matching folder prefix ("" is the whole folder); with no match nobody may
read it. `<path>/.securesearch/users.json` maps a GitHub login to the e-mail address of the person in this app:
    {"priya-gh": "priya@company.example"}
A login that is not in that file is ignored. With "mirror_collaborators" (the default) a person must ALSO be a collaborator
of the repository: removing someone on GitHub removes their access here at the next sync."""
import base64
import json
import logging
import re
import time
from typing import Any

import httpx

from app.core.config import settings
from app.sync.base import ConnectorSpec, SourceError, SourceItem, register

logger = logging.getLogger(__name__)

EXTENSIONS = (".md", ".txt", ".pdf", ".docx")
MAX_FILE_BYTES = 50 * 1024 * 1024  # the same limit as an upload
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,100}$")
ACCESS_FILE = ".securesearch/access.json"
USERS_FILE = ".securesearch/users.json"
TIMEOUT = 20.0
MAX_PAGES = 10  # 1000 collaborators

_transport: httpx.BaseTransport | None = None  # tests replace this; it is None in real use


def set_transport(transport: httpx.BaseTransport | None) -> None:
    global _transport
    _transport = transport


def validate(config: dict[str, Any]) -> None:
    repo, branch, path = config.get("repo"), config.get("branch", "main"), config.get("path", "")
    if not isinstance(repo, str) or not REPO_RE.match(repo):
        raise ValueError("Repository must look like owner/name.")
    if not isinstance(branch, str) or not BRANCH_RE.match(branch) or ".." in branch:
        raise ValueError("Branch name is not valid.")
    if not isinstance(path, str) or path.startswith("/") or ".." in path.split("/") or len(path) > 200:
        raise ValueError("Folder must be a relative path such as demo-docs.")
    if "mirror_collaborators" in config and not isinstance(config["mirror_collaborators"], bool):
        raise ValueError("mirror_collaborators must be true or false.")


def normalise_prefix(prefix: str) -> str:
    p = prefix.strip().strip("/")
    return f"{p}/" if p else ""


def teams_for_path(relative_path: str, access: dict[str, list[str]]) -> frozenset[str]:
    """The teams of the longest folder prefix that matches; nobody if none does."""
    best, teams = -1, frozenset[str]()
    for prefix, names in access.items():
        p = normalise_prefix(prefix)
        if relative_path.startswith(p) and len(p) > best:
            best, teams = len(p), frozenset(str(n) for n in names)
    return teams


class GitHubConnector:
    def __init__(self, config: dict[str, Any], token: str | None = None, api_url: str | None = None) -> None:
        self.repo = config["repo"]
        self.branch = config.get("branch", "main")
        self.path = normalise_prefix(config.get("path", ""))
        self.mirror = config.get("mirror_collaborators", True)
        self.token = token if token is not None else settings.github_token
        self.api = (api_url or settings.github_api_url).rstrip("/")
        self.shas: dict[str, str] = {}  # file path -> git blob id, filled by list_items
        self._users: dict[str, str] = {}  # GitHub login (lower case) -> e-mail address in this app
        self._teams: dict[str, list[str]] = {}  # team -> GitHub logins (lower case)

    # ---- talking to GitHub
    def _client(self) -> httpx.Client:
        if not self.token:
            raise SourceError("TOKEN_MISSING")
        return httpx.Client(
            base_url=self.api, timeout=TIMEOUT, transport=_transport,
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
        )

    def _get(self, client: httpx.Client, url: str, params: dict[str, str] | None = None, *, permissions: bool = False) -> Any:
        """One GET with one retry on a server error. Error messages never contain the token or any response text."""
        resp = None
        for attempt in range(2):
            try:
                resp = client.get(url, params=params)
            except httpx.HTTPError as exc:
                if attempt == 0:
                    time.sleep(0.2)
                    continue
                raise SourceError("SOURCE_UNREACHABLE") from exc
            if resp.status_code >= 500 and attempt == 0:
                time.sleep(0.2)
                continue
            break
        assert resp is not None
        code = resp.status_code
        if code == 200:
            return resp.json()
        if code == 401:
            raise SourceError("BAD_CREDENTIALS")
        if code == 429 or (code == 403 and resp.headers.get("x-ratelimit-remaining") == "0"):
            raise SourceError("RATE_LIMITED")
        if code in (403, 404):
            raise SourceError("PERMISSIONS_UNAVAILABLE" if permissions else "NOT_FOUND")
        raise SourceError("SOURCE_UNREACHABLE")

    def _blob(self, client: httpx.Client, sha: str) -> bytes:
        data = self._get(client, f"/repos/{self.repo}/git/blobs/{sha}")
        if data.get("encoding") != "base64":
            raise SourceError("SOURCE_UNREACHABLE")
        return base64.b64decode(data.get("content", ""))

    def _json_file(self, client: httpx.Client, tree: dict[str, str], name: str) -> dict[str, Any]:
        sha = tree.get(self.path + name)
        if sha is None:
            return {}
        try:
            data = json.loads(self._blob(client, sha).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise SourceError("BAD_ACCESS_FILE") from None
        if not isinstance(data, dict):
            raise SourceError("BAD_ACCESS_FILE")
        return data

    # ---- the connector interface
    def _tree(self, client: httpx.Client) -> dict[str, dict[str, Any]]:
        data = self._get(client, f"/repos/{self.repo}/git/trees/{self.branch}", {"recursive": "1"})
        if data.get("truncated"):
            raise SourceError("TREE_TOO_LARGE")
        return {e["path"]: e for e in data.get("tree", []) if e.get("type") == "blob"}

    def list_items(self) -> list[SourceItem]:
        with self._client() as client:
            blobs = self._tree(client)
            access = self._access(client, blobs)
            items: list[SourceItem] = []
            self.shas.clear()
            for path, entry in sorted(blobs.items()):
                if not path.startswith(self.path):
                    continue
                rel = path[len(self.path):]
                if any(part.startswith(".") for part in rel.split("/")):
                    continue  # hidden folders and files (the access files) are not documents
                if not rel.lower().endswith(EXTENSIONS) or int(entry.get("size") or 0) > MAX_FILE_BYTES:
                    continue
                self.shas[path] = entry["sha"]
                name = rel.rsplit("/", 1)[-1]
                stem = name.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").strip()
                title = (stem[:1].upper() + stem[1:]) or name
                items.append(SourceItem(
                    external_id=path, title=title, filename=name, groups=teams_for_path(rel, access.get("access", {})),
                    url=f"https://github.com/{self.repo}/blob/{self.branch}/{path}",
                ))
            return items

    def _access(self, client: httpx.Client, blobs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        shas = {p: e["sha"] for p, e in blobs.items()}
        access = self._json_file(client, shas, ACCESS_FILE)
        self._users = {str(k).lower(): str(v) for k, v in self._json_file(client, shas, USERS_FILE).items()}
        self._teams = {str(k): [str(x).lower() for x in v] for k, v in access.get("teams", {}).items() if isinstance(v, list)}
        acc = access.get("access", {})
        if not isinstance(acc, dict) or any(not isinstance(v, list) for v in acc.values()):
            raise SourceError("BAD_ACCESS_FILE")
        return {"access": acc}

    def read(self, item: SourceItem) -> bytes:
        with self._client() as client:
            return self._blob(client, self.shas[item.external_id])

    def members(self) -> dict[str, set[str]]:
        collaborators: set[str] | None = None
        if self.mirror:
            collaborators = set()
            with self._client() as client:
                for page in range(1, MAX_PAGES + 1):
                    rows = self._get(client, f"/repos/{self.repo}/collaborators", {"per_page": "100", "page": str(page)}, permissions=True)
                    collaborators |= {str(r["login"]).lower() for r in rows if r.get("permissions", {}).get("pull", True)}
                    if len(rows) < 100:
                        break
        out: dict[str, set[str]] = {}
        for team, logins in self._teams.items():
            allowed = [lg for lg in logins if collaborators is None or lg in collaborators]
            out[team] = {self._users[lg] for lg in allowed if lg in self._users}
        return out


def _build(config: dict[str, Any]) -> GitHubConnector:
    return GitHubConnector(config)


register("GITHUB", ConnectorSpec(build=_build, validate=validate))
