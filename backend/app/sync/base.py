"""What a source has to be able to do (Phase 8B), and the list of known source kinds.

A connector is deliberately small and knows nothing about the database or access rules: it lists items, reads one item and
says which teams (groups) may read each item and who is in each team. The sync engine does everything else.
Secrets (tokens) are read by the connector from the environment, never from the source's saved settings."""
import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

FORBIDDEN_CONFIG_WORDS = ("token", "secret", "password", "passwd", "apikey", "api_key", "credential", "authorization")


@dataclass(frozen=True)
class SourceItem:
    external_id: str  # stable id inside the source (for example a file path); never changes when the file changes
    title: str
    filename: str  # with an extension: the upload rules (pdf, docx, txt, md) apply
    groups: frozenset[str] = field(default_factory=frozenset)  # local team names that may read it (the engine adds the prefix)
    url: str | None = None


class Connector(Protocol):
    def list_items(self) -> list[SourceItem]: ...

    def read(self, item: SourceItem) -> bytes: ...

    def members(self) -> dict[str, set[str]]:
        """Team name -> member email addresses (any case)."""
        ...


@dataclass(frozen=True)
class ConnectorSpec:
    build: Callable[[dict[str, Any]], Connector]
    validate: Callable[[dict[str, Any]], None]  # raises ValueError with a plain sentence


REGISTRY: dict[str, ConnectorSpec] = {}


def register(kind: str, spec: ConnectorSpec) -> None:
    REGISTRY[kind.upper()] = spec


def permission_hash(groups: frozenset[str] | set[str]) -> str:
    """A fingerprint of who may read an item. The order of the teams does not matter."""
    return hashlib.sha256("\n".join(sorted(groups)).encode("utf-8")).hexdigest()


def find_secret_key(config: Any, path: str = "") -> str | None:
    """The first key in the settings that looks like a secret (searched inside nested settings too), or None."""
    if isinstance(config, dict):
        for k, v in config.items():
            if any(w in str(k).lower() for w in FORBIDDEN_CONFIG_WORDS):
                return f"{path}{k}"
            found = find_secret_key(v, f"{path}{k}.")
            if found:
                return found
    elif isinstance(config, list):
        for i, v in enumerate(config):
            found = find_secret_key(v, f"{path}{i}.")
            if found:
                return found
    return None
