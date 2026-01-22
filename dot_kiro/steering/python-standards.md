---
inclusion: manual
---

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

## Testing

You MUST execute tests using `uv run`.

Example: `PYTHONPATH=src uv run pytest tests/test_foo.py`
