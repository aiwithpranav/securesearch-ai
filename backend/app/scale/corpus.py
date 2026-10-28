"""Turns real public Markdown documentation into documents for the scale demo.

Three sources are used (all public, all Markdown; they are downloaded by scripts/big/download.sh, never committed):
- kubernetes/  Kubernetes documentation (CC BY 4.0)
- docker/      Docker documentation (Apache 2.0)
- gitlab/      the GitLab handbook (CC BY-SA 4.0), which also covers HR, finance, legal and security topics

Every function here is pure (no database, no network) so it can be tested hard."""
import hashlib
import re
from dataclasses import dataclass

MIN_BODY_CHARS = 300  # tiny index or redirect pages carry no knowledge
MAX_TITLE = 200

# Department -> who may read. Roles are used where a department rule would also let the system administrator in
# (he sits in Engineering): "admin is not reader" stays true in the scale demo too.
DEPARTMENT_RULE: dict[str, tuple[str, str | None]] = {
    "Engineering": ("ROLE", "engineer"),
    "HR": ("ROLE", "hr_manager"),
    "Finance": ("ROLE", "finance_analyst"),
    "Sales": ("ROLE", "sales_executive"),
    "Security": ("ROLE", "security_admin"),
    "Legal": ("DEPARTMENT", "Legal"),
    "Customer Support": ("DEPARTMENT", "Customer Support"),
    "Company-wide": ("COMPANY", None),
}

# First folder below the handbook root -> (department, sensitivity)
HANDBOOK_FOLDERS: dict[str, tuple[str, int]] = {
    "engineering": ("Engineering", 1),
    "product": ("Engineering", 1),
    "business-technology": ("Engineering", 1),
    "people-group": ("HR", 2),
    "total-rewards": ("HR", 2),
    "hiring": ("HR", 2),
    "finance": ("Finance", 2),
    "legal": ("Legal", 2),
    "security": ("Security", 3),
    "sales": ("Sales", 1),
    "customer-success": ("Sales", 1),
    "support": ("Customer Support", 1),
    "marketing": ("Company-wide", 0),
    "company": ("Company-wide", 0),
}


@dataclass(frozen=True)
class Placement:
    department: str
    document_type: str
    sensitivity: int
    executive_read: bool  # executives may also read restricted documents


def classify(rel_path: str) -> Placement:
    """Where a file belongs, from its path (for example 'gitlab/people-group/onboarding/index.md')."""
    parts = [p for p in rel_path.replace("\\", "/").split("/") if p]
    source = parts[0] if parts else ""
    lower = "/".join(parts).lower()
    if source in ("kubernetes", "docker"):
        runbook = any(w in lower for w in ("/tasks/", "/tutorials/", "troubleshoot", "/guides/"))
        return Placement("Engineering", "RUNBOOK" if runbook else "OTHER", 1, False)
    if source == "gitlab":
        folder = parts[1] if len(parts) > 2 else ""
        department, sensitivity = HANDBOOK_FOLDERS.get(folder, ("Company-wide", 0))
        if "policy" in lower or "policies" in lower:
            doc_type = "POLICY"
        elif any(w in lower for w in ("runbook", "/howto", "/process")):
            doc_type = "RUNBOOK"
        else:
            doc_type = "OTHER"
        return Placement(department, doc_type, sensitivity, sensitivity >= 2)
    return Placement("Company-wide", "OTHER", 0, False)


def rules_for(placement: Placement) -> list[tuple[tuple[str, str | None], str, str]]:
    """Access rules for a placed document: the owning team, and executives for restricted documents."""
    rules: list[tuple[tuple[str, str | None], str, str]] = [(DEPARTMENT_RULE[placement.department], "ALLOW", "READ")]
    if placement.executive_read:
        rules.append((("ROLE", "executive"), "ALLOW", "READ"))
    return rules


_FRONT_YAML = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
_FRONT_TOML = re.compile(r"\A\+\+\+\s*\n(.*?)\n\+\+\+\s*(?:\n|\Z)", re.DOTALL)
_TITLE = re.compile(r"^title\s*[:=]\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
_SHORTCODE = re.compile(r"\{\{[<%].*?[>%]\}\}", re.DOTALL)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_BLANKS = re.compile(r"\n{3,}")


def clean_markdown(raw: str, fallback_title: str) -> tuple[str, str]:
    """(title, body). Removes the site-generator front matter, shortcodes such as {{< note >}} and HTML comments,
    which are build instructions and not knowledge. The page title comes from the front matter when it has one."""
    text = raw.replace("\r\n", "\n").lstrip("﻿")
    title = ""
    for pattern in (_FRONT_YAML, _FRONT_TOML):
        match = pattern.match(text)
        if match:
            found = _TITLE.search(match.group(1))
            if found:
                title = found.group(1).strip().strip("\"'")
            text = text[match.end():]
            break
    text = _HTML_COMMENT.sub("", _SHORTCODE.sub("", text))
    body = _BLANKS.sub("\n\n", text).strip()
    return (title or fallback_title)[:MAX_TITLE], body


def fallback_title(rel_path: str) -> str:
    """A readable title from the file name when the page has none ('index.md' uses its folder)."""
    parts = [p for p in rel_path.replace("\\", "/").split("/") if p]
    stem = parts[-1].rsplit(".", 1)[0]
    if stem in ("index", "_index", "readme") and len(parts) > 1:
        stem = parts[-2]
    return stem.replace("-", " ").replace("_", " ").strip().title() or "Untitled"


def unique_filename(rel_path: str) -> str:
    """A file name that is unique across the whole corpus: the readable stem plus a short hash of the full path."""
    digest = hashlib.sha1(rel_path.encode()).hexdigest()[:8]
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", fallback_title(rel_path)).strip("-")[:90] or "doc"
    return f"{stem}-{digest}.md"


CANARY_PREFIX = "CANARY-BIG-"


def canary_for(rel_path: str) -> str:
    return CANARY_PREFIX + hashlib.sha1(("canary:" + rel_path).encode()).hexdigest()[:8].upper()


def wants_canary(rel_path: str, sensitivity: int, every: int = 20) -> bool:
    """Every restricted document (sensitivity 2 or more) carries a canary; of the rest, one in `every` does."""
    if sensitivity >= 2:
        return True
    return int(hashlib.sha1(("pick:" + rel_path).encode()).hexdigest()[:6], 16) % every == 0


def with_canary(body: str, canary: str) -> str:
    return f"{body}\n\nInternal reference marker: {canary}\n"
