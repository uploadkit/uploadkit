"""Mutable upload context for async streaming validators."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class UploadContext:
    """Side-channel values collected during async validation/upload."""

    name: str | None = None
    size: int | None = None
    content_type: str | None = None
    mime_type: str | None = None
    sha256: str | None = None
    bytes_seen: int = 0
    extras: dict[str, object] = field(default_factory=dict)
