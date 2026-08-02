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

- Do not put framework adapters here (see `uploadkit-django`, etc.).
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

## Quick Start

```python
from uploadkit import Uploader, UploadPolicy

class MyStorage:
    def put(self, *, bucket, object_name, body, content_type):
        # put to S3 / MinIO / local disk …
        return "etag-value"

policy = UploadPolicy(max_size=5 * 1024 * 1024)
uploader = Uploader(policy=policy, storage=MyStorage())
result = uploader.upload(file, bucket="uploads", object_name="2026/file.bin")
# result.bucket, result.object_name, result.sha256, …
```

### Async streaming (separate stack)

```python
from uploadkit import AsyncUploader, UploadPolicy
from uploadkit_security import default_async_validators

policy = UploadPolicy(
    max_size=5 * 1024 * 1024,
    async_validators=default_async_validators(),
)
result = await AsyncUploader(policy, async_storage).upload(
    source,  # AsyncByteSource
    bucket="uploads",
    object_name="2026/file.bin",
)
```

Compose security validators from `uploadkit-security`:

```python
from uploadkit import UploadPolicy
from uploadkit_security import default_validators

# All stock defaults
validators = default_validators()

# Clear stock defaults and use only your own
validators = default_validators(include=(), extra=(MyValidator(),))

policy = UploadPolicy(
    max_size=10 * 1024 * 1024,
    allowed_extensions=frozenset({"xlsx"}),
    allowed_mime_types=frozenset({
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    }),
    validators=validators,
)
```

## Architecture

```text
Uploader.upload(...)
  → run_validators(policy.validators)
  → StorageProvider.put(...)
  → UploadResult
  → after_upload (sync callback and/or Celery-like .delay)
```

## Public API

| Symbol | Kind |
|--------|------|
| `Uploader` | Public |
| `UploadPolicy` | Public |
| `UploadResult` | Public |
| `UploadableFile` | Public (protocol) |
| `StorageProvider` | Public (protocol) |
| `Validator` / `run_validators` | Public (extension points) |
| `UPLOADER_MIME_ATTR` / `UPLOADER_SHA256_ATTR` | Public (validator side-channels) |
| `UploaderError` and subclasses | Public |
| `AfterUploadHook` | Public |

## Examples

See Quick Start above. For Django, use `uploadkit-django`. For fake storage in tests, use `uploadkit-testing`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
