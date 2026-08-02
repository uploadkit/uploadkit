"""UploadKit core exceptions.

The uploader only raises. Callers catch and map to API responses.
"""

from __future__ import annotations


class UploaderError(Exception):
    """Base exception for all UploadKit errors."""


class UploadFailed(UploaderError):
    """Raised when the storage put operation fails."""


class InvalidExtension(UploaderError):
    """Raised when the file extension is not allowed by the policy."""


class InvalidMimeType(UploaderError):
    """Raised when the detected MIME type is not allowed by the policy."""


class FileTooLarge(UploaderError):
    """Raised when the file exceeds the policy maximum size."""


class InvalidFileName(UploaderError):
    """Raised when the file name fails sanitization or validation."""


class EmptyFile(UploaderError):
    """Raised when the uploaded file is empty."""


class InvalidFileContent(UploaderError):
    """Raised when file content fails domain-specific validation."""
