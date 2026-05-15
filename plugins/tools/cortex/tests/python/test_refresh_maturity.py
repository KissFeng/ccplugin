"""test revalue_maturity D5 rules + _days_since helper (PR5)."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from _helpers import PLUGIN_ROOT, add_paths

add_paths()
# Make `cli.refresh_projects` importable
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from cli.refresh_projects import _days_since, revalue_maturity  # noqa: E402


def test_frequent_change_30d():
    """hash 变 ≥ 2 + < 30 天 → draft"""
    assert revalue_maturity("stable", 3, 10) == "draft"
    assert revalue_maturity("review", 2, 20) == "draft"
    assert revalue_maturity("draft", 5, 0) == "draft"


def test_single_change_from_stable():
    """hash 变 1 + 旧 stable → review (从 stable 回退)"""
    assert revalue_maturity("stable", 1, 50) == "review"
    assert revalue_maturity("stable", 1, 5) == "review"


def test_single_change_from_review_keep():
    """hash 变 1 + 旧 review → 保持 review (不降级)"""
    assert revalue_maturity("review", 1, 50) == "review"


def test_single_change_from_draft_keep():
    """hash 变 1 + 旧 draft → 保持 draft"""
    assert revalue_maturity("draft", 1, 50) == "draft"


def test_no_change_90d_to_stable():
    """无变化 + ≥ 90 天 → stable"""
    assert revalue_maturity("review", 0, 100) == "stable"
    assert revalue_maturity("draft", 0, 120) == "stable"
    assert revalue_maturity("stable", 0, 95) == "stable"


def test_no_change_180d_to_deprecated():
    """无变化 + ≥ 180 天 → deprecated (优先于 90d→stable)"""
    assert revalue_maturity("stable", 0, 200) == "deprecated"
    assert revalue_maturity("review", 0, 365) == "deprecated"
    assert revalue_maturity("draft", 0, 180) == "deprecated"


def test_no_change_short_period_keep():
    """无变化 + < 90 天 → 保持"""
    assert revalue_maturity("draft", 0, 10) == "draft"
    assert revalue_maturity("stable", 0, 60) == "stable"
    assert revalue_maturity("review", 0, 89) == "review"


def test_frequent_change_old_period():
    """hash 变 ≥ 2 + ≥ 30 天 → 不进 draft 规则, 保持 old"""
    assert revalue_maturity("stable", 2, 40) == "stable"
    assert revalue_maturity("review", 3, 60) == "review"


def test_days_since_iso():
    """_days_since ISO 8601 解析"""
    past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    assert 4 <= _days_since(past) <= 6


def test_days_since_iso_z_suffix():
    """_days_since 接受 Z 后缀 (utc_now() 输出格式)"""
    past = (datetime.now(timezone.utc) - timedelta(days=10)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    assert 9 <= _days_since(past) <= 11


def test_days_since_invalid():
    assert _days_since("") == 0
    assert _days_since("not-a-date") == 0
    assert _days_since(None) == 0


def test_deprecated_no_revival():
    """deprecated + 无变化 (短期) → 保持 deprecated"""
    assert revalue_maturity("deprecated", 0, 10) == "deprecated"


def test_deprecated_with_change():
    """deprecated + hash 变 1 (非 stable) → 保持 (不自动升级 active)"""
    assert revalue_maturity("deprecated", 1, 50) == "deprecated"


def test_patch_index_maturity(tmp_path: Path):
    """_patch_index_maturity 改 _index.md frontmatter"""
    from cli.refresh_projects import _patch_index_maturity

    idx = tmp_path / "_index.md"
    idx.write_text(
        "---\n"
        "source_url: https://x.test\n"
        "maturity: stable\n"
        "last_ingested_at: 2026-01-01T00:00:00Z\n"
        "---\n"
        "# body\n",
        encoding="utf-8",
    )
    _patch_index_maturity(idx, "review")
    text = idx.read_text(encoding="utf-8")
    assert "maturity: review" in text
    assert "maturity: stable" not in text
    assert "source_url: https://x.test" in text
    assert "# body" in text


def test_patch_index_maturity_adds_when_missing(tmp_path: Path):
    """_patch_index_maturity 在 fm 缺 maturity 时新增"""
    from cli.refresh_projects import _patch_index_maturity

    idx = tmp_path / "_index.md"
    idx.write_text(
        "---\nsource_url: https://x.test\n---\n# body\n",
        encoding="utf-8",
    )
    _patch_index_maturity(idx, "draft")
    text = idx.read_text(encoding="utf-8")
    assert "maturity: draft" in text
    assert "last_ingested_at:" in text
