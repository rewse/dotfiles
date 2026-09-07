#!/usr/bin/env python3
"""Regression tests for local fallback cache cleanup."""

import os
import pathlib
import subprocess
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CLEANUP = (
    REPO_ROOT
    / "dot_local"
    / "bin"
    / "executable_cleanup-local-cache-fallbacks.tmpl"
)
IGNORE = REPO_ROOT / ".chezmoiignore"
PLIST = (
    REPO_ROOT
    / "private_Library"
    / "LaunchAgents"
    / "local.cleanup-local-cache-fallbacks.plist.tmpl"
)
RELOAD = REPO_ROOT / "run_onchange_after_reload-local-cache-cleanup.sh.tmpl"
EXPECTED_UUID = "1C3ED642-8FFD-43BF-BF08-9CB49AF76676"


class LocalCacheCleanupTest(unittest.TestCase):
    @staticmethod
    def write_executable(path: pathlib.Path, content: str) -> None:
        path.write_text(content)
        path.chmod(0o755)

    def render(self, path: pathlib.Path, hostname: str = "youth") -> str:
        data = f'{{"chezmoi":{{"hostname":"{hostname}","os":"darwin"}}}}'
        result = subprocess.run(
            [
                "env",
                "-u",
                "OP_SERVICE_ACCOUNT_TOKEN",
                "chezmoi",
                "execute-template",
                "--override-data",
                data,
            ],
            cwd=REPO_ROOT,
            input=path.read_text(),
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def run_cleanup(
        self,
        *,
        mounted: bool = True,
        mount_disappears: bool = False,
        volume_uuid: str = EXPECTED_UUID,
        filesystem_type: str = "apfs",
        missing_destination: str | None = None,
        symlink_destination: str | None = None,
        symlink_local_parent: str | None = None,
        open_cache: str | None = None,
        lsof_failure: bool = False,
        rm_failure: bool = False,
    ) -> tuple[
        subprocess.CompletedProcess[str],
        dict[str, pathlib.Path],
        dict[str, pathlib.Path],
    ]:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        root = pathlib.Path(temporary_directory.name)
        home = root / "home"
        volume = root / "ExternalHD"
        commands = root / "commands"
        commands.mkdir()
        home.mkdir()
        volume.mkdir()

        if symlink_local_parent == "uv":
            redirected_cache = root / "redirected-cache"
            redirected_cache.mkdir()
            (home / ".cache").symlink_to(redirected_cache, target_is_directory=True)

        local_caches = {
            "homebrew": home / "Library" / "Caches" / "Homebrew",
            "restic": home / "Library" / "Caches" / "restic",
            "uv": home / ".cache" / "uv",
        }
        external_caches = {
            "homebrew": volume / "Library" / "Caches" / "Homebrew",
            "restic": volume / "Library" / "Caches" / "restic",
            "uv": volume / ".cache" / "uv",
        }
        for cache in local_caches.values():
            cache.mkdir(parents=True)
            (cache / "fallback-entry").write_text("cache")
        for name, cache in external_caches.items():
            if name == missing_destination or name == symlink_destination:
                continue
            cache.mkdir(parents=True)
            (cache / "external-entry").write_text("keep")
        if symlink_destination is not None:
            redirected_destination = root / "redirected-destination"
            redirected_destination.mkdir()
            external_caches[symlink_destination].parent.mkdir(parents=True, exist_ok=True)
            external_caches[symlink_destination].symlink_to(
                redirected_destination,
                target_is_directory=True,
            )

        mount_output = f"/dev/mock on {volume} (apfs, local)\n"
        if mount_disappears:
            mount_counter = root / "mount-counter"
            self.write_executable(
                commands / "mount",
                "#!/bin/sh\n"
                f"counter={mount_counter!s}\n"
                "count=$(cat \"$counter\" 2>/dev/null || echo 0)\n"
                "count=$((count + 1))\n"
                "echo \"$count\" > \"$counter\"\n"
                f"[ \"$count\" -le 2 ] && printf '%s' '{mount_output}'\n",
            )
        else:
            output = mount_output if mounted else ""
            self.write_executable(
                commands / "mount",
                f"#!/bin/sh\nprintf '%s' '{output}'\n",
            )
        self.write_executable(commands / "diskutil", "#!/bin/sh\necho '<plist/>'\n")
        self.write_executable(
            commands / "plutil",
            "#!/bin/sh\n"
            "cat >/dev/null\n"
            "case \"$*\" in\n"
            f"  *VolumeUUID*) printf '%s\\n' '{volume_uuid}' ;;\n"
            f"  *FilesystemType*) printf '%s\\n' '{filesystem_type}' ;;\n"
            f"  *MountPoint*) printf '%s\\n' '{volume}' ;;\n"
            "esac\n",
        )
        lsof_output = ""
        if open_cache is not None:
            lsof_output = f"p123\nn{local_caches[open_cache]}/active-file\n"
        lsof_exit = 1 if lsof_failure else 0
        self.write_executable(
            commands / "lsof",
            f"#!/bin/sh\nprintf '%s' '{lsof_output}'\nexit {lsof_exit}\n",
        )
        if rm_failure:
            self.write_executable(commands / "rm", "#!/bin/sh\nexit 1\n")
        else:
            self.write_executable(commands / "rm", "#!/bin/sh\nexec /bin/rm \"$@\"\n")

        script = root / "cleanup"
        rewritten = self.render(CLEANUP)
        replacements = {
            "/Users/tats": str(home),
            "/Volumes/ExternalHD": str(volume),
            "/bin/rm": str(commands / "rm"),
            "/sbin/mount": str(commands / "mount"),
            "/usr/bin/plutil": str(commands / "plutil"),
            "/usr/sbin/diskutil": str(commands / "diskutil"),
            "/usr/sbin/lsof": str(commands / "lsof"),
        }
        for source, destination in replacements.items():
            rewritten = rewritten.replace(source, destination)
        self.write_executable(script, rewritten)

        result = subprocess.run(
            [str(script)],
            capture_output=True,
            check=False,
            env=os.environ.copy(),
            text=True,
        )
        return result, local_caches, external_caches

    def test_does_nothing_when_external_hd_is_not_mounted(self) -> None:
        result, local_caches, _ = self.run_cleanup(mounted=False)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(all(path.exists() for path in local_caches.values()))

    def test_refuses_cleanup_for_unexpected_volume_identity(self) -> None:
        for field in ("uuid", "filesystem"):
            with self.subTest(field=field):
                arguments = (
                    {"volume_uuid": "unexpected"}
                    if field == "uuid"
                    else {"filesystem_type": "hfs"}
                )
                result, local_caches, _ = self.run_cleanup(**arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("identity mismatch", result.stdout + result.stderr)
                self.assertTrue(all(path.exists() for path in local_caches.values()))

    def test_requires_matching_external_destination(self) -> None:
        result, local_caches, _ = self.run_cleanup(missing_destination="restic")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(local_caches["homebrew"].exists())
        self.assertTrue(local_caches["restic"].exists())
        self.assertFalse(local_caches["uv"].exists())
        self.assertIn("destination missing", result.stdout)

    def test_rejects_symlinked_local_parent_or_external_destination(self) -> None:
        local_result, local_caches, _ = self.run_cleanup(symlink_local_parent="uv")
        external_result, external_locals, _ = self.run_cleanup(
            symlink_destination="restic"
        )

        self.assertNotEqual(local_result.returncode, 0)
        self.assertTrue(local_caches["uv"].exists())
        self.assertIn("symlink", local_result.stdout)
        self.assertNotEqual(external_result.returncode, 0)
        self.assertTrue(external_locals["restic"].exists())
        self.assertIn("symlink", external_result.stdout)

    def test_defers_only_cache_with_open_files(self) -> None:
        result, local_caches, _ = self.run_cleanup(open_cache="uv")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(local_caches["homebrew"].exists())
        self.assertFalse(local_caches["restic"].exists())
        self.assertTrue(local_caches["uv"].exists())
        self.assertIn("in use", result.stdout)

    def test_lsof_failure_is_fail_closed(self) -> None:
        result, local_caches, _ = self.run_cleanup(lsof_failure=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(all(path.exists() for path in local_caches.values()))
        self.assertIn("unable to verify open files", result.stdout)

    def test_mount_loss_before_deletion_is_fail_closed(self) -> None:
        result, local_caches, _ = self.run_cleanup(mount_disappears=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(all(path.exists() for path in local_caches.values()))
        self.assertIn("safety conditions changed", result.stdout)

    def test_rm_failure_is_reported_without_false_success(self) -> None:
        result, local_caches, _ = self.run_cleanup(rm_failure=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(all(path.exists() for path in local_caches.values()))
        self.assertIn("Failed to remove", result.stdout)
        self.assertNotIn("Removed local", result.stdout)

    def test_removes_only_unused_local_fallback_caches(self) -> None:
        result, local_caches, external_caches = self.run_cleanup()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(all(not path.exists() for path in local_caches.values()))
        self.assertTrue(
            all((path / "external-entry").exists() for path in external_caches.values())
        )
        self.assertIn("validation-only and is never deleted", CLEANUP.read_text())
        self.assertIn("cleanup_local_cache", CLEANUP.read_text())
        self.assertIn("Removed", result.stdout)

    def test_launch_agent_runs_at_load_and_on_mount(self) -> None:
        template = PLIST.read_text()

        self.assertIn("<key>RunAtLoad</key>", template)
        self.assertIn("<key>StartOnMount</key>", template)
        self.assertIn("cleanup-local-cache-fallbacks", template)
        self.assertIn("local-cache-cleanup.log", template)

    def test_reload_script_replaces_launch_agent_when_sources_change(self) -> None:
        template = RELOAD.read_text()

        self.assertIn("/bin/launchctl bootout", template)
        self.assertIn("/bin/launchctl bootstrap", template)
        self.assertIn("/usr/bin/id -u", template)
        self.assertIn("sha256sum", template)

    def test_cleanup_is_ignored_on_every_non_target_host(self) -> None:
        youth = self.render(IGNORE, "youth")
        business = self.render(IGNORE, "7cf34ded5d65")
        other = self.render(IGNORE, "other")

        cleanup_path = ".local/bin/cleanup-local-cache-fallbacks"
        self.assertNotIn(cleanup_path, youth)
        self.assertIn(cleanup_path, business)
        self.assertIn(cleanup_path, other)


if __name__ == "__main__":
    unittest.main()
