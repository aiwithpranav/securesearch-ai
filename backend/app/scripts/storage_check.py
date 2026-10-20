"""Checks that object storage works, and lists what is stored (keys and sizes only, never content).

Run inside the backend container:
    docker compose exec backend python -m app.scripts.storage_check
Creates the bucket if it does not exist, writes a tiny test object, reads it back, deletes it."""
import sys
import uuid

from app.core.config import settings
from app.storage import StorageError, get_storage


def main() -> int:
    storage = get_storage()
    try:
        storage.ensure_bucket()
        key = f"healthcheck/{uuid.uuid4()}"
        payload = b"storage check"
        storage.put_bytes(key, payload)
        ok = storage.get_bytes(key) == payload
        storage.delete(key)
        print(f"Bucket '{settings.s3_bucket}' is reachable. Write, read and delete: {'OK' if ok else 'MISMATCH'}.")
        keys = storage.list_keys("documents/", limit=50)
        print(f"Stored document objects (first 50 keys): {len(keys)}")
        for k in keys:
            info = storage.head(k)
            print(f"  {k}  {info.size} bytes")
        return 0 if ok else 1
    except StorageError as exc:
        print(f"Storage problem: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
