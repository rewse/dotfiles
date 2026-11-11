"""Regression tests for the SSH client configuration."""

import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tests import chezmoi_template

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SSH_CONFIG = REPO_ROOT / "private_dot_ssh" / "config.tmpl"
SSH = shutil.which("ssh")


@unittest.skipUnless(SSH and shutil.which("chezmoi"), "needs ssh and chezmoi")
class SshTunnelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        rendered = chezmoi_template.execute_template(
            SSH_CONFIG.read_text(), {"os": "darwin", "hostname": "test"}
        )
        if rendered.returncode != 0:
            raise AssertionError(rendered.stderr)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.config = pathlib.Path(cls.tmp.name) / "config"
        cls.config.write_text(rendered.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def options(self, host: str, name: str) -> set[str]:
        assert SSH is not None
        result = subprocess.run(
            [SSH, "-G", "-F", str(self.config), host],
            capture_output=True,
            check=True,
            text=True,
        )
        return {
            value
            for key, _, value in (
                line.partition(" ") for line in result.stdout.splitlines()
            )
            if key == name
        }

    def test_plain_alfa_sessions_forward_nothing(self) -> None:
        # Ansible and ordinary logins would otherwise hold the local ports and
        # make a later tunnel fail with "Address already in use".
        for host in ("alfa", "alfa.rewse.jp"):
            with self.subTest(host=host):
                self.assertEqual(self.options(host, "localforward"), set())

    def test_tunnel_aliases_forward_one_port_each_through_alfa(self) -> None:
        for host, forward in (
            ("alfa-vnc", "5901 [localhost]:5901"),
            ("alfa-rewse-pg", "15432 [rewse-pg.rewse.jp]:5432"),
        ):
            with self.subTest(host=host):
                self.assertEqual(self.options(host, "localforward"), {forward})
                self.assertEqual(self.options(host, "hostname"), {"alfa.rewse.jp"})
                self.assertEqual(self.options(host, "user"), {"tats"})


if __name__ == "__main__":
    unittest.main()
