"""S3 implementation of ObjectStorage using boto3. Works with SeaweedFS and with cloud S3."""
import hashlib

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.storage.base import ObjectInfo, ObjectNotFound, StorageError

_NOT_FOUND_CODES = {"404", "NoSuchKey", "NotFound", "NoSuchBucket"}


def _code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


class S3Storage:
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket: str, region: str) -> None:
        self.bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},  # http://storage:8333/<bucket>/<key>
                connect_timeout=5,
                read_timeout=30,
                retries={"max_attempts": 3, "mode": "standard"},  # bounded retries
            ),
        )

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            if _code(exc) not in _NOT_FOUND_CODES:
                raise StorageError(f"Cannot open bucket (code {_code(exc)}).") from None
            try:
                self._client.create_bucket(Bucket=self.bucket)
            except (ClientError, BotoCoreError) as exc2:
                raise StorageError(f"Cannot create bucket ({type(exc2).__name__}).") from None
        except BotoCoreError as exc:
            raise StorageError(f"Cannot reach storage ({type(exc).__name__}).") from None

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> ObjectInfo:
        digest = hashlib.sha256(data).hexdigest()
        try:
            self._client.put_object(
                Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, Metadata={"sha256": digest}
            )
        except (ClientError, BotoCoreError) as exc:
            raise StorageError(f"Upload failed ({type(exc).__name__}).") from None
        return ObjectInfo(key=key, size=len(data), sha256=digest)

    def get_bytes(self, key: str) -> bytes:
        try:
            return self._client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except ClientError as exc:
            if _code(exc) in _NOT_FOUND_CODES:
                raise ObjectNotFound("Object not found.") from None
            raise StorageError(f"Download failed (code {_code(exc)}).") from None
        except BotoCoreError as exc:
            raise StorageError(f"Download failed ({type(exc).__name__}).") from None

    def head(self, key: str) -> ObjectInfo:
        try:
            r = self._client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if _code(exc) in _NOT_FOUND_CODES:
                raise ObjectNotFound("Object not found.") from None
            raise StorageError(f"Lookup failed (code {_code(exc)}).") from None
        except BotoCoreError as exc:
            raise StorageError(f"Lookup failed ({type(exc).__name__}).") from None
        return ObjectInfo(key=key, size=int(r["ContentLength"]), sha256=r.get("Metadata", {}).get("sha256"))

    def exists(self, key: str) -> bool:
        try:
            self.head(key)
            return True
        except ObjectNotFound:
            return False

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)  # S3 delete is idempotent
        except (ClientError, BotoCoreError) as exc:
            raise StorageError(f"Delete failed ({type(exc).__name__}).") from None

    def list_keys(self, prefix: str, limit: int = 1000) -> list[str]:
        try:
            r = self._client.list_objects_v2(Bucket=self.bucket, Prefix=prefix, MaxKeys=limit)
        except (ClientError, BotoCoreError) as exc:
            raise StorageError(f"List failed ({type(exc).__name__}).") from None
        return [o["Key"] for o in r.get("Contents", [])]


def get_storage() -> S3Storage:
    """Builds a storage client from the settings. Cheap to call; boto3 clients are thread-safe."""
    return S3Storage(
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=settings.s3_bucket,
        region=settings.s3_region,
    )
