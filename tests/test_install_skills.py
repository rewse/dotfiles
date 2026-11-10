"""Regression tests for run_install-skills.sh, run against fake commands."""

import pathlib
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALL_SKILLS = REPO_ROOT / "run_install-skills.sh"

CLEAN_REQUIREMENTS = """\
# Install / see https://pip.pypa.io/ for details
PyYAML>=6.0
python-pptx>=0.6.21  # docs at https://python-pptx.readthedocs.io
numpy>=1.20.0; python_version >= "3.9"
#   pip install rapidocr onnxruntime
# rapidocr>=3.0
"""

# Writes each call as one line of unit-separated fields, the command name first.
FAKE_LOGGER = """\
#!/bin/sh
{ printf '%s' "${0##*/}"; for a in "$@"; do printf '\\037%s' "$a"; done
  echo; } >> "$FAKE_CALLS"
"""


class InstallSkillsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp(dir="/var/tmp")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / "home"
        self.requirements = self.home / ".agents/skills/ppt-master/requirements.txt"
        self.requirements.parent.mkdir(parents=True)
        self.requirements.write_text(CLEAN_REQUIREMENTS)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.calls = self.tmp / "calls"
        for name in ("skills", "uv"):
            self.write_executable(name, FAKE_LOGGER)
        # Linux skips the darwin-only checks for agent-desktop and officecli.
        self.write_executable("uname", "#!/bin/sh\necho Linux\n")

    def write_executable(self, name: str, content: str) -> None:
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def run_script(self) -> tuple[subprocess.CompletedProcess[str], list[list[str]]]:
        env = {
            "FAKE_CALLS": str(self.calls),
            "HOME": str(self.home),
            "PATH": f"{self.bin}:/usr/bin:/bin",
        }
        result = subprocess.run(
            ["/bin/bash", str(INSTALL_SKILLS)],
            capture_output=True,
            text=True,
            env=env,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        lines = self.calls.read_text().splitlines() if self.calls.exists() else []
        calls = [line.split("\x1f") for line in lines]
        return result, calls

    @staticmethod
    def pip_installs(calls: list[list[str]]) -> list[list[str]]:
        return [call for call in calls if call[:3] == ["uv", "pip", "install"]]

    def test_ppt_master_requirements_install_wheels_only(self) -> None:
        result, calls = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        (install,) = self.pip_installs(calls)
        self.assertIn("--no-build", install)
        self.assertEqual(install[-2:], ["-r", str(self.requirements)])

    def test_ppt_master_requirements_must_name_packages_only(self) -> None:
        unsafe = [
            "--index-url https://a.example/simple",
            "  --extra-index-url=https://b.example/simple",
            "-i https://c.example/simple",
            "-r other.txt",
            "-c constraints.txt",
            "-e .",
            "foo>=1 --find-links wheels",
            "foo @ https://d.example/foo-1.0-py3-none-any.whl",
            "foo@file:///tmp/foo",
            "git+https://github.com/o/r",
            # pip joins a continued line, so the option still applies to foo.
            "--extra-index-url=https://e.example/simple",
        ]
        self.requirements.write_text(
            CLEAN_REQUIREMENTS + "\n".join(unsafe[:-1]) + "\nfoo \\\n" + unsafe[-1]
        )
        result, calls = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("ppt-master requirements", result.stderr)
        self.assertFalse(self.pip_installs(calls))
        # grep -n reports each offending line as NUMBER:LINE.
        reported = [line.partition(":")[2] for line in result.stderr.splitlines()]
        for line in unsafe:
            with self.subTest(line=line):
                self.assertIn(line, reported)


if __name__ == "__main__":
    unittest.main()
