"""Tests for lint rule: frontmatter-required-scores.

知识库 .md 必含 score / confidence / source_credibility / maturity 4 字段;
记忆 .md 必含 importance / confidence 2 字段; 全 0.0-10.0 浮点 (maturity enum).
"""

from __future__ import annotations

import unittest
from pathlib import Path

from _helpers import add_paths

add_paths()

import run as lint_run  # noqa: E402


def _rules(findings: list[dict]) -> list[str]:
    return [f["rule"] for f in findings]


def _msgs(findings: list[dict]) -> str:
    return "\n".join(f["msg"] for f in findings)


KB_PATH = "知识库/项目/foo/bar/x.md"
KB_DOMAIN_PATH = "知识库/领域/技术/x.md"
MEM_L0_PATH = "记忆/L0-核心/价值观.md"
MEM_L1_PATH = "记忆/L1-长期/x.md"


# ---------------- check (validation) ----------------


class CheckTest(unittest.TestCase):
    def test_kb_all_4_fields_ok(self):
        content = (
            "---\n"
            "title: foo\n"
            "score: 7.5\n"
            "confidence: 8.0\n"
            "source_credibility: 9.0\n"
            "maturity: stable\n"
            "---\n\nbody"
        )
        findings = lint_run.check_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertEqual(findings, [])

    def test_kb_missing_score(self):
        content = (
            "---\n"
            "title: foo\n"
            "confidence: 8.0\n"
            "source_credibility: 9.0\n"
            "maturity: stable\n"
            "---\n"
        )
        findings = lint_run.check_frontmatter_required_scores(
            Path(KB_DOMAIN_PATH), content
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("score", _msgs(findings))
        self.assertEqual(findings[0]["rule"], "frontmatter-required-scores")

    def test_kb_missing_confidence(self):
        content = (
            "---\n"
            "score: 5.0\n"
            "source_credibility: 7.0\n"
            "maturity: review\n"
            "---\n"
        )
        findings = lint_run.check_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertTrue(any("confidence" in f["msg"] for f in findings))

    def test_kb_missing_source_credibility(self):
        content = (
            "---\n"
            "score: 5.0\n"
            "confidence: 6.0\n"
            "maturity: draft\n"
            "---\n"
        )
        findings = lint_run.check_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertTrue(any("source_credibility" in f["msg"] for f in findings))

    def test_kb_missing_maturity(self):
        content = (
            "---\n"
            "score: 5.0\n"
            "confidence: 6.0\n"
            "source_credibility: 7.0\n"
            "---\n"
        )
        findings = lint_run.check_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertTrue(any("maturity" in f["msg"] for f in findings))

    def test_kb_score_boundary_10(self):
        content = (
            "---\n"
            "score: 10.0\n"
            "confidence: 10.0\n"
            "source_credibility: 10.0\n"
            "maturity: stable\n"
            "---\n"
        )
        findings = lint_run.check_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertEqual(findings, [])

    def test_kb_score_out_of_range(self):
        content = (
            "---\n"
            "score: 11.5\n"
            "confidence: 8.0\n"
            "source_credibility: 9.0\n"
            "maturity: stable\n"
            "---\n"
        )
        findings = lint_run.check_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertTrue(any("score" in f["msg"] for f in findings))

    def test_kb_score_negative(self):
        content = (
            "---\n"
            "score: -1.0\n"
            "confidence: 8.0\n"
            "source_credibility: 9.0\n"
            "maturity: stable\n"
            "---\n"
        )
        findings = lint_run.check_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertTrue(any("score" in f["msg"] for f in findings))

    def test_kb_score_str_value(self):
        # parse_frontmatter quotes are stripped; emulate raw text with explicit quotes
        content = (
            "---\n"
            'score: "high"\n'
            "confidence: 8.0\n"
            "source_credibility: 9.0\n"
            "maturity: stable\n"
            "---\n"
        )
        findings = lint_run.check_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertTrue(any("score" in f["msg"] for f in findings))

    def test_kb_score_non_numeric_text(self):
        # plain text like 'high' is not a valid number — must flag
        content = (
            "---\n"
            "score: high\n"
            "confidence: 8.0\n"
            "source_credibility: 9.0\n"
            "maturity: stable\n"
            "---\n"
        )
        findings = lint_run.check_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertTrue(any("score" in f["msg"] for f in findings))

    def test_mem_missing_importance(self):
        content = "---\nconfidence: 8.0\n---\n"
        findings = lint_run.check_frontmatter_required_scores(
            Path(MEM_L0_PATH), content
        )
        self.assertTrue(any("importance" in f["msg"] for f in findings))

    def test_mem_missing_confidence(self):
        content = "---\nimportance: 9.0\n---\n"
        findings = lint_run.check_frontmatter_required_scores(
            Path(MEM_L1_PATH), content
        )
        self.assertTrue(any("confidence" in f["msg"] for f in findings))

    def test_mem_2_fields_ok(self):
        content = "---\nimportance: 9.0\nconfidence: 8.0\n---\n"
        findings = lint_run.check_frontmatter_required_scores(
            Path(MEM_L0_PATH), content
        )
        self.assertEqual(findings, [])

    def test_maturity_bad_enum(self):
        content = (
            "---\n"
            "score: 5.0\n"
            "confidence: 5.0\n"
            "source_credibility: 5.0\n"
            "maturity: bad-enum\n"
            "---\n"
        )
        findings = lint_run.check_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertTrue(any("maturity" in f["msg"] for f in findings))

    def test_skip_dashboard(self):
        content = "---\ntitle: foo\n---\n"
        findings = lint_run.check_frontmatter_required_scores(
            Path("仪表盘/foo.md"), content
        )
        self.assertEqual(findings, [])

    def test_skip_inbox(self):
        content = "---\ntitle: foo\n---\n"
        findings = lint_run.check_frontmatter_required_scores(
            Path("知识库/收件箱/x.md"), content
        )
        self.assertEqual(findings, [])

    def test_skip_archive(self):
        content = "---\ntitle: foo\n---\n"
        findings = lint_run.check_frontmatter_required_scores(
            Path("归档/x.md"), content
        )
        self.assertEqual(findings, [])

    def test_skip_meta(self):
        content = "---\ntitle: foo\n---\n"
        findings = lint_run.check_frontmatter_required_scores(
            Path("_meta/version.json.md"), content
        )
        self.assertEqual(findings, [])

    def test_skip_non_kb_non_mem(self):
        content = "---\ntitle: foo\n---\n"
        findings = lint_run.check_frontmatter_required_scores(
            Path("README.md"), content
        )
        self.assertEqual(findings, [])

    def test_skip_no_frontmatter(self):
        content = "# just markdown body, no frontmatter\n"
        findings = lint_run.check_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertEqual(findings, [])

    def test_skip_non_md(self):
        content = "filters:\n  - foo\n"
        findings = lint_run.check_frontmatter_required_scores(
            Path("知识库/项目/foo/x.base"), content
        )
        self.assertEqual(findings, [])


# ---------------- autofix ----------------


class AutofixTest(unittest.TestCase):
    def test_autofix_kb_adds_stubs(self):
        content = "---\ntitle: foo\n---\nbody"
        new = lint_run.autofix_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertIsNotNone(new)
        self.assertIn("score:", new)
        self.assertIn("confidence:", new)
        self.assertIn("source_credibility:", new)
        self.assertIn("maturity: draft", new)
        # body preserved
        self.assertIn("body", new)

    def test_autofix_mem_adds_stubs(self):
        content = "---\ntitle: foo\n---\nbody"
        new = lint_run.autofix_frontmatter_required_scores(Path(MEM_L0_PATH), content)
        self.assertIsNotNone(new)
        self.assertIn("importance:", new)
        self.assertIn("confidence:", new)

    def test_autofix_clamp_high(self):
        content = (
            "---\n"
            "score: 12.0\n"
            "confidence: 8.0\n"
            "source_credibility: 9.0\n"
            "maturity: stable\n"
            "---\nbody"
        )
        new = lint_run.autofix_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertIsNotNone(new)
        self.assertIn("score: 10.0", new)

    def test_autofix_clamp_low(self):
        content = (
            "---\n"
            "score: 5.0\n"
            "confidence: -5.0\n"
            "source_credibility: 9.0\n"
            "maturity: stable\n"
            "---\nbody"
        )
        new = lint_run.autofix_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertIsNotNone(new)
        self.assertIn("confidence: 0.0", new)

    def test_autofix_maturity_bad_enum(self):
        content = (
            "---\n"
            "score: 5.0\n"
            "confidence: 5.0\n"
            "source_credibility: 5.0\n"
            "maturity: bogus\n"
            "---\nbody"
        )
        new = lint_run.autofix_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertIsNotNone(new)
        self.assertIn("maturity: draft", new)

    def test_autofix_str_to_float(self):
        content = (
            "---\n"
            'score: "high"\n'
            "confidence: 8.0\n"
            "source_credibility: 9.0\n"
            "maturity: stable\n"
            "---\nbody"
        )
        new = lint_run.autofix_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertIsNotNone(new)
        self.assertIn("score: 0.0", new)

    def test_autofix_skip_when_ok(self):
        content = (
            "---\n"
            "score: 7.5\n"
            "confidence: 8.0\n"
            "source_credibility: 9.0\n"
            "maturity: stable\n"
            "---\nbody"
        )
        new = lint_run.autofix_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertIsNone(new)

    def test_autofix_skip_dashboard(self):
        content = "---\ntitle: foo\n---\nbody"
        new = lint_run.autofix_frontmatter_required_scores(
            Path("仪表盘/foo.md"), content
        )
        self.assertIsNone(new)

    def test_autofix_skip_no_frontmatter(self):
        content = "no frontmatter here\n"
        new = lint_run.autofix_frontmatter_required_scores(Path(KB_PATH), content)
        self.assertIsNone(new)

    def test_autofix_mem_with_existing_importance(self):
        content = "---\nimportance: 9.0\n---\nbody"
        new = lint_run.autofix_frontmatter_required_scores(Path(MEM_L0_PATH), content)
        self.assertIsNotNone(new)
        self.assertIn("importance: 9.0", new)
        self.assertIn("confidence:", new)


if __name__ == "__main__":
    unittest.main()
