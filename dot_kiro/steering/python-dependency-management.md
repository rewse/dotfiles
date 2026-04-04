---
inclusion: always
---

# Python Dependency Management

**Do**

- Use inline script metadata with `uv run` for standalone scripts
- Use `pyproject.toml` with `uv` for multi-file projects

**Don't**

- Use `pip install` or `requirements.txt`
- Use `venv` or `virtualenv` directly

### Inline Script Dependencies (Recommended)

For Python scripts that need external dependencies, use inline script metadata with `uv run`. This approach ensures scripts are self-contained and dependencies are automatically managed.

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

#### Usage

```bash
uv run script.py
# or with shebang
./script.py
```

### Project-based Dependencies

For larger projects with multiple scripts and modules, use `pyproject.toml` to manage dependencies.

```bash
cd your-project
uv init                  # Create pyproject.toml
uv add pyyaml requests   # Add dependencies
uv run python script.py  # Run scripts
```

```toml
[project.scripts]
my-command = "my_package.cli:main"

[build-system]
build-backend = "uv_build"

[tool.uv.build-backend]
module-root = "src"
```

#### When to Use

- Projects with multiple Python files
- Shared dependencies across multiple scripts
- Projects requiring development dependencies (testing, linting, etc.)

#### Testing

Execute tests using `uv run` with `PYTHONPATH=src`. The `src` layout requires this so Python can resolve modules under `src/` during test execution.

Example: `PYTHONPATH=src uv run pytest tests/test_foo.py`

