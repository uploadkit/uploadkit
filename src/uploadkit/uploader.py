"""Main entry point: validate → storage put → callback → UploadResult."""

from __future__ import annotations

import logging

from uploadkit._utils import (
    UPLOADER_MIME_ATTR,
    UPLOADER_SHA256_ATTR,
    get_extension,
)
from uploadkit.exceptions import UploadFailed
from uploadkit.files import UploadableFile
from uploadkit.hooks import AfterUploadHook, invoke_after_upload
from uploadkit.pipeline import run_validators
from uploadkit.policy import UploadPolicy
from uploadkit.providers import StorageProvider
from uploadkit.result import UploadResult

logger = logging.getLogger(__name__)


class Uploader:
    """Sole public entry point for the upload pipeline.

    Responsibilities (in order):

    1. Receive an ``UploadableFile``
    2. Execute the validation pipeline (``run_validators``)
    3. Upload via the configured ``StorageProvider``
    4. Build an immutable ``UploadResult``
    5. Invoke the optional ``after_upload`` hook once
    6. Return ``UploadResult``
    """

    def __init__(self, policy: UploadPolicy, storage: StorageProvider) -> None:
        self.policy = policy
        self.storage = storage

    def upload(
        self,
        file: UploadableFile,
        *,
        bucket: str,
        object_name: str,
        after_upload: AfterUploadHook | None = None,
    ) -> UploadResult:
        """Validate, store, optionally callback, return ``UploadResult``."""
        run_validators(file, self.policy)

        original_name = file.name or ""
        mime_type = (
            getattr(file, UPLOADER_MIME_ATTR, None)
            or getattr(file, "content_type", None)
            or "application/octet-stream"
        )
        extension = get_extension(original_name)
        size = file.size if file.size is not None else 0
        sha256 = getattr(file, UPLOADER_SHA256_ATTR, None)

        try:
            body = file.read()
            etag = self.storage.put(
                bucket=bucket,
                object_name=object_name,
                body=body,
                content_type=mime_type,
            )
        except Exception as exc:
            logger.exception(
                "Storage upload failed",
                extra={"bucket": bucket, "object_name": object_name},
            )
            raise UploadFailed("Upload to object storage failed") from exc

        cleaned_etag = etag.strip('"') if etag else None

        result = UploadResult(
            bucket=bucket,
            object_name=object_name,
            original_name=original_name,
            mime_type=mime_type,
            extension=extension,
            size=size,
            sha256=sha256,
            etag=cleaned_etag or None,
        )

        if after_upload:
            invoke_after_upload(after_upload, result)

        return result
