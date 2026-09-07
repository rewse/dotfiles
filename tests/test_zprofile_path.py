#!/usr/bin/env python3
"""Regression tests for zsh path-array configuration."""

import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ZPROFILE = REPO_ROOT / "dot_zprofile.tmpl"


class ZprofilePathTest(unittest.TestCase):
    def test_path_is_a_unique_array_without_string_exports(self) -> None:
        template = ZPROFILE.read_text()

        self.assertIn("typeset -U path", template)
        self.assertNotIn("export PATH=", template)

    def test_all_managed_paths_use_array_operations(self) -> None:
        template = ZPROFILE.read_text()

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
        template = ZPROFILE.read_text()

        first_local = template.index('path=("${HOME}/.local/bin" $path)')
        homebrew = template.index('eval "$(/opt/homebrew/bin/brew shellenv)"')
        post_hook = template.index("zprofile.post.zsh")
        final_local = template.rindex('path=("${HOME}/.local/bin" $path)')

        self.assertLess(first_local, homebrew)
        self.assertLess(homebrew, post_hook)
        self.assertLess(post_hook, final_local)


if __name__ == "__main__":
    unittest.main()
