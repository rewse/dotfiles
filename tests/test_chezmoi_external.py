"""Regression tests for the externally fetched agent resources."""

import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EXTERNAL = REPO_ROOT / "dot_agents/.chezmoiexternal.yaml"


def entries() -> dict[str, dict[str, str]]:
    result = {}
    for block in re.split(
        r"^(?=\S[^\n]*:\n)", EXTERNAL.read_text(), flags=re.MULTILINE
    ):
        if block.startswith("#") or ":\n" not in block:
            continue
        name, body = block.split(":\n", 1)
        entry, parent = {}, ""
        for indent, key, value in re.findall(
            r"^( {2,4})(\w+):(?: (\S.*))?$", body, re.MULTILINE
        ):
            if len(indent) == 2:
                parent = key
            if value:
                entry[f"{parent}.{key}" if len(indent) == 4 else key] = value
        result[name] = entry
    return result


class ChezmoiExternalTest(unittest.TestCase):
    def test_executables_are_pinned_to_a_commit_and_checksum(self) -> None:
        # A hook runs on every agent turn, so a moved branch must not change it.
        executables = {k: v for k, v in entries().items() if v.get("executable")}
        self.assertIn("hooks/japanese-guard.py", executables)
        for name, entry in executables.items():
            with self.subTest(name=name):
                self.assertRegex(
                    entry["url"],
                    r"^https://raw\.githubusercontent\.com/[\w.-]+/[\w.-]+/[0-9a-f]{40}/",
                )
                # YAML reads an unquoted hex digest that starts with digits as a number.
                self.assertRegex(entry.get("checksum.sha256", ""), r'^"[0-9a-f]{64}"$')
                self.assertNotIn("refreshPeriod", entry)


if __name__ == "__main__":
    unittest.main()
