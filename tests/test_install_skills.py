"""Regression tests for run_install-skills.sh, run against fake commands."""

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.parse

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALL_SKILLS = REPO_ROOT / "run_install-skills.sh"
JQ = shutil.which("jq")

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

# Answers `gh api` from canned JSON per repository and applies --jq with the
# real jq, so the script's filter is exercised too. Each repository's default
# branch is "trunk", whose activity is a fresh push, a branch deletion and a
# zero SHA that must be skipped, the aged merge, and an older push.
FAKE_GH = """\
#!{python}
import datetime, hashlib, json, os, subprocess, sys
args = sys.argv[1:]
with open(os.environ["FAKE_CALLS"], "a") as f:
    f.write("\\x1f".join(["gh", *args]) + "\\n")
if args[:1] != ["api"]:
    sys.exit(1)
path = args[1].split("?", 1)[0]
parts = path.split("/")
if parts[:1] != ["repos"] or len(parts) not in (3, 4):
    sys.exit(1)
repo = "/".join(parts[1:3])
behaviour = json.loads(os.environ.get("FAKE_GH", "{{}}")).get(repo)
if behaviour == "fail":
    print("gh: HTTP 502", file=sys.stderr)
    sys.exit(1)
now = datetime.datetime.now(datetime.UTC)
def at(days):
    return (now - datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
def sha(label):
    return hashlib.sha1(f"{{label}}:{{repo}}".encode()).hexdigest()
def activity(kind, days, after):
    return {{"activity_type": kind, "ref": "refs/heads/trunk",
            "timestamp": at(days), "after": after}}
if len(parts) == 3:
    body = {{"default_branch": "trunk"}}
elif parts[3] != "activity":
    sys.exit(1)
elif behaviour == "empty":
    body = []
elif behaviour == "fresh-only":
    body = [activity("push", 1, sha("fresh"))]
elif behaviour == "bad-sha":
    body = [activity("push", 5, "null")]
else:
    body = [
        activity("push", 1, sha("fresh")),
        activity("branch_deletion", 4.5, "0" * 40),
        activity("force_push", 4.6, "0" * 40),
        activity("pr_merge", 5, sha("aged")),
        activity("push", 9, sha("older")),
    ]
text = json.dumps(body)
if "--jq" in args:
    expression = args[args.index("--jq") + 1]
    result = subprocess.run(
        [os.environ["FAKE_JQ"], "-r", expression],
        input=text, capture_output=True, text=True, check=False,
    )
    sys.stdout.write(result.stdout)
    sys.exit(result.returncode)
sys.stdout.write(text)
"""


def aged_commit(repo: str) -> str:
    return hashlib.sha1(f"aged:{repo}".encode()).hexdigest()


@unittest.skipUnless(JQ, "needs jq to evaluate gh --jq filters")
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
        self.write_executable("gh", FAKE_GH.format(python=sys.executable))
        # Linux skips the darwin-only checks for agent-desktop and officecli.
        self.write_executable("uname", "#!/bin/sh\necho Linux\n")

    def write_executable(self, name: str, content: str) -> None:
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def run_script(
        self, gh: dict[str, str] | None = None, script: str | None = None
    ) -> tuple[subprocess.CompletedProcess[str], list[list[str]]]:
        path = INSTALL_SKILLS
        if script is not None:
            path = self.tmp / "install-skills.sh"
            path.write_text(script)
        env = {
            "FAKE_CALLS": str(self.calls),
            "FAKE_GH": json.dumps(gh or {}),
            "FAKE_JQ": str(JQ),
            "HOME": str(self.home),
            "PATH": f"{self.bin}:/usr/bin:/bin",
        }
        result = subprocess.run(
            ["/bin/bash", str(path)],
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
    def skill_adds(calls: list[list[str]]) -> list[list[str]]:
        return [call for call in calls if call[:2] == ["skills", "add"]]

    @staticmethod
    def pip_installs(calls: list[list[str]]) -> list[list[str]]:
        return [call for call in calls if call[:3] == ["uv", "pip", "install"]]

    def test_third_party_skills_install_from_a_commit_past_the_cooldown(
        self,
    ) -> None:
        result, calls = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)

        adds = self.skill_adds(calls)
        sources = {call[2] for call in adds}
        for repo in ("anthropics/skills", "blader/humanizer", "obra/superpowers"):
            with self.subTest(repo=repo):
                self.assertIn(f"{repo}#{aged_commit(repo)}", sources)
        for source in sources:
            with self.subTest(source=source):
                repo, _, commit = source.partition("#")
                self.assertEqual(commit, aged_commit(repo))

        lookups = [
            urllib.parse.urlsplit(call[2])
            for call in calls
            if call[0] == "gh" and call[2].split("?", 1)[0].endswith("/activity")
        ]
        self.assertTrue(lookups)
        for endpoint in lookups:
            with self.subTest(endpoint=endpoint):
                # GitHub records when the branch moved; a commit date is
                # whatever the publisher wrote.
                self.assertRegex(endpoint.path, r"^repos/[\w.-]+/[\w.-]+/activity$")
                query = urllib.parse.parse_qs(endpoint.query)
                self.assertEqual(query["ref"], ["refs/heads/trunk"])
                self.assertEqual(query["per_page"], ["100"])
        self.assertFalse(
            [call for call in calls if call[0] == "gh" and "/commits" in call[2]]
        )

    def test_claude_only_skills_use_the_same_commit(self) -> None:
        self.write_executable("claude", "#!/bin/sh\nexit 0\n")
        _, calls = self.run_script()
        source = f"anthropics/skills#{aged_commit('anthropics/skills')}"
        self.assertIn(
            ["skills", "add", source, "--skill", "pdf", "-g", "--agent", "claude-code"]
            + ["-y"],
            self.skill_adds(calls),
        )

    def test_own_repositories_track_their_default_branch(self) -> None:
        script = INSTALL_SKILLS.read_text().replace(
            "install_skills blader/humanizer humanizer",
            "install_skills rewse/humanizer humanizer",
        )
        self.assertIn("rewse/humanizer", script)
        _, calls = self.run_script(script=script)
        self.assertIn("rewse/humanizer", [call[2] for call in self.skill_adds(calls)])
        self.assertFalse(
            [call for call in calls if call[0] == "gh" and "rewse/" in call[2]]
        )

    def test_keeps_installed_skills_when_no_aged_commit_resolves(self) -> None:
        for behaviour in ("bad-sha", "empty", "fail", "fresh-only"):
            with self.subTest(behaviour=behaviour):
                self.calls.unlink(missing_ok=True)
                result, calls = self.run_script(gh={"blader/humanizer": behaviour})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Warning", result.stderr)
                self.assertIn("blader/humanizer", result.stderr)
                sources = [call[2] for call in self.skill_adds(calls)]
                self.assertFalse([s for s in sources if s.startswith("blader/")])
                self.assertIn(
                    f"obra/superpowers#{aged_commit('obra/superpowers')}", sources
                )

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
