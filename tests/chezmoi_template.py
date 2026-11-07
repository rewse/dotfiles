"""Renders chezmoi templates for tests independently of the user's config."""

import json
import pathlib
import subprocess
import tempfile
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def execute_template(
    template: str, chezmoi_data: dict[str, Any]
) -> subprocess.CompletedProcess[str]:
    """Runs `chezmoi execute-template` with .chezmoi overridden by chezmoi_data.

    chezmoi panics when --override-data meets a config without a data section,
    so the template renders against a throwaway config that has an empty one.
    """
    with tempfile.TemporaryDirectory() as config_dir:
        config = pathlib.Path(config_dir) / "chezmoi.yaml"
        config.write_text("data: {}\n")
        return subprocess.run(
            [
                "env",
                "-u",
                "OP_SERVICE_ACCOUNT_TOKEN",
                "chezmoi",
                "execute-template",
                "--config",
                str(config),
                "--override-data",
                json.dumps({"chezmoi": chezmoi_data}),
            ],
            cwd=REPO_ROOT,
            input=template,
            capture_output=True,
            check=False,
            text=True,
        )
