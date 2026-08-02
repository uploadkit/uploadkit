"""Framework-agnostic file protocol.

Duck-types Django's ``UploadedFile`` (``name``, ``size``, ``content_type``,
``read`` / ``seek`` / ``tell``).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class UploadableFile(Protocol):
    """Minimal file interface accepted by ``Uploader.upload``."""

    @property
    def name(self) -> str | None: ...

    @property
    def size(self) -> int | None: ...

    @property
    def content_type(self) -> str | None: ...

    def read(self, size: int = -1) -> bytes: ...

    def seek(self, offset: int, whence: int = 0) -> int: ...

    def tell(self) -> int: ...
