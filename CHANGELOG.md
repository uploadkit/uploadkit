# Changelog

## 0.2.0 — 2026-08-02

- Add separate async streaming stack: `AsyncUploader`, `AsyncByteSource`,
  `AsyncStorageProvider` / `AsyncObjectWriter`, `AsyncStreamingValidator`,
  `UploadContext`, and `UploadPolicy.async_validators`.
- Async after-upload hooks support awaitable callables and Celery-like `.delay`.

## 0.1.0 — 2026-08-02

- Initial public release of UploadKit Core.
- `Uploader`, `UploadPolicy`, `UploadResult`, storage/file/validator protocols, after-upload hooks, and exception hierarchy.
