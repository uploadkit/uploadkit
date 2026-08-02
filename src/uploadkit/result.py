"""Immutable UploadResult returned after a successful upload."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UploadResult:
    """Everything the business layer needs after an upload."""

    bucket: str
    object_name: str
    original_name: str
    mime_type: str
    extension: str
    size: int
    sha256: str | None
    etag: str | None

    def as_task_kwargs(self) -> dict[str, str | int | None]:
        """JSON-serializable dict for ``task.delay(**result.as_task_kwargs())``."""
        return {
            "bucket": self.bucket,
            "object_name": self.object_name,
            "original_name": self.original_name,
            "mime_type": self.mime_type,
            "extension": self.extension,
            "size": self.size,
            "sha256": self.sha256,
            "etag": self.etag,
        }
