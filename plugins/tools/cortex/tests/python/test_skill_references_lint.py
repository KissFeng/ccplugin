"""Tests for lint rule: skill-references-exists.

SKILL.md / AGENT.md / agents/*.md 引用 references/<name>.md 必须存在.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _helpers import add_paths

add_paths()

import run as lint_run  # noqa: E402


def _rules(findings: list[dict]) -> list[str]:
    return [f["rule"] for f in findings]


class SkillReferencesExistsTest(unittest.TestCase):
    def test_references_link_ok(self):
        """SKILL.md 引用 references/layout.md, 文件存在 → 无 issue."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            skill_dir = root / "skills" / "my-skill"
            (skill_dir / "references").mkdir(parents=True)
            (skill_dir / "references" / "layout.md").write_text(
                "# Layout\n", encoding="utf-8"
            )
            skill_md = skill_dir / "SKILL.md"
            content = "# SKILL\n\n详见 [layout](references/layout.md) §1.\n"
            skill_md.write_text(content, encoding="utf-8")

            findings = lint_run.check_skill_references_exists(
                skill_md,
                "skills/my-skill/SKILL.md",
                content,
            )
            self.assertEqual(findings, [])

    def test_references_link_missing(self):
        """SKILL.md 引用 references/missing.md, 文件不存在 → 1 issue (warn)."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            skill_dir = root / "skills" / "my-skill"
            skill_dir.mkdir(parents=True)
            skill_md = skill_dir / "SKILL.md"
            content = "# SKILL\n\n详见 [missing](references/missing.md).\n"
            skill_md.write_text(content, encoding="utf-8")

            findings = lint_run.check_skill_references_exists(
                skill_md,
                "skills/my-skill/SKILL.md",
                content,
            )
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["rule"], "skill-references-exists")
            self.assertEqual(findings[0]["severity"], "warn")
            self.assertIn("missing.md", findings[0]["msg"])

    def test_external_link_skipped(self):
        """SKILL.md 引用 https:// 链接 → 无 issue (跳过)."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            skill_dir = root / "skills" / "my-skill"
            skill_dir.mkdir(parents=True)
            skill_md = skill_dir / "SKILL.md"
            content = "# SKILL\n\n详见 [github](https://github.com/foo/bar/references/x.md).\n"
            skill_md.write_text(content, encoding="utf-8")

            findings = lint_run.check_skill_references_exists(
                skill_md,
                "skills/my-skill/SKILL.md",
                content,
            )
            self.assertEqual(findings, [])

    def test_non_skill_file_skipped(self):
        """非 SKILL.md / AGENT.md / agents/ 的 markdown → 不检查."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            doc = root / "docs" / "README.md"
            doc.parent.mkdir(parents=True)
            content = "# README\n\n详见 [x](references/missing.md).\n"
            doc.write_text(content, encoding="utf-8")

            findings = lint_run.check_skill_references_exists(
                doc,
                "docs/README.md",
                content,
            )
            self.assertEqual(findings, [])

    def test_agent_md_checked(self):
        """AGENT.md 也走该规则."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plugin_dir = root / "myplugin"
            plugin_dir.mkdir(parents=True)
            agent_md = plugin_dir / "AGENT.md"
            content = "# AGENT\n\n[bad](references/nope.md)\n"
            agent_md.write_text(content, encoding="utf-8")

            findings = lint_run.check_skill_references_exists(
                agent_md,
                "myplugin/AGENT.md",
                content,
            )
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["rule"], "skill-references-exists")

    def test_agents_subdir_md_checked(self):
        """agents/<x>.md 也走该规则."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            agents_dir = root / "agents"
            (agents_dir / "references").mkdir(parents=True)
            (agents_dir / "references" / "ok.md").write_text("ok\n", encoding="utf-8")
            agent_file = agents_dir / "cortex-curator.md"
            content = (
                "# curator\n\n[ok](references/ok.md)\n[bad](references/missing.md)\n"
            )
            agent_file.write_text(content, encoding="utf-8")

            findings = lint_run.check_skill_references_exists(
                agent_file,
                "agents/cortex-curator.md",
                content,
            )
            self.assertEqual(len(findings), 1)
            self.assertIn("missing.md", findings[0]["msg"])


if __name__ == "__main__":
    unittest.main()
