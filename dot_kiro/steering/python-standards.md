# Python Standards

## Dependency Management

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
chmod +x script.py
./script.py
# or
uv run script.py
```

#### Benefits

- Self-contained: Dependencies are declared in the script itself
- Automatic installation: `uv` handles dependency installation automatically
- No virtual environment setup needed
- Portable across different environments

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

#### Benefits

- Projects with multiple Python files
- Shared dependencies across multiple scripts
- Projects requiring development dependencies (testing, linting, etc.)

#### Testing

You MUST execute tests using `uv run` with `PYTHONPATH=src`.

Example: `PYTHONPATH=src uv run pytest tests/test_foo.py`

#### Troubleshooting

If `ModuleNotFoundError` occurs, you MUST retry the execution.
