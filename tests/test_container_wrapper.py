#!/usr/bin/env python3
"""Regression tests for the ExternalHD-backed Apple container wrapper."""

import os
import pathlib
import subprocess
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WRAPPER = REPO_ROOT / "dot_local" / "bin" / "executable_container.tmpl"
ZPROFILE = REPO_ROOT / "dot_zprofile.tmpl"


class ContainerWrapperTest(unittest.TestCase):
    def render(self, path: pathlib.Path) -> str:
        result = subprocess.run(
            ["env", "-u", "OP_SERVICE_ACCOUNT_TOKEN", "chezmoi", "execute-template"],
            cwd=REPO_ROOT,
            input=path.read_text(),
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    @staticmethod
    def write_executable(path: pathlib.Path, content: str) -> None:
        path.write_text(content)
        path.chmod(0o755)

    def run_wrapper(
        self,
        arguments: list[str],
        *,
        external_root: str | None = "",
        running_app_root: str | None = None,
        status_field: str = "appRoot",
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        root = pathlib.Path(temporary_directory.name)
        home = root / "home"
        home.mkdir()
        cache_environment = home / ".config" / "environment" / "cache.sh"
        cache_environment.parent.mkdir(parents=True)
        if external_root == "":
            external_root = str(
                root / "ExternalHD" / "Library" / "Application Support" / "com.apple.container"
            )
            pathlib.Path(external_root).mkdir(parents=True)
        if external_root is None:
            cache_environment.write_text("unset CONTAINER_APP_ROOT\n")
        else:
            cache_environment.write_text(f'export CONTAINER_APP_ROOT="{external_root}"\n')

        calls = root / "calls"
        real_container = root / "real-container"
        self.write_executable(
            real_container,
            "#!/bin/sh\n"
            "if [ \"${1:-}\" = system ] && [ \"${2:-}\" = status ]; then\n"
            "  [ -n \"${RUNNING_APP_ROOT:-}\" ] || exit 1\n"
            "  printf 'FIELD VALUE\\n%s %s\\n' \"$STATUS_FIELD\" \"$RUNNING_APP_ROOT\"\n"
            "  exit 0\n"
            "fi\n"
            "printf '%s\\000' \"$@\" >> \"$CONTAINER_CALLS\"\n",
        )
        wrapper = root / "container"
        rendered = self.render(WRAPPER)
        rendered = rendered.replace("/Users/tats", str(home)).replace(
            "/opt/homebrew/bin/container", str(real_container)
        )
        self.write_executable(wrapper, rendered)
        environment = os.environ.copy()
        environment.update(
            {
                "CONTAINER_CALLS": str(calls),
                "RUNNING_APP_ROOT": running_app_root or "",
                "STATUS_FIELD": status_field,
            }
        )
        result = subprocess.run(
            [str(wrapper), *arguments],
            capture_output=True,
            check=False,
            env=environment,
            text=True,
        )
        actual = []
        if calls.exists():
            actual = [value.decode() for value in calls.read_bytes().split(b"\0") if value]
        return result, actual

    def test_injects_external_app_root_for_default_start(self) -> None:
        result, arguments = self.run_wrapper(["system", "start", "--debug"])

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(arguments[:-1], ["system", "start", "--debug", "--app-root"])
        self.assertTrue(
            arguments[-1].endswith(
                "/ExternalHD/Library/Application Support/com.apple.container"
            )
        )

    def test_refuses_default_start_without_external_root(self) -> None:
        result, arguments = self.run_wrapper(["system", "start"], external_root=None)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(arguments, [])
        self.assertIn("ExternalHD", result.stderr)

    def test_preserves_explicit_app_root_and_informational_options(self) -> None:
        for arguments in (
            ["system", "start", "--app-root", "/custom/root"],
            ["system", "start", "--app-root=/custom/root"],
            ["system", "start", "-a", "/custom/root"],
            ["system", "start", "--help"],
            ["system", "start", "--version"],
        ):
            with self.subTest(arguments=arguments):
                result, actual = self.run_wrapper(arguments, external_root=None)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(actual, arguments)

    def test_passes_other_commands_through(self) -> None:
        result, arguments = self.run_wrapper(["image", "list", "--quiet"])

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(arguments, ["image", "list", "--quiet"])

    def test_running_service_accepts_old_and_new_root_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            app_root = pathlib.Path(temporary_directory) / "app-root"
            app_root.mkdir()
            for field in ("appRoot", "paths.appRoot"):
                with self.subTest(field=field):
                    result, arguments = self.run_wrapper(
                        ["system", "start"],
                        external_root=str(app_root),
                        running_app_root=f"{app_root}/",
                        status_field=field,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(arguments[-2:], ["--app-root", str(app_root)])

    def test_running_service_rejects_mismatch_or_missing_field(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            app_root = pathlib.Path(temporary_directory) / "app-root"
            app_root.mkdir()
            for field, message in (("appRoot", "already uses"), ("unknown", "determine")):
                with self.subTest(field=field):
                    result, arguments = self.run_wrapper(
                        ["system", "start"],
                        external_root=str(app_root),
                        running_app_root="/different/root/",
                        status_field=field,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(arguments, [])
                    self.assertIn(message, result.stderr)

    def test_local_bin_precedes_homebrew_after_kiro_post_hook(self) -> None:
        template = ZPROFILE.read_text()
        post_hook = template.index("zprofile.post.zsh")
        local_precedence = template.rindex('path=("${HOME}/.local/bin" $path)')

        self.assertLess(post_hook, local_precedence)


if __name__ == "__main__":
    unittest.main()
