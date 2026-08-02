"""Async streaming validator protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uploadkit.context import UploadContext
    from uploadkit.policy import UploadPolicy


class AsyncStreamingValidator(Protocol):
    """Incremental async validator invoked by ``AsyncUploader``."""

    async def begin(
        self,
        *,
        name: str | None,
        size: int | None,
        content_type: str | None,
        policy: UploadPolicy,
        context: UploadContext,
    ) -> None: ...

    async def feed(self, chunk: bytes) -> None: ...

    async def finalize(self) -> None: ...
