"""Async entry point: stream validate → storage write → callback → UploadResult."""

from __future__ import annotations

import logging
from typing import Final

from uploadkit._utils import get_extension
from uploadkit.async_files import AsyncByteSource
from uploadkit.async_hooks import AsyncAfterUploadHook, invoke_after_upload_async
from uploadkit.async_pipeline import AsyncStreamingValidator
from uploadkit.async_providers import AsyncObjectWriter, AsyncStorageProvider
from uploadkit.context import UploadContext
from uploadkit.exceptions import UploadFailed, UploaderError
from uploadkit.policy import UploadPolicy
from uploadkit.result import UploadResult

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE: Final = 1024 * 1024


class AsyncUploader:
    """Async streaming upload pipeline.

    Responsibilities (in order):

    1. Require ``policy.async_validators`` (separate from sync validators)
    2. ``begin`` all async validators
    3. Open async storage writer
    4. Read chunks → ``feed`` validators → ``write`` storage
    5. ``finalize`` validators and ``complete`` storage
    6. Invoke optional ``after_upload`` hook
    7. Return ``UploadResult``
    """

    def __init__(
        self,
        policy: UploadPolicy,
        storage: AsyncStorageProvider,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        self.policy = policy
        self.storage = storage
        self.chunk_size = chunk_size

    async def upload(
        self,
        source: AsyncByteSource,
        *,
        bucket: str,
        object_name: str,
        after_upload: AsyncAfterUploadHook | None = None,
    ) -> UploadResult:
        """Validate and store ``source`` asynchronously."""
        validators = self._require_async_validators()
        context = UploadContext(
            name=source.name,
            size=source.size,
            content_type=source.content_type,
        )

        for validator in validators:
            await validator.begin(
                name=source.name,
                size=source.size,
                content_type=source.content_type,
                policy=self.policy,
                context=context,
            )

        content_type = (
            context.mime_type
            or source.content_type
            or "application/octet-stream"
        )
        writer: AsyncObjectWriter | None = None
        try:
            writer = await self.storage.open_write(
                bucket=bucket,
                object_name=object_name,
                content_type=content_type,
            )
            while True:
                chunk = await source.read(self.chunk_size)
                if not chunk:
                    break
                context.bytes_seen += len(chunk)
                for validator in validators:
                    await validator.feed(chunk)
                await writer.write(chunk)

            for validator in validators:
                await validator.finalize()

            etag = await writer.complete()
            writer = None
        except UploaderError:
            if writer is not None:
                await writer.abort()
            raise
        except Exception as exc:
            if writer is not None:
                await writer.abort()
            logger.exception(
                "Async storage upload failed",
                extra={"bucket": bucket, "object_name": object_name},
            )
            raise UploadFailed("Upload to object storage failed") from exc

        original_name = source.name or ""
        size = (
            context.size
            if context.size is not None
            else context.bytes_seen
        )
        mime_type = (
            context.mime_type
            or source.content_type
            or "application/octet-stream"
        )
        cleaned_etag = etag.strip('"') if etag else None

        result = UploadResult(
            bucket=bucket,
            object_name=object_name,
            original_name=original_name,
            mime_type=mime_type,
            extension=get_extension(original_name),
            size=size if size is not None else 0,
            sha256=context.sha256,
            etag=cleaned_etag or None,
        )

        if after_upload:
            await invoke_after_upload_async(after_upload, result)

        return result

    def _require_async_validators(self) -> tuple[AsyncStreamingValidator, ...]:
        validators = tuple(self.policy.async_validators)
        if not validators:
            raise UploaderError(
                "AsyncUploader requires policy.async_validators; "
                "use sync Uploader with policy.validators for the sync stack"
            )
        return validators
