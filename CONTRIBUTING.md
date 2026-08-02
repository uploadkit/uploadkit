# Contributing

Thank you for contributing to UploadKit Core.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
coverage run -m pytest
coverage report -m --include='src/*'
```

## Guidelines

- Keep Core free of framework and storage SDK dependencies.
- Extend via public protocols (`Validator`, `StorageProvider`, `UploadableFile`).
- Do not add concrete security validators or media-specific policies here.
- Prefer small, focused pull requests with tests.
