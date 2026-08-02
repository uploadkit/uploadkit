"""Shared pure helpers used by core orchestration."""

from __future__ import annotations

import os

# Side-channel attribute names set by validators (e.g. uploadkit-security).
UPLOADER_SHA256_ATTR = "uploader_sha256"
UPLOADER_MIME_ATTR = "uploader_mime_type"


def get_extension(filename: str) -> str:
    """Return the lowercased file extension without the leading dot."""
    _, ext = os.path.splitext(filename or "")
    return ext.lstrip(".").lower()
