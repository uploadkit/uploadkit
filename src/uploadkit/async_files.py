"""Framework-agnostic async byte source protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AsyncByteSource(Protocol):
    """Minimal async readable accepted by ``AsyncUploader.upload``."""

    @property
    def name(self) -> str | None: ...

    @property
    def size(self) -> int | None: ...

    @property
    def content_type(self) -> str | None: ...

    async def read(self, size: int = -1) -> bytes: ...
