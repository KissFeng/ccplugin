"""Tests for lint rule #16: vault-structure-violation (lint/run.py + schemas.py)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _helpers import add_paths

add_paths()

import run as lint_run  # noqa: E402
import schemas as lint_schemas  # noqa: E402


def _bare_vault(root: Path, preset: str = "LYT",
                whitelist: list[str] | None = None) -> Path:
    """Build a minimal vault with explicit preset (no localized dirs)."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "_meta").mkdir(exist_ok=True)
    meta: dict = {"preset": preset, "lang": "zh-CN"}
    if whitelist is not None:
        meta["lint_whitelist"] = whitelist
    (root / "_meta" / "version.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8"
    )
    return root


def _structure_violations(vault: Path) -> list[dict]:
    """Run check_vault_structure directly (no subprocess)."""
    preset = lint_run._load_vault_preset(vault)
    whitelist = lint_run._load_lint_whitelist(vault)
    return lint_run.check_vault_structure(vault, preset, whitelist, None)


class SchemasTest(unittest.TestCase):
    def test_schemas_have_all_three_presets(self):
        for key in ("LYT", "PARA", "flat"):
            self.assertIn(key, lint_schemas.SCHEMAS)
            schema = lint_schemas.SCHEMAS[key]
            self.assertIsInstance(schema["root_dirs"], set)
            self.assertIsInstance(schema["root_files"], set)
            self.assertGreater(len(schema["root_dirs"]), 0)

    def test_get_schema_case_insensitive(self):
        self.assertIs(lint_schemas.get_schema("LYT"),
                      lint_schemas.SCHEMAS["LYT"])
        self.assertIs(lint_schemas.get_schema("lyt"),
                      lint_schemas.SCHEMAS["LYT"])
        self.assertIs(lint_schemas.get_schema("para"),
                      lint_schemas.SCHEMAS["PARA"])
        self.assertIs(lint_schemas.get_schema("FLAT"),
                      lint_schemas.SCHEMAS["flat"])

    def test_get_schema_unknown_falls_back_to_lyt(self):
        self.assertIs(lint_schemas.get_schema("nonexistent"),
                      lint_schemas.SCHEMAS["LYT"])
        self.assertIs(lint_schemas.get_schema(None),
                      lint_schemas.SCHEMAS["LYT"])

    def test_hidden_obsidian_dirs_allowed_everywhere(self):
        for key in ("LYT", "PARA", "flat"):
            self.assertIn(".obsidian", lint_schemas.SCHEMAS[key]["root_dirs"])
            self.assertIn(".trash", lint_schemas.SCHEMAS[key]["root_dirs"])


class VaultStructureRuleTest(unittest.TestCase):
    def test_lyt_illegal_dir_and_file_both_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            vault = _bare_vault(Path(d), preset="LYT")
            (vault / "foobar").mkdir()
            (vault / "random.txt").write_text("x", encoding="utf-8")

            violations = _structure_violations(vault)
            rules = {v["rule"] for v in violations}
            self.assertEqual(rules, {"vault-structure-violation"})

            paths = {v["path"] for v in violations}
            self.assertEqual(paths, {"foobar/", "random.txt"})

            kinds = {v["path"]: v["kind"] for v in violations}
            self.assertEqual(kinds["foobar/"], "dir")
            self.assertEqual(kinds["random.txt"], "file")

            # standard finding shape preserved
            for v in violations:
                self.assertEqual(v["severity"], "error")
                self.assertFalse(v["fixable"])
                self.assertIn("msg", v)

    def test_para_preset_known_dirs_pass(self):
        with tempfile.TemporaryDirectory() as d:
            vault = _bare_vault(Path(d), preset="PARA")
            for name in ("1_projects", "2_areas", "3_resources", "4_archives"):
                (vault / name).mkdir()
            (vault / "hot.md").write_text("x", encoding="utf-8")
            (vault / "garbage").mkdir()

            violations = _structure_violations(vault)
            paths = {v["path"] for v in violations}
            self.assertEqual(paths, {"garbage/"})

    def test_flat_preset_known_dirs_pass(self):
        with tempfile.TemporaryDirectory() as d:
            vault = _bare_vault(Path(d), preset="flat")
            (vault / "concepts").mkdir()
            (vault / "domains").mkdir()
            (vault / "weirdo").mkdir()

            violations = _structure_violations(vault)
            paths = {v["path"] for v in violations}
            self.assertEqual(paths, {"weirdo/"})

    def test_whitelist_skips_violation(self):
        with tempfile.TemporaryDirectory() as d:
            vault = _bare_vault(Path(d), preset="LYT",
                                whitelist=["foobar/", "random.txt"])
            (vault / "foobar").mkdir()
            (vault / "random.txt").write_text("x", encoding="utf-8")

            violations = _structure_violations(vault)
            self.assertEqual(violations, [])

    def test_hidden_obsidian_dirs_not_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            vault = _bare_vault(Path(d), preset="LYT")
            (vault / ".obsidian").mkdir()
            (vault / ".trash").mkdir()

            violations = _structure_violations(vault)
            self.assertEqual(violations, [])

    def test_extra_allowed_dirs_locale_passthrough(self):
        """Locale-derived dir names (e.g. 概念) bypass schema strictness."""
        with tempfile.TemporaryDirectory() as d:
            vault = _bare_vault(Path(d), preset="LYT")
            (vault / "概念").mkdir()
            (vault / "foobar").mkdir()

            violations = lint_run.check_vault_structure(
                vault, "LYT", set(), extra_allowed_dirs={"概念"}
            )
            paths = {v["path"] for v in violations}
            self.assertEqual(paths, {"foobar/"})

    def test_missing_preset_defaults_to_lyt(self):
        with tempfile.TemporaryDirectory() as d:
            vault = Path(d)
            (vault / "_meta").mkdir()
            (vault / "_meta" / "version.json").write_text(
                json.dumps({"lang": "zh-CN"}), encoding="utf-8"
            )
            self.assertEqual(lint_run._load_vault_preset(vault), "LYT")
            self.assertEqual(lint_run._load_lint_whitelist(vault), set())


if __name__ == "__main__":
    unittest.main()
