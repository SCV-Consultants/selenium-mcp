---
description: Publish the selenium-mcp package to PyPI
---

# Publish to PyPI

## Prerequisites

- A PyPI account at https://pypi.org
- A PyPI API token (create at https://pypi.org/manage/account/token/)
- The token should be stored securely (e.g. in `~/.pypirc` or as env var)

## Steps

### 1. Activate the virtual environment

```bash
cd /home/mdobrzycki/priv/selenium-mcp
source .venv/bin/activate
```

### 2. Install build dependencies

// turbo
```bash
pip install build twine
```

### 3. Run tests to ensure everything passes

// turbo
```bash
python -m pytest tests/ -v
```

### 4. Run linting

// turbo
```bash
ruff check .
```

### 5. Update version in pyproject.toml

Edit `pyproject.toml` and bump the `version` field under `[project]`.
Use semantic versioning: MAJOR.MINOR.PATCH

Also update `SERVER_VERSION` in `server.py` to match.

### 6. Clean old build artifacts

// turbo
```bash
rm -rf dist/ build/ *.egg-info
```

### 7. Build the distribution

// turbo
```bash
python -m build
```

### 8. Verify the build with twine

// turbo
```bash
twine check dist/*
```

Both the `.whl` and `.tar.gz` should show `PASSED`.

### 9. (Optional) Test upload to TestPyPI first

```bash
twine upload --repository testpypi dist/*
```

Then verify the package at https://test.pypi.org/project/selenium-mcp-server-bidi/

### 10. Upload to PyPI

```bash
twine upload dist/*
```

You will be prompted for credentials:
- **Username**: `__token__`
- **Password**: your PyPI API token (starts with `pypi-`)

Alternatively, configure `~/.pypirc`:
```ini
[pypi]
username = __token__
password = pypi-YOUR-TOKEN-HERE
```

### 11. Verify the published package

// turbo
```bash
pip install selenium-mcp-server-bidi --dry-run
```

## Notes

- The package name on PyPI is `selenium-mcp-server-bidi` (since `selenium-mcp` was already taken)
- You can change the name in `pyproject.toml` → `[project]` → `name` before publishing
- The entry-point `selenium-mcp` will be installed as a CLI command
- Remember to tag the release in git: `git tag v1.0.0 && git push --tags`
