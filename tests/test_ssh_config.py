"""Regression tests for the SSH client configuration."""

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tests import chezmoi_template

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SSH_CONFIG = REPO_ROOT / "private_dot_ssh" / "config.tmpl"
SSH = shutil.which("ssh")
ALFA_HOSTS = ("alfa", "alfa.rewse.jp", "alfa-vnc", "alfa-rewse-pg", "alfa-northwind")


class RenderedSshConfig:
    """Renders the config for one host and evaluates it with `ssh -G`.

    The config probes alfa with `nc` in a Match exec. A stub `nc` that exits
    with NC_STUB_EXIT stands in for it, so the result does not depend on the
    network the tests run on.
    """

    def __init__(self, chezmoi_data: dict[str, str]) -> None:
        rendered = chezmoi_template.execute_template(
            SSH_CONFIG.read_text(), chezmoi_data
        )
        if rendered.returncode != 0:
            raise AssertionError(rendered.stderr)
        self.tmp = tempfile.TemporaryDirectory()
        tmp = pathlib.Path(self.tmp.name)
        self.config = tmp / "config"
        self.config.write_text(rendered.stdout)
        nc = tmp / "bin" / "nc"
        nc.parent.mkdir()
        nc.write_text('#!/bin/sh\nexit "$NC_STUB_EXIT"\n')
        nc.chmod(0o755)
        self.path = f"{nc.parent}{os.pathsep}{os.environ['PATH']}"

    def cleanup(self) -> None:
        self.tmp.cleanup()

    def options(self, host: str, name: str, *, reachable: bool = True) -> set[str]:
        assert SSH is not None
        result = subprocess.run(
            [SSH, "-G", "-F", str(self.config), host],
            capture_output=True,
            check=True,
            env={
                **os.environ,
                "NC_STUB_EXIT": "0" if reachable else "1",
                "PATH": self.path,
            },
            text=True,
        )
        return {
            value
            for key, _, value in (
                line.partition(" ") for line in result.stdout.splitlines()
            )
            if key == name
        }


@unittest.skipUnless(SSH and shutil.which("chezmoi"), "needs ssh and chezmoi")
class SshTunnelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rendered = RenderedSshConfig({"os": "darwin", "hostname": "test"})

    @classmethod
    def tearDownClass(cls) -> None:
        cls.rendered.cleanup()

    def options(self, host: str, name: str) -> set[str]:
        return self.rendered.options(host, name)

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


@unittest.skipUnless(SSH and shutil.which("chezmoi"), "needs ssh and chezmoi")
class SshSessionManagerFallbackTest(unittest.TestCase):
    def render(self, chezmoi_data: dict[str, str]) -> RenderedSshConfig:
        rendered = RenderedSshConfig(chezmoi_data)
        self.addCleanup(rendered.cleanup)
        return rendered

    def test_mac_reaches_alfa_directly_when_the_vpn_route_answers(self) -> None:
        rendered = self.render({"os": "darwin", "hostname": "test"})
        for host in ALFA_HOSTS:
            with self.subTest(host=host):
                self.assertEqual(rendered.options(host, "proxycommand"), set())

    def test_mac_falls_back_to_session_manager_away_from_home(self) -> None:
        # alfa is in a private subnet that the internet cannot reach, so
        # Session Manager is the only path when the VPN route is absent.
        rendered = self.render({"os": "darwin", "hostname": "test"})
        for host in ALFA_HOSTS:
            with self.subTest(host=host):
                (command,) = rendered.options(host, "proxycommand", reachable=False)
                args = command.split()
                self.assertEqual(args[:3], ["aws", "ssm", "start-session"])
                self.assertEqual(args[args.index("--profile") + 1], "alfa-ssm")
                self.assertEqual(args[args.index("--region") + 1], "ap-northeast-1")
                self.assertRegex(args[args.index("--target") + 1], r"^i-[0-9a-f]{17}$")
                self.assertEqual(
                    args[args.index("--document-name") + 1], "AWS-StartSSHSession"
                )
                # ssh -G leaves ProxyCommand tokens unexpanded.
                self.assertEqual(args[args.index("--parameters") + 1], "portNumber=%p")

    def test_linux_hosts_never_use_session_manager(self) -> None:
        # The home servers always have the VPN route and no Session Manager
        # plugin.
        rendered = self.render({"os": "linux", "hostname": "fox"})
        for host in ALFA_HOSTS:
            with self.subTest(host=host):
                self.assertEqual(
                    rendered.options(host, "proxycommand", reachable=False), set()
                )


if __name__ == "__main__":
    unittest.main()
