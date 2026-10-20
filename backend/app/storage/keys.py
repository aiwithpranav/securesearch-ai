"""How object keys are built. Keys contain only IDs and a hash, never the user's file name
(file names can hold odd characters or personal data)."""
import re
import uuid

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def original_key(document_id: uuid.UUID, version_no: int, sha256: str) -> str:
    """Key of the original uploaded file: documents/<document id>/v<version>/<sha256>."""
    if version_no < 1:
        raise ValueError("version_no must be 1 or more")
    if not _SHA256.match(sha256):
        raise ValueError("sha256 must be 64 lowercase hex characters")
    return f"documents/{document_id}/v{version_no}/{sha256}"
