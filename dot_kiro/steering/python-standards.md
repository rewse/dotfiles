# Python Standards

## Build System

You MUST use `uv` as the build system for Python projects.

When running console scripts with `uv run <command>` in projects using the `src` layout, you MUST add the following configuration to `pyproject.toml`:

```toml
[project.scripts]
my-command = "my_package.cli:main"

[build-system]
build-backend = "uv_build"

[tool.uv.build-backend]
module-root = "src"
```

### Troubleshooting

If `ModuleNotFoundError` occurs, you MUST retry the execution.

## Dependency Management

For Python scripts that need external dependencies, use inline script metadata with `uv run`.

```python
#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "pyyaml",
#   "requests",
# ]
# ///

import yaml
import requests

# Your script code here
```

**Usage:**

```bash
chmod +x script.py
./script.py
# or
uv run script.py
```

## Testing

You MUST execute tests using `uv run`.

Example: `PYTHONPATH=src uv run pytest tests/test_foo.py`
