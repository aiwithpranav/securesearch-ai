"""Copies the uploaded original files out of (and back into) the file store as one tar stream (Phase 9B, backup and restore).

    docker compose exec -T backend python -m app.scripts.storage_archive export > files.tar
    docker compose exec -T backend python -m app.scripts.storage_archive import < files.tar

Used by scripts/backup.sh and scripts/restore.sh. The stream ends with a `manifest.json` (every key with its SHA-256 and size);
`import` checks every file against it and exits with 1 if anything does not match, so a damaged backup is never half-trusted.
The files are the company's documents: treat the archive like the documents themselves (never commit it, keep it private)."""
import hashlib
import io
import json
import sys
import tarfile

from app.storage import get_storage

PREFIX = "documents/"
MANIFEST = "manifest.json"


def export_files(out) -> int:  # type: ignore[no-untyped-def]
    storage = get_storage()
    storage.ensure_bucket()
    manifest: dict[str, dict[str, object]] = {}
    with tarfile.open(fileobj=out, mode="w|") as tar:
        for key in sorted(storage.list_keys(PREFIX, limit=100000)):
            data = storage.get_bytes(key)
            info = tarfile.TarInfo(key)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
            manifest[key] = {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
        body = json.dumps(manifest, sort_keys=True).encode("utf-8")
        info = tarfile.TarInfo(MANIFEST)
        info.size = len(body)
        tar.addfile(info, io.BytesIO(body))
    return len(manifest)


def import_files(src) -> int:  # type: ignore[no-untyped-def]
    storage = get_storage()
    storage.ensure_bucket()
    seen: dict[str, dict[str, object]] = {}
    manifest: dict[str, dict[str, object]] | None = None
    with tarfile.open(fileobj=src, mode="r|") as tar:
        for member in tar:
            f = tar.extractfile(member)
            if f is None:
                continue
            data = f.read()
            if member.name == MANIFEST:
                manifest = json.loads(data.decode("utf-8"))
                continue
            if not member.name.startswith(PREFIX) or ".." in member.name:
                raise ValueError("unexpected path in the archive")
            storage.put_bytes(member.name, data, "application/octet-stream")
            seen[member.name] = {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
    if manifest is None:
        raise ValueError("the archive has no manifest (it is incomplete)")
    if manifest != seen:
        raise ValueError("the files do not match the manifest")
    return len(seen)


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in ("export", "import"):
        print("Usage: python -m app.scripts.storage_archive export|import", file=sys.stderr)
        return 2
    try:
        n = export_files(sys.stdout.buffer) if argv[0] == "export" else import_files(sys.stdin.buffer)
    except Exception as exc:  # noqa: BLE001
        print(f"{argv[0]} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"{argv[0]}: {n} file(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
