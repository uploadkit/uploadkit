"""Upload policy configuration only."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from uploadkit.pipeline import Validator

if TYPE_CHECKING:
    from uploadkit.async_pipeline import AsyncStreamingValidator


@dataclass(frozen=True, slots=True)
class UploadPolicy:
    """Configuration only — no business logic."""

    max_size: int | None = None
    allowed_extensions: frozenset[str] = frozenset()
    allowed_mime_types: frozenset[str] = frozenset()
    validators: Sequence[Validator] = field(default_factory=tuple)
    async_validators: Sequence[AsyncStreamingValidator] = field(
        default_factory=tuple
    )
