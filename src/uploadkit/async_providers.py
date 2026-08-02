"""Async storage provider protocols.

Storage is an implementation detail. Callers supply a provider.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AsyncObjectWriter(Protocol):
    """Incremental async write handle for one object."""

    async def write(self, chunk: bytes) -> None:
        """Append ``chunk`` to the object being written."""
        ...

    async def abort(self) -> None:
        """Cancel the write and discard partial data when possible."""
        ...

    async def complete(self) -> str | None:
        """Finalize the object and return an etag (or ``None``)."""
        ...


@runtime_checkable
class AsyncStorageProvider(Protocol):
    """Open an async writer for durable object storage."""

    async def open_write(
        self,
        *,
        bucket: str,
        object_name: str,
        content_type: str,
    ) -> AsyncObjectWriter:
        """Begin a streamed put and return a writer."""
        ...
