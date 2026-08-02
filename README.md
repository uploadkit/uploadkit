# UploadKit

[![CI](https://github.com/uploadkit/uploadkit/actions/workflows/ci.yml/badge.svg)](https://github.com/uploadkit/uploadkit/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/uploadkit/uploadkit/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](pyproject.toml)

Framework-independent secure upload pipeline for Python.

## What problem does this solve?

UploadKit Core owns validation orchestration, upload policies, storage provider interfaces, after-upload hooks, and a stable exception hierarchy — without depending on Django, FastAPI, Flask, or any storage SDK.

## When to use it

Use Core when you need a reusable upload pipeline that you can plug into any framework and any object store.

## When not to use it

- Do not put framework adapters here (see `uploadkit-django`, `uploadkit-fastapi`, etc.).
- Do not put MIME/filename/checksum validators here (see `uploadkit-security`).
- Do not put image/PDF/office-specific policies here (see feature packages).

## Installation

Requires **Python 3.10+**.

```bash
pip install uploadkit uploadkit-security
```

```bash
uv add uploadkit uploadkit-security
```

```bash
poetry add uploadkit uploadkit-security
```

For the storage samples below (not package dependencies):

```bash
pip install boto3          # sync AWS S3 / MinIO
pip install aioboto3       # async AWS S3 / MinIO
```

## Quick Start (sync)

```python
from uploadkit import Uploader, UploadPolicy
from uploadkit_security import default_validators

policy = UploadPolicy(
    max_size=5 * 1024 * 1024,
    allowed_extensions=frozenset({"png"}),
    allowed_mime_types=frozenset({"image/png"}),
    validators=default_validators(),
)
result = Uploader(policy, storage).upload(
    file,  # UploadableFile
    bucket="uploads",
    object_name="2026/file.png",
)
# result.bucket, result.object_name, result.sha256, result.etag, …
```

## Quick Start (async streaming)

```python
from uploadkit import AsyncUploader, UploadPolicy
from uploadkit_security import default_async_validators

policy = UploadPolicy(
    max_size=5 * 1024 * 1024,
    allowed_extensions=frozenset({"png"}),
    allowed_mime_types=frozenset({"image/png"}),
    async_validators=default_async_validators(),
)
result = await AsyncUploader(policy, async_storage).upload(
    source,  # AsyncByteSource
    bucket="uploads",
    object_name="2026/file.png",
)
```

## Storage examples (AWS S3 and MinIO)

UploadKit does **not** ship boto3/aioboto3. Implement the protocols once; the same classes work for **AWS S3** (omit `endpoint_url`) and **MinIO** (set `endpoint_url`).

### Sync — `Boto3S3Storage` (`StorageProvider`)

```python
import boto3
from botocore.client import Config

class Boto3S3Storage:
    """S3-compatible sync storage for AWS S3 or MinIO."""

    def __init__(
        self,
        *,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
    ) -> None:
        kwargs: dict = {
            "service_name": "s3",
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region,
            "config": Config(signature_version="s3v4"),
        }
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self.client = boto3.client(**kwargs)

    def put(self, *, bucket, object_name, body, content_type):
        resp = self.client.put_object(
            Bucket=bucket,
            Key=object_name,
            Body=body,
            ContentType=content_type,
        )
        return resp.get("ETag")
```

**AWS S3:**

```python
storage = Boto3S3Storage(
    access_key="AKIA...",
    secret_key="...",
    region="eu-west-1",
)
```

**MinIO** (local default):

```python
storage = Boto3S3Storage(
    endpoint_url="http://127.0.0.1:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    region="us-east-1",
)
```

### Async — `AsyncS3Storage` (`AsyncStorageProvider`)

Multipart streaming writer (5 MiB part size — S3/MinIO rule except the last part):

```python
from __future__ import annotations

import aioboto3
from botocore.client import Config

_PART_SIZE = 5 * 1024 * 1024  # 5 MiB


class AsyncS3Writer:
    def __init__(self, client, *, bucket: str, object_name: str, content_type: str) -> None:
        self._client = client
        self._bucket = bucket
        self._key = object_name
        self._content_type = content_type
        self._upload_id: str | None = None
        self._parts: list[dict] = []
        self._buffer = bytearray()
        self._part_number = 1

    async def _ensure_upload(self) -> None:
        if self._upload_id is not None:
            return
        resp = await self._client.create_multipart_upload(
            Bucket=self._bucket,
            Key=self._key,
            ContentType=self._content_type,
        )
        self._upload_id = resp["UploadId"]

    async def _flush_part(self, data: bytes) -> None:
        await self._ensure_upload()
        assert self._upload_id is not None
        resp = await self._client.upload_part(
            Bucket=self._bucket,
            Key=self._key,
            PartNumber=self._part_number,
            UploadId=self._upload_id,
            Body=data,
        )
        self._parts.append({"ETag": resp["ETag"], "PartNumber": self._part_number})
        self._part_number += 1

    async def write(self, chunk: bytes) -> None:
        self._buffer.extend(chunk)
        while len(self._buffer) >= _PART_SIZE:
            part = bytes(self._buffer[:_PART_SIZE])
            del self._buffer[:_PART_SIZE]
            await self._flush_part(part)

    async def abort(self) -> None:
        if self._upload_id is None:
            return
        await self._client.abort_multipart_upload(
            Bucket=self._bucket,
            Key=self._key,
            UploadId=self._upload_id,
        )
        self._upload_id = None

    async def complete(self) -> str | None:
        if self._buffer:
            await self._flush_part(bytes(self._buffer))
            self._buffer.clear()
        if self._upload_id is None:
            # empty object
            resp = await self._client.put_object(
                Bucket=self._bucket,
                Key=self._key,
                Body=b"",
                ContentType=self._content_type,
            )
            return resp.get("ETag")
        resp = await self._client.complete_multipart_upload(
            Bucket=self._bucket,
            Key=self._key,
            UploadId=self._upload_id,
            MultipartUpload={"Parts": self._parts},
        )
        self._upload_id = None
        return resp.get("ETag")


class AsyncS3Storage:
    """S3-compatible async storage for AWS S3 or MinIO."""

    def __init__(
        self,
        *,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
    ) -> None:
        self._session = aioboto3.Session()
        self._client_kwargs: dict = {
            "service_name": "s3",
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region,
            "config": Config(signature_version="s3v4"),
        }
        if endpoint_url:
            self._client_kwargs["endpoint_url"] = endpoint_url
        self._cm = None
        self._client = None

    async def _get_client(self):
        if self._client is None:
            self._cm = self._session.client(**self._client_kwargs)
            self._client = await self._cm.__aenter__()
        return self._client

    async def open_write(self, *, bucket: str, object_name: str, content_type: str):
        client = await self._get_client()
        return AsyncS3Writer(
            client,
            bucket=bucket,
            object_name=object_name,
            content_type=content_type,
        )
```

**AWS S3:**

```python
async_storage = AsyncS3Storage(
    access_key="AKIA...",
    secret_key="...",
    region="eu-west-1",
)
```

**MinIO:**

```python
async_storage = AsyncS3Storage(
    endpoint_url="http://127.0.0.1:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
)
```

## Validators (`uploadkit-security`)

```python
from uploadkit_security import default_validators, default_async_validators

validators = default_validators()                 # sync Uploader
async_validators = default_async_validators()     # AsyncUploader
```

## Architecture

```text
Sync:  Uploader.upload → validators → StorageProvider.put → UploadResult → after_upload
Async: AsyncUploader.upload → async validators feed → AsyncStorageProvider writer → UploadResult
```

## Public API

| Symbol | Kind |
|--------|------|
| `Uploader` / `AsyncUploader` | Public |
| `UploadPolicy` | Public (`validators` / `async_validators`) |
| `UploadResult` / `UploadContext` | Public |
| `UploadableFile` / `AsyncByteSource` | Public (protocols) |
| `StorageProvider` / `AsyncStorageProvider` / `AsyncObjectWriter` | Public (protocols) |
| `Validator` / `AsyncStreamingValidator` | Public |
| `UploaderError` and subclasses | Public |
| `AfterUploadHook` / async after-upload | Public |

## Framework integrations

- Django: [`uploadkit-django`](https://github.com/uploadkit/uploadkit-django)
- FastAPI: [`uploadkit-fastapi`](https://github.com/uploadkit/uploadkit-fastapi)
- aiohttp: use Core `AsyncByteSource` directly (see [docs site](https://uploadkit.github.io/))

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
