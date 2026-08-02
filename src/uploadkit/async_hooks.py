"""Async after-upload hook invocation."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Union

from uploadkit.hooks import CeleryTaskLike
from uploadkit.result import UploadResult

AsyncAfterUploadCallback = Callable[[UploadResult], Awaitable[None] | None]
AsyncAfterUploadHook = Union[AsyncAfterUploadCallback, CeleryTaskLike]


async def invoke_after_upload_async(
    hook: AsyncAfterUploadHook,
    result: UploadResult,
) -> None:
    """Invoke sync/async callback or enqueue a Celery-like task.

    Exceptions propagate (not swallowed).
    """
    delay = getattr(hook, "delay", None)
    if callable(delay):
        delay(**result.as_task_kwargs())
        return

    if inspect.iscoroutinefunction(hook):
        await hook(result)  # type: ignore[misc]
        return

    maybe_awaitable = hook(result)  # type: ignore[operator]
    if inspect.isawaitable(maybe_awaitable):
        await maybe_awaitable
