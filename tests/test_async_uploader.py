"""AsyncUploader tests."""

from __future__ import annotations

import pytest

from uploadkit import (
    AsyncUploader,
    UploadFailed,
    UploadPolicy,
    UploadResult,
    UploaderError,
)


class MemoryAsyncSource:
    def __init__(
        self,
        content: bytes,
        *,
        name: str = "file.txt",
        content_type: str | None = "text/plain",
    ) -> None:
        self._content = content
        self._offset = 0
        self.name = name
        self.size = len(content)
        self.content_type = content_type

    async def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._content) - self._offset
        data = self._content[self._offset : self._offset + size]
        self._offset += len(data)
        return data


class FakeAsyncWriter:
    def __init__(self, storage: FakeAsyncStorage) -> None:
        self._storage = storage
        self._chunks: list[bytes] = []
        self.aborted = False
        self.completed = False

    async def write(self, chunk: bytes) -> None:
        if self._storage.fail_write:
            raise RuntimeError("write failed")
        self._chunks.append(chunk)

    async def abort(self) -> None:
        self.aborted = True

    async def complete(self) -> str | None:
        self.completed = True
        body = b"".join(self._chunks)
        self._storage.puts.append(body)
        return '"etag-async"'


class FakeAsyncStorage:
    def __init__(self, *, fail_write: bool = False) -> None:
        self.fail_write = fail_write
        self.puts: list[bytes] = []
        self.last_writer: FakeAsyncWriter | None = None

    async def open_write(
        self,
        *,
        bucket: str,
        object_name: str,
        content_type: str,
    ) -> FakeAsyncWriter:
        writer = FakeAsyncWriter(self)
        self.last_writer = writer
        return writer


class RecordingAsyncValidator:
    def __init__(self, *, fail_on_feed: bool = False) -> None:
        self.fail_on_feed = fail_on_feed
        self.begins = 0
        self.feeds: list[bytes] = []
        self.finalizes = 0
        self.context = None

    async def begin(self, *, name, size, content_type, policy, context) -> None:  # noqa: ANN001
        self.begins += 1
        self.context = context

    async def feed(self, chunk: bytes) -> None:
        if self.fail_on_feed:
            raise UploaderError("blocked-async")
        self.feeds.append(chunk)

    async def finalize(self) -> None:
        self.finalizes += 1
        if self.context is not None:
            self.context.mime_type = "text/plain"
            self.context.sha256 = "deadbeef"


@pytest.mark.asyncio
async def test_async_upload_happy_path() -> None:
    storage = FakeAsyncStorage()
    validator = RecordingAsyncValidator()
    uploader = AsyncUploader(
        UploadPolicy(async_validators=(validator,)),
        storage,
        chunk_size=3,
    )

    result = await uploader.upload(
        MemoryAsyncSource(b"hello", name="hello.txt"),
        bucket="b",
        object_name="k/hello.txt",
    )

    assert isinstance(result, UploadResult)
    assert result.original_name == "hello.txt"
    assert result.extension == "txt"
    assert result.size == 5
    assert result.mime_type == "text/plain"
    assert result.sha256 == "deadbeef"
    assert result.etag == "etag-async"
    assert storage.puts == [b"hello"]
    assert validator.begins == 1
    assert validator.feeds == [b"hel", b"lo"]
    assert validator.finalizes == 1


@pytest.mark.asyncio
async def test_async_upload_requires_async_validators() -> None:
    uploader = AsyncUploader(UploadPolicy(), FakeAsyncStorage())
    with pytest.raises(UploaderError, match="async_validators"):
        await uploader.upload(
            MemoryAsyncSource(b"x"),
            bucket="b",
            object_name="x",
        )


@pytest.mark.asyncio
async def test_async_validator_failure_aborts_writer() -> None:
    storage = FakeAsyncStorage()
    uploader = AsyncUploader(
        UploadPolicy(async_validators=(RecordingAsyncValidator(fail_on_feed=True),)),
        storage,
    )
    with pytest.raises(UploaderError, match="blocked-async"):
        await uploader.upload(MemoryAsyncSource(b"data"), bucket="b", object_name="x")
    assert storage.last_writer is not None
    assert storage.last_writer.aborted is True
    assert storage.puts == []


@pytest.mark.asyncio
async def test_async_storage_failure_raises_upload_failed() -> None:
    storage = FakeAsyncStorage(fail_write=True)
    uploader = AsyncUploader(
        UploadPolicy(async_validators=(RecordingAsyncValidator(),)),
        storage,
    )
    with pytest.raises(UploadFailed):
        await uploader.upload(MemoryAsyncSource(b"data"), bucket="b", object_name="x")
    assert storage.last_writer is not None
    assert storage.last_writer.aborted is True


@pytest.mark.asyncio
async def test_async_after_upload_hook() -> None:
    seen: list[UploadResult] = []

    async def hook(result: UploadResult) -> None:
        seen.append(result)

    uploader = AsyncUploader(
        UploadPolicy(async_validators=(RecordingAsyncValidator(),)),
        FakeAsyncStorage(),
    )
    result = await uploader.upload(
        MemoryAsyncSource(b"x", name="a.bin"),
        bucket="b",
        object_name="a.bin",
        after_upload=hook,
    )
    assert seen == [result]


@pytest.mark.asyncio
async def test_sync_after_upload_hook_on_async_uploader() -> None:
    seen: list[UploadResult] = []

    def hook(result: UploadResult) -> None:
        seen.append(result)

    uploader = AsyncUploader(
        UploadPolicy(async_validators=(RecordingAsyncValidator(),)),
        FakeAsyncStorage(),
    )
    result = await uploader.upload(
        MemoryAsyncSource(b"x", name="a.bin"),
        bucket="b",
        object_name="a.bin",
        after_upload=hook,
    )
    assert seen == [result]


@pytest.mark.asyncio
async def test_sync_hook_returning_awaitable() -> None:
    seen: list[UploadResult] = []

    async def _async_body(result: UploadResult) -> None:
        seen.append(result)

    def hook(result: UploadResult):
        return _async_body(result)

    uploader = AsyncUploader(
        UploadPolicy(async_validators=(RecordingAsyncValidator(),)),
        FakeAsyncStorage(),
    )
    result = await uploader.upload(
        MemoryAsyncSource(b"x", name="a.bin"),
        bucket="b",
        object_name="a.bin",
        after_upload=hook,
    )
    assert seen == [result]


@pytest.mark.asyncio
async def test_async_celery_like_after_upload_hook() -> None:
    captured: dict = {}

    class Task:
        def delay(self, **kwargs: str | int | None) -> None:
            captured.update(kwargs)

    uploader = AsyncUploader(
        UploadPolicy(async_validators=(RecordingAsyncValidator(),)),
        FakeAsyncStorage(),
    )
    result = await uploader.upload(
        MemoryAsyncSource(b"data", name="d.csv"),
        bucket="bucket",
        object_name="d.csv",
        after_upload=Task(),
    )
    assert captured == result.as_task_kwargs()


def test_invalid_chunk_size() -> None:
    with pytest.raises(ValueError, match="chunk_size"):
        AsyncUploader(UploadPolicy(async_validators=(RecordingAsyncValidator(),)), FakeAsyncStorage(), chunk_size=0)
