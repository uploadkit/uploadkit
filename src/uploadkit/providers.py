"""Storage provider protocol.

Storage is an implementation detail. Callers supply a provider.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageProvider(Protocol):
    """Put object bytes into durable storage."""

    def put(
        self,
        *,
        bucket: str,
        object_name: str,
        body: bytes,
        content_type: str,
    ) -> str | None:
        """Store ``body`` and return an etag (or ``None``)."""
        ...
