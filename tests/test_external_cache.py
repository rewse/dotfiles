#!/usr/bin/env python3
"""Regression tests for externally stored cache configuration."""

import os
import pathlib
import subprocess
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE_ENV = REPO_ROOT / "dot_config" / "environment" / "cache.sh.tmpl"
CREATE_DIRS = REPO_ROOT / "run_before_create-external-cache-dirs.sh.tmpl"
ZSHENV = REPO_ROOT / "dot_zshenv.tmpl"
EXPECTED_UUID = "1C3ED642-8FFD-43BF-BF08-9CB49AF76676"

EXPECTED_EXPORTS = {
    'export HOMEBREW_CACHE="/Volumes/ExternalHD/Library/Caches/Homebrew"',
    'export RESTIC_CACHE_DIR="/Volumes/ExternalHD/Library/Caches/restic"',
    'export UV_CACHE_DIR="/Volumes/ExternalHD/.cache/uv"',
}


class ExternalCacheConfigurationTest(unittest.TestCase):
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

    def write_mount_command(
        self, path: pathlib.Path, mount_point: pathlib.Path | None
    ) -> None:
        output = "" if mount_point is None else f"/dev/mock on {mount_point} (apfs, local)\n"
        self.write_executable(path, f"#!/bin/sh\nprintf '%s' '{output}'\n")

    def write_identity_commands(
        self,
        diskutil: pathlib.Path,
        plutil: pathlib.Path,
        volume_uuid: str,
    ) -> None:
        self.write_executable(diskutil, "#!/bin/sh\necho '<plist/>'\n")
        self.write_executable(
            plutil,
            "#!/bin/sh\n"
            "cat >/dev/null\n"
            f"printf '%s\\n' '{volume_uuid}'\n",
        )

    def test_cache_environment_exports_approved_paths(self) -> None:
        template = CACHE_ENV.read_text()

        self.assertIn(
            "Shared by zsh and launchd bash jobs to keep cache paths in one place.",
            template,
        )
        self.assertIn(EXPECTED_UUID, template)
        for export in EXPECTED_EXPORTS:
            self.assertIn(export, template)

    def test_cache_environment_requires_mount_and_expected_uuid(self) -> None:
        rendered = self.render(CACHE_ENV)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = pathlib.Path(temporary_directory)
            cache_environment = root / "cache.sh"
            diskutil = root / "diskutil"
            mount_command = root / "mount"
            plutil = root / "plutil"
            environment = os.environ.copy()
            environment.update(
                {
                    "HOMEBREW_CACHE": "stale",
                    "RESTIC_CACHE_DIR": "stale",
                    "UV_CACHE_DIR": "stale",
                }
            )
            command = (
                '. "$1"; printf "%s\\n" "${HOMEBREW_CACHE-unset}" '
                '"${RESTIC_CACHE_DIR-unset}" "${UV_CACHE_DIR-unset}"'
            )

            for mounted, volume_uuid, expected in (
                (False, EXPECTED_UUID, ["unset", "unset", "unset"]),
                (True, "unexpected", ["unset", "unset", "unset"]),
                (
                    True,
                    EXPECTED_UUID,
                    [
                        "/Volumes/ExternalHD/Library/Caches/Homebrew",
                        "/Volumes/ExternalHD/Library/Caches/restic",
                        "/Volumes/ExternalHD/.cache/uv",
                    ],
                ),
            ):
                with self.subTest(mounted=mounted, volume_uuid=volume_uuid):
                    self.write_mount_command(
                        mount_command,
                        pathlib.Path("/Volumes/ExternalHD") if mounted else None,
                    )
                    self.write_identity_commands(diskutil, plutil, volume_uuid)
                    cache_environment.write_text(
                        rendered.replace("/sbin/mount", str(mount_command))
                        .replace("/usr/sbin/diskutil", str(diskutil))
                        .replace("/usr/bin/plutil", str(plutil))
                    )
                    result = subprocess.run(
                        ["/bin/sh", "-c", command, "sh", str(cache_environment)],
                        capture_output=True,
                        check=False,
                        env=environment,
                        text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout.splitlines(), expected)

    def test_zshenv_sources_cache_environment(self) -> None:
        template = ZSHENV.read_text()

        self.assertIn('${XDG_CONFIG_HOME}/environment/cache.sh', template)
        self.assertIn('source "${cache_environment}"', template)

    def test_run_before_requires_identity_and_sets_restrictive_mode_bits(self) -> None:
        rendered = self.render(CREATE_DIRS)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = pathlib.Path(temporary_directory)
            volume = root / "ExternalHD"
            volume.mkdir()
            diskutil = root / "diskutil"
            mount_command = root / "mount"
            plutil = root / "plutil"
            script = root / "create-dirs.sh"
            rewritten = (
                rendered.replace("/Volumes/ExternalHD", str(volume))
                .replace("/sbin/mount", str(mount_command))
                .replace("/usr/sbin/diskutil", str(diskutil))
                .replace("/usr/bin/plutil", str(plutil))
            )
            script.write_text(rewritten)
            script.chmod(0o755)

            self.write_mount_command(mount_command, None)
            self.write_identity_commands(diskutil, plutil, EXPECTED_UUID)
            unmounted = subprocess.run([str(script)], capture_output=True, check=False, text=True)
            self.assertNotEqual(unmounted.returncode, 0)
            self.assertFalse((volume / ".cache" / "uv").exists())

            self.write_mount_command(mount_command, volume)
            self.write_identity_commands(diskutil, plutil, "unexpected")
            wrong_uuid = subprocess.run(
                [str(script)], capture_output=True, check=False, text=True
            )
            self.assertNotEqual(wrong_uuid.returncode, 0)
            self.assertFalse((volume / ".cache" / "uv").exists())

            self.write_identity_commands(diskutil, plutil, EXPECTED_UUID)
            mounted = subprocess.run([str(script)], capture_output=True, check=False, text=True)
            self.assertEqual(mounted.returncode, 0, mounted.stdout + mounted.stderr)
            for relative_path in (
                ".cache/uv",
                "Library/Caches/Homebrew",
                "Library/Caches/restic",
            ):
                path = volume / relative_path
                self.assertTrue(path.is_dir())
                self.assertEqual(path.stat().st_mode & 0o777, 0o700)


if __name__ == "__main__":
    unittest.main()
