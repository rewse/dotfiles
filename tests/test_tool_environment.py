"""Regression tests for keeping tool secrets out of the shell environment."""

import os
import pathlib
import subprocess
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TESLAMATE_SCRIPTS = REPO_ROOT / "dot_agents/skills/teslamate/scripts"

# Records its arguments and answers like curl -o FILE -w '%{http_code}'.
FAKE_CURL = """\
#!/usr/bin/env bash
printf '%s\\n' "$@" > "${FAKE_LOG}"
out=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o) out="$2"; shift ;;
    --data-binary) cat > /dev/null ;;
  esac
  shift
done
if [[ -n "${out}" ]]; then
  printf '{}' > "${out}"
  printf '200'
else
  printf '{"results": {"A": {"frames": []}}}'
fi
"""


def write_executable(path: pathlib.Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


class ToolEnvironmentTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = pathlib.Path(temporary_directory.name)
        self.config = self.root / "config"
        (self.config / "environment").mkdir(parents=True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "curl.log"
        self.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("TESLAMATE_")
        }
        self.env.update(
            FAKE_LOG=str(self.log),
            HOME=str(self.root / "home"),
            PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            XDG_CONFIG_HOME=str(self.config),
        )

    def write_environment(self, name: str, content: str) -> None:
        (self.config / "environment" / name).write_text(content)

    def run_script(self, *command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            env=self.env,
            stdin=subprocess.DEVNULL,
            check=False,
        )

    def test_teslamate_scripts_read_their_environment_file(self) -> None:
        write_executable(self.bin / "curl", FAKE_CURL)
        self.write_environment(
            "teslamate.sh",
            'export TESLAMATE_GRAFANA_TOKEN="test-token"\n'
            'export TESLAMATE_GRAFANA_URL="https://grafana.invalid"\n',
        )
        for script, argument, url in (
            ("api.sh", "/api/search", "https://grafana.invalid/api/search"),
            ("query.sh", "SELECT 1", "https://grafana.invalid/api/ds/query"),
        ):
            with self.subTest(script=script):
                result = self.run_script(
                    "bash", str(TESLAMATE_SCRIPTS / script), argument
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                arguments = self.log.read_text().splitlines()
                self.assertIn("Authorization: Bearer test-token", arguments)
                self.assertEqual(arguments[-1], url)

    def test_teslamate_scripts_fail_without_their_environment_file(self) -> None:
        write_executable(self.bin / "curl", FAKE_CURL)
        for script in ("api.sh", "query.sh"):
            with self.subTest(script=script):
                result = self.run_script(
                    "bash", str(TESLAMATE_SCRIPTS / script), "/api/search"
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn("is not set", result.stderr)
                self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
