"""Core package tests. Uses a minimal inline fake storage/file."""

from __future__ import annotations

from io import BytesIO

import pytest

from uploadkit import (
    UploadFailed,
    UploadPolicy,
    UploadResult,
    Uploader,
    UploaderError,
)


class MemoryFile:
    def __init__(
        self,
        content: bytes,
        *,
        name: str = "file.txt",
        content_type: str | None = "text/plain",
    ) -> None:
        self._buffer = BytesIO(content)
        self.name = name
        self.size = len(content)
        self.content_type = content_type

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._buffer.seek(offset, whence)

    def tell(self) -> int:
        return self._buffer.tell()


class FakeStorage:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.puts: list[dict] = []

    def put(
        self,
        *,
        bucket: str,
        object_name: str,
        body: bytes,
        content_type: str,
    ) -> str | None:
        if self.fail:
            raise RuntimeError("storage down")
        self.puts.append(
            {
                "bucket": bucket,
                "object_name": object_name,
                "body": body,
                "content_type": content_type,
            }
        )
        return '"abc123"'


class FailingValidator:
    def validate(self, file, policy) -> None:  # noqa: ANN001
        raise UploaderError("blocked")


def test_upload_happy_path() -> None:
    storage = FakeStorage()
    uploader = Uploader(UploadPolicy(), storage)
    file = MemoryFile(b"hello", name="hello.txt")

    result = uploader.upload(file, bucket="b", object_name="k/hello.txt")

    assert isinstance(result, UploadResult)
    assert result.bucket == "b"
    assert result.object_name == "k/hello.txt"
    assert result.original_name == "hello.txt"
    assert result.extension == "txt"
    assert result.size == 5
    assert result.etag == "abc123" or result.etag == '"abc123"'
    assert len(storage.puts) == 1
    assert storage.puts[0]["body"] == b"hello"


def test_validation_short_circuits_before_storage() -> None:
    storage = FakeStorage()
    policy = UploadPolicy(validators=(FailingValidator(),))
    uploader = Uploader(policy, storage)

    with pytest.raises(UploaderError, match="blocked"):
        uploader.upload(MemoryFile(b"x"), bucket="b", object_name="x")

    assert storage.puts == []


def test_storage_failure_raises_upload_failed() -> None:
    uploader = Uploader(UploadPolicy(), FakeStorage(fail=True))

    with pytest.raises(UploadFailed):
        uploader.upload(MemoryFile(b"x"), bucket="b", object_name="x")


def test_sync_after_upload_hook() -> None:
    seen: list[UploadResult] = []

    def hook(result: UploadResult) -> None:
        seen.append(result)

    uploader = Uploader(UploadPolicy(), FakeStorage())
    result = uploader.upload(
        MemoryFile(b"x", name="a.bin"),
        bucket="b",
        object_name="a.bin",
        after_upload=hook,
    )
    assert seen == [result]


def test_celery_like_after_upload_hook() -> None:
    captured: dict = {}

    class Task:
        def delay(self, **kwargs: str | int | None) -> None:
            captured.update(kwargs)

    uploader = Uploader(UploadPolicy(), FakeStorage())
    result = uploader.upload(
        MemoryFile(b"data", name="d.csv"),
        bucket="bucket",
        object_name="d.csv",
        after_upload=Task(),
    )
    assert captured == result.as_task_kwargs()


def test_upload_result_as_task_kwargs() -> None:
    result = UploadResult(
        bucket="b",
        object_name="o",
        original_name="n.txt",
        mime_type="text/plain",
        extension="txt",
        size=1,
        sha256="abc",
        etag="e",
    )
    assert result.as_task_kwargs()["sha256"] == "abc"
