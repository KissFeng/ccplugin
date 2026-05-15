"""Tests for save._patch_hot_project_subpages (P10 R1).

hot.md `## 项目高分页面` 节维护:
- 阈值 score ≥ 7 + maturity in stable/review
- 项目子段 `### host/org/repo` ≤ 3 篇
- 按 score desc 排序保 top
"""
from __future__ import annotations

import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts" / "cli"))

from save import (  # noqa: E402
    _HOT_PROJECT_SECTION,
    _derive_project_key,
    _extract_score_from_line,
    _patch_hot_project_subpages,
)


def _make_hot(tmp_path: Path, body: str = "# hot\n\n## 最近落档\n\n- [[old]]\n") -> Path:
    hot = tmp_path / "hot.md"
    hot.write_text(body, encoding="utf-8")
    return hot


def test_below_score_threshold_skip(tmp_path):
    hot = _make_hot(tmp_path)
    orig = hot.read_text(encoding="utf-8")
    _patch_hot_project_subpages(tmp_path, "github.com/foo/bar", "[[x]]", 6.5, "stable")
    assert hot.read_text(encoding="utf-8") == orig


def test_below_maturity_skip(tmp_path):
    hot = _make_hot(tmp_path)
    orig = hot.read_text(encoding="utf-8")
    _patch_hot_project_subpages(tmp_path, "github.com/foo/bar", "[[x]]", 9.0, "draft")
    assert hot.read_text(encoding="utf-8") == orig


def test_create_section_when_missing(tmp_path):
    hot = _make_hot(tmp_path)
    _patch_hot_project_subpages(tmp_path, "github.com/foo/bar", "[[x]]", 8.0, "stable")
    text = hot.read_text(encoding="utf-8")
    assert _HOT_PROJECT_SECTION in text
    assert "### github.com/foo/bar" in text
    assert "[[x]]" in text
    assert "score: 8.0" in text


def test_create_project_subsection(tmp_path):
    _make_hot(tmp_path, body=f"# hot\n\n{_HOT_PROJECT_SECTION}\n\n")
    _patch_hot_project_subpages(tmp_path, "github.com/foo/bar", "[[x]]", 7.5, "review")
    text = (tmp_path / "hot.md").read_text(encoding="utf-8")
    assert "### github.com/foo/bar" in text
    assert "- [[x]] (score: 7.5, review)" in text


def test_append_to_existing_subsection(tmp_path):
    body = (
        "# hot\n\n"
        f"{_HOT_PROJECT_SECTION}\n\n"
        "### github.com/foo/bar\n\n"
        "- [[a]] (score: 8.0, stable)\n\n"
    )
    _make_hot(tmp_path, body=body)
    _patch_hot_project_subpages(tmp_path, "github.com/foo/bar", "[[b]]", 9.0, "stable")
    text = (tmp_path / "hot.md").read_text(encoding="utf-8")
    # b score=9 排前
    a_idx = text.index("[[a]]")
    b_idx = text.index("[[b]]")
    assert b_idx < a_idx
    assert "### github.com/foo/bar" in text


def test_top_3_cap(tmp_path):
    body = (
        "# hot\n\n"
        f"{_HOT_PROJECT_SECTION}\n\n"
        "### github.com/foo/bar\n\n"
        "- [[a]] (score: 7.5, stable)\n"
        "- [[b]] (score: 8.0, stable)\n"
        "- [[c]] (score: 8.5, stable)\n\n"
    )
    _make_hot(tmp_path, body=body)
    _patch_hot_project_subpages(tmp_path, "github.com/foo/bar", "[[d]]", 10.0, "stable")
    text = (tmp_path / "hot.md").read_text(encoding="utf-8")
    # d=10 + c=8.5 + b=8.0 留, a=7.5 被砍
    assert "[[d]]" in text
    assert "[[c]]" in text
    assert "[[b]]" in text
    assert "[[a]]" not in text


def test_dedup_same_wikilink(tmp_path):
    body = (
        "# hot\n\n"
        f"{_HOT_PROJECT_SECTION}\n\n"
        "### github.com/foo/bar\n\n"
        "- [[x]] (score: 7.0, review)\n\n"
    )
    _make_hot(tmp_path, body=body)
    _patch_hot_project_subpages(tmp_path, "github.com/foo/bar", "[[x]]", 9.5, "stable")
    text = (tmp_path / "hot.md").read_text(encoding="utf-8")
    # 仅 1 个 [[x]] 行 (新值取代)
    assert text.count("[[x]]") == 1
    assert "score: 9.5" in text
    assert "score: 7.0" not in text


def test_derive_project_key_valid():
    assert (
        _derive_project_key("知识库/项目/github.com/foo/bar/_index.md")
        == "github.com/foo/bar"
    )
    assert (
        _derive_project_key(Path("知识库/项目/gitlab.com/org/repo/sub/x.md"))
        == "gitlab.com/org/repo"
    )


def test_derive_project_key_non_project():
    assert _derive_project_key("知识库/领域/技术/x.md") is None
    assert _derive_project_key("知识库/收件箱/a.md") is None
    assert _derive_project_key("hot.md") is None


def test_hot_md_missing_skip(tmp_path):
    # 无 hot.md → 静默, 不抛
    _patch_hot_project_subpages(tmp_path, "github.com/foo/bar", "[[x]]", 8.0, "stable")
    assert not (tmp_path / "hot.md").exists()


def test_extract_score_from_line():
    assert _extract_score_from_line("- [[foo]] (score: 7.5, stable)") == 7.5
    assert _extract_score_from_line("- [[bar]] (score: 10.0, review)") == 10.0


def test_extract_score_fallback():
    assert _extract_score_from_line("- [[no-score]]") == 0.0
    assert _extract_score_from_line("") == 0.0


def test_multiple_projects_separate(tmp_path):
    _make_hot(tmp_path)
    _patch_hot_project_subpages(tmp_path, "github.com/a/b", "[[x]]", 8.0, "stable")
    _patch_hot_project_subpages(tmp_path, "github.com/c/d", "[[y]]", 9.0, "review")
    text = (tmp_path / "hot.md").read_text(encoding="utf-8")
    assert "### github.com/a/b" in text
    assert "### github.com/c/d" in text
    assert "[[x]]" in text
    assert "[[y]]" in text
