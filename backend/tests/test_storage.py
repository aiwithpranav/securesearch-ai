"""Object storage: real SeaweedFS, a separate test bucket, cleaned up after each test."""
import hashlib
import os
import uuid

import pytest

from app.core.config import settings
from app.storage import ObjectNotFound, S3Storage, StorageError
from app.storage.keys import original_key


@pytest.fixture
def storage():
    s = S3Storage(
        settings.s3_endpoint_url, settings.s3_access_key, settings.s3_secret_key,
        settings.s3_bucket + "-test", settings.s3_region,
    )
    s.ensure_bucket()
    prefix = f"t-{uuid.uuid4()}/"
    s.prefix = prefix  # type: ignore[attr-defined]
    yield s
    for k in s.list_keys(prefix):
        s.delete(k)


def test_round_trip_keeps_bytes_size_and_hash(storage):
    data = os.urandom(1_000_000)  # 1 MB of random bytes
    key = storage.prefix + "blob"
    info = storage.put_bytes(key, data)
    assert info.size == len(data) and info.sha256 == hashlib.sha256(data).hexdigest()
    assert storage.get_bytes(key) == data
    head = storage.head(key)
    assert head.size == len(data) and head.sha256 == info.sha256


def test_missing_object_raises_not_found_and_exists_is_false(storage):
    key = storage.prefix + "nope"
    assert storage.exists(key) is False
    with pytest.raises(ObjectNotFound):
        storage.get_bytes(key)
    with pytest.raises(ObjectNotFound):
        storage.head(key)


def test_delete_is_idempotent_and_list_by_prefix(storage):
    a, b = storage.prefix + "a", storage.prefix + "b"
    storage.put_bytes(a, b"1")
    storage.put_bytes(b, b"2")
    assert sorted(storage.list_keys(storage.prefix)) == [a, b]
    storage.delete(a)
    storage.delete(a)  # second delete must not fail
    assert storage.list_keys(storage.prefix) == [b]


def test_overwrite_same_key_replaces_content(storage):
    key = storage.prefix + "same"
    storage.put_bytes(key, b"old")
    storage.put_bytes(key, b"new")
    assert storage.get_bytes(key) == b"new"


def test_wrong_secret_is_rejected_without_leaking_it():
    bad = S3Storage(settings.s3_endpoint_url, settings.s3_access_key, "wrong-secret-value-123",
                    settings.s3_bucket + "-test", settings.s3_region)
    with pytest.raises(StorageError) as exc:
        bad.put_bytes("x", b"data")
    assert "wrong-secret-value-123" not in str(exc.value)


def test_unreachable_storage_gives_a_clean_error():
    dead = S3Storage("http://127.0.0.1:1", "a", "b", "bucket", "us-east-1")
    with pytest.raises(StorageError):
        dead.ensure_bucket()


def test_original_key_uses_ids_and_hash_only():
    doc = uuid.uuid4()
    digest = hashlib.sha256(b"x").hexdigest()
    assert original_key(doc, 2, digest) == f"documents/{doc}/v2/{digest}"
    with pytest.raises(ValueError):
        original_key(doc, 0, digest)
    with pytest.raises(ValueError):
        original_key(doc, 1, "../../etc/passwd")
