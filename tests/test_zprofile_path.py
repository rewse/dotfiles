#!/usr/bin/env python3
"""Regression tests for zsh startup-file responsibilities."""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ZPROFILE = REPO_ROOT / "dot_zprofile.tmpl"
ZSHENV = REPO_ROOT / "dot_zshenv.tmpl"
ZSHRC = REPO_ROOT / "dot_zshrc.tmpl"


class ZshStartupTest(unittest.TestCase):
    def test_environment_variables_are_loaded_for_every_zsh(self) -> None:
        zprofile = ZPROFILE.read_text()
        zshenv = ZSHENV.read_text()
        zshrc = ZSHRC.read_text()

        for variable in (
            "ANSIBLE_HOME",
            "DOTNET_CLI_HOME",
            "EDITOR",
            "INPUTRC",
            "IPYTHONDIR",
            "JUPYTER_CONFIG_DIR",
            "LANG",
            "NODE_PATH",
            "NPM_CONFIG_USERCONFIG",
            "PAGER",
        ):
            with self.subTest(variable=variable):
                self.assertIn(variable, zshenv)
                self.assertNotIn(variable, zprofile)

        self.assertNotIn("GITHUB_TOKEN", zprofile + zshenv + zshrc)
        self.assertIn("GITLAB_TOKEN", zshrc)
        self.assertNotIn("GITLAB_TOKEN", zprofile + zshenv)

    def test_zshenv_sections_follow_dependency_order(self) -> None:
        template = ZSHENV.read_text()
        sections = (
            "# XDG Base Directory specification",
            "# Shell defaults",
            "# Tool environment",
            "# External cache environment",
            "# Path configuration",
            "# Pager selection",
        )

        positions = []
        for section in sections:
            with self.subTest(section=section):
                self.assertIn(section, template)
                positions.append(template.index(section))

        self.assertEqual(positions, sorted(positions))

    def test_zshrc_sections_follow_dependency_order(self) -> None:
        template = ZSHRC.read_text()
        sections = (
            "# <<< Pre Block",
            "# <<< Environment Variables",
            "# <<< Shell Options",
            "# <<< History Configuration",
            "# <<< Completion and Plugins",
            "# <<< Key Bindings",
            "# <<< Prompt Configuration",
            "# <<< Terminal Integration",
            "# <<< Aliases",
            "# <<< Safe-chain Initialization",
            "# <<< Midway Key Check",
            "# <<< Post Block",
            "# >>> otty shell integration >>>",
        )

        positions = []
        for section in sections:
            with self.subTest(section=section):
                self.assertIn(section, template)
                positions.append(template.index(section))

        self.assertEqual(positions, sorted(positions))

    def test_alias_groups_are_alphabetical(self) -> None:
        template = ZSHRC.read_text()
        aliases = template[
            template.index("# <<< Aliases") : template.index(
                "# <<< Safe-chain Initialization"
            )
        ]
        groups = (
            "# 1Password CLI",
            "# bat aliases",
            "# chezmoi",
            "# Claude code",
            "# Codex CLI",
            "# Disk usage",
            "# Editor",
            "# GNU Coreutils",
            "# Grep with color",
            "# History",
            "# Kiro CLI",
            "# ls aliases",
            "# Navigation",
            "# Safe operations",
        )

        positions = [aliases.index(group) for group in groups]
        self.assertEqual(positions, sorted(positions))

    def test_path_is_a_unique_array_without_string_exports(self) -> None:
        template = ZSHENV.read_text()

        self.assertIn("typeset -U path", template)
        self.assertNotIn("export PATH=", template)

    def test_all_managed_paths_use_array_operations(self) -> None:
        template = ZSHENV.read_text()

        for line in (
            'path=("${HOME}/bin" $path)',
            'path=("${HOME}/.local/bin" $path)',
            'path+=("${DOTNET_CLI_HOME}/tools")',
            'path+=("${HOME}/.lmstudio/bin")',
            'path+=("/Applications/Obsidian.app/Contents/MacOS")',
            'path=("${HOME}/.aim/mcp-servers" $path)',
            'path=("${HOME}/.toolbox/bin" $path)',
        ):
            with self.subTest(line=line):
                self.assertIn(line, template)

    def test_wrapper_precedence_is_restored_after_kiro_post_hook(self) -> None:
        zprofile = ZPROFILE.read_text()
        zshenv = ZSHENV.read_text()

        self.assertIn('path=("${HOME}/.local/bin" $path)', zshenv)
        self.assertIn('eval "$(/opt/homebrew/bin/brew shellenv)"', zshenv)

        post_hook = zprofile.index("zprofile.post.zsh")
        final_local = zprofile.index('path=("${HOME}/.local/bin" $path)')
        self.assertLess(post_hook, final_local)


if __name__ == "__main__":
    unittest.main()
