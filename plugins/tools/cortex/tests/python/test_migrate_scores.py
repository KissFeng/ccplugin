"""Tests for migrate_scores_to_v2 (PR6 一次性 schema v2 迁移)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = (
    PLUGIN_ROOT / "scripts" / "migrate" / "migrate_scores_to_v2.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("migrate_scores_v2", _MODULE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["migrate_scores_v2"] = mod
    spec.loader.exec_module(mod)
    return mod


migrate_mod = _load_module()


def _make_vault(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "_meta").mkdir(exist_ok=True)
    (root / "_meta" / "version.json").write_text(
        '{"lang":"zh-CN"}', encoding="utf-8"
    )
    return root


def _write_md(path: Path, fm_lines: list[str], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "---\n" + "\n".join(fm_lines) + "\n---\n\n" + body
    path.write_text(text, encoding="utf-8")


def _read_fm(path: Path) -> dict:
    from lib.frontmatter import parse as fm_parse  # type: ignore

    return fm_parse(path.read_text(encoding="utf-8"))[0]


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    return _make_vault(tmp_path / "vault")


def test_migrate_score_int_to_float(vault: Path) -> None:
    md = vault / "知识库" / "项目" / "github.com" / "foo" / "bar" / "_index.md"
    _write_md(
        md,
        [
            "type: project",
            "title: bar",
            "score: 3",
            "confidence: 5.0",
            "source_credibility: 7.0",
            "maturity: review",
        ],
        "# bar\n",
    )
    result = migrate_mod.migrate(vault, dry_run=False, backup=False)
    fm = _read_fm(md)
    assert fm["score"] == "6.0"  # frontmatter helper returns str, value is 6.0
    assert result["score_migrated"] == 1
    assert result["files_changed"] == 1


def test_migrate_score_5_to_10(vault: Path) -> None:
    md = vault / "知识库" / "领域" / "技术" / "x.md"
    _write_md(
        md,
        [
            "type: concept",
            "score: 5",
            "confidence: 5.0",
            "source_credibility: 5.0",
            "maturity: review",
        ],
        "# x\n",
    )
    migrate_mod.migrate(vault, dry_run=False, backup=False)
    fm = _read_fm(md)
    assert fm["score"] == "10.0"


def test_migrate_score_already_float(vault: Path) -> None:
    md = vault / "知识库" / "领域" / "技术" / "y.md"
    _write_md(
        md,
        [
            "type: concept",
            "score: 7.5",
            "confidence: 8.0",
            "source_credibility: 6.0",
            "maturity: stable",
        ],
        "# y\n",
    )
    result = migrate_mod.migrate(vault, dry_run=False, backup=False)
    assert result["score_migrated"] == 0  # value preserved
    fm = _read_fm(md)
    # Value preserved as 7.5 (helper returns str; coerce to float for compare)
    assert float(str(fm["score"])) == 7.5


def test_migrate_kb_add_stubs(vault: Path) -> None:
    md = vault / "知识库" / "领域" / "技术" / "missing.md"
    _write_md(md, ["type: concept", "title: missing"], "# missing\n")
    result = migrate_mod.migrate(vault, dry_run=False, backup=False)
    fm = _read_fm(md)
    assert "score" in fm
    assert "confidence" in fm
    assert "source_credibility" in fm
    assert fm["maturity"] == "draft"
    assert result["fields_added"] >= 4


def test_migrate_mem_add_stubs(vault: Path) -> None:
    md = vault / "记忆" / "L1-长期" / "procedural" / "skill.md"
    _write_md(md, ["type: memory", "title: skill"], "# skill\n")
    result = migrate_mod.migrate(vault, dry_run=False, backup=False)
    fm = _read_fm(md)
    assert "importance" in fm
    assert "confidence" in fm
    assert result["fields_added"] >= 2


def test_migrate_patterns_confidence(vault: Path) -> None:
    p = vault / "记忆" / "L0-核心" / "patterns.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "# Patterns\n\n## skill-trigger\n\n### pat-2026-05-15-abc Foo\n\n"
        "```yaml\n"
        "id: pat-2026-05-15-abc\n"
        "confidence: 0.85\n"
        "applications: 5\n"
        "```\n",
        encoding="utf-8",
    )
    result = migrate_mod.migrate(vault, dry_run=False, backup=False)
    text = p.read_text(encoding="utf-8")
    assert "confidence: 8.5" in text
    assert result["patterns_migrated"] == 1


def test_migrate_dry_run(vault: Path) -> None:
    md = vault / "知识库" / "领域" / "技术" / "x.md"
    _write_md(md, ["type: concept", "score: 3"], "# x\n")
    before = md.read_text(encoding="utf-8")
    result = migrate_mod.migrate(vault, dry_run=True, backup=False)
    after = md.read_text(encoding="utf-8")
    assert before == after
    assert result["files_changed"] >= 1
    assert result["dry_run"] is True


def test_migrate_skip_archived(vault: Path) -> None:
    md = vault / "归档" / "old.md"
    _write_md(md, ["type: concept", "score: 3"], "# old\n")
    result = migrate_mod.migrate(vault, dry_run=False, backup=False)
    fm = _read_fm(md)
    # untouched
    assert fm["score"] == "3"
    assert result["files_scanned"] == 0


def test_migrate_skip_inbox(vault: Path) -> None:
    md = vault / "知识库" / "收件箱" / "new.md"
    _write_md(md, ["type: fleeting", "score: 2"], "# new\n")
    result = migrate_mod.migrate(vault, dry_run=False, backup=False)
    fm = _read_fm(md)
    assert fm["score"] == "2"
    assert result["files_scanned"] == 0


def test_migrate_json_schema(vault: Path) -> None:
    result = migrate_mod.migrate(vault, dry_run=True, backup=False)
    for key in (
        "vault",
        "dry_run",
        "backup_path",
        "files_scanned",
        "files_changed",
        "fields_added",
        "score_migrated",
        "patterns_migrated",
        "errors",
    ):
        assert key in result


def test_migrate_maturity_invalid_enum(vault: Path) -> None:
    md = vault / "知识库" / "领域" / "技术" / "z.md"
    _write_md(
        md,
        [
            "type: concept",
            "score: 7.5",
            "confidence: 8.0",
            "source_credibility: 6.0",
            "maturity: bogus",
        ],
        "# z\n",
    )
    migrate_mod.migrate(vault, dry_run=False, backup=False)
    fm = _read_fm(md)
    assert fm["maturity"] == "draft"


def test_migrate_score_clamp_high(vault: Path) -> None:
    md = vault / "知识库" / "领域" / "技术" / "high.md"
    _write_md(
        md,
        [
            "type: concept",
            "score: 11.5",
            "confidence: 8.0",
            "source_credibility: 6.0",
            "maturity: stable",
        ],
        "# high\n",
    )
    migrate_mod.migrate(vault, dry_run=False, backup=False)
    fm = _read_fm(md)
    assert fm["score"] == "10.0"
