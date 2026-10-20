"""The storage contract. Application code talks to THIS, never to boto3 directly,
so the storage service can change (SeaweedFS today, cloud S3 later) without touching callers."""
from dataclasses import dataclass
from typing import Protocol


class StorageError(Exception):
    """Any storage problem. The message never contains file content or secrets."""


class ObjectNotFound(StorageError):
    pass


@dataclass(frozen=True)
class ObjectInfo:
    key: str
    size: int
    sha256: str | None  # set when the object was written by put_bytes (stored as metadata)


class ObjectStorage(Protocol):
    def ensure_bucket(self) -> None: ...

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> ObjectInfo: ...

    def get_bytes(self, key: str) -> bytes: ...

    def head(self, key: str) -> ObjectInfo: ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...

    def list_keys(self, prefix: str, limit: int = 1000) -> list[str]: ...
