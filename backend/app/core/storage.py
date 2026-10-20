"""Immutable document storage. Keys are content-addressed, so an object is never overwritten."""

from pathlib import Path
from typing import Protocol

import boto3

from app.core.config import get_settings


class DocumentStore(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...


class LocalStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"Invalid storage key: {key}")
        return path

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        if path.exists():
            return  # same key = same content
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()


class S3Store:
    def __init__(self, bucket: str, endpoint_url: str | None, region: str) -> None:
        self.bucket = bucket
        self.client = boto3.client("s3", endpoint_url=endpoint_url or None, region_name=region)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self.client.put_object(
                Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, IfNoneMatch="*"
            )
        except self.client.exceptions.ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "PreconditionFailed":
                raise

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()


def get_store() -> DocumentStore:
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3Store(settings.s3_bucket, settings.s3_endpoint_url, settings.aws_region)
    return LocalStore(Path(settings.local_storage_dir))
