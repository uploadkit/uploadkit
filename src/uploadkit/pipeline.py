"""Validation pipeline and Validator protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from uploadkit.files import UploadableFile

if TYPE_CHECKING:
    from uploadkit.policy import UploadPolicy


class Validator(Protocol):
    """Single-responsibility validator invoked by the pipeline."""

    def validate(self, file: UploadableFile, policy: UploadPolicy) -> None: ...


def run_validators(file: UploadableFile, policy: UploadPolicy) -> None:
    """Execute ``policy.validators`` in order (fail-fast)."""
    for validator in policy.validators:
        validator.validate(file, policy)
