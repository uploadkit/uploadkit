"""After-upload hook protocols and invocation helper.

No Celery import — duck-types objects with ``.delay(**kwargs)``.
"""

from __future__ import annotations

from typing import Protocol, Union

from uploadkit.result import UploadResult


class AfterUploadCallback(Protocol):
    """Sync callback: ``(result: UploadResult) -> None``."""

    def __call__(self, result: UploadResult) -> None: ...


class CeleryTaskLike(Protocol):
    """Duck-typed Celery task: anything with ``.delay(**kwargs)``."""

    def delay(self, **kwargs: str | int | None) -> object: ...


AfterUploadHook = Union[AfterUploadCallback, CeleryTaskLike]


def invoke_after_upload(hook: AfterUploadHook, result: UploadResult) -> None:
    """Invoke a sync callback or enqueue a Celery-like task.

    Exceptions propagate (not swallowed).
    """
    delay = getattr(hook, "delay", None)
    if callable(delay):
        delay(**result.as_task_kwargs())
        return
    hook(result)  # type: ignore[operator]
