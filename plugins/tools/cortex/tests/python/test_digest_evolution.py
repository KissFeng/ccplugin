"""Tests for cortex-digest evolution CLI (PR3).

覆盖: scan_sessions / extract_patterns / write_patterns_md / generate_proposals
+ CLI smoke (--dry-run + JSON schema).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
CLI_DIR = PLUGIN_ROOT / "scripts" / "cli"
sys.path.insert(0, str(CLI_DIR))

from lib.evolution import (  # noqa: E402
    MIN_APPLICATIONS,
    MIN_CONFIDENCE,
    PATTERNS_REL,
    PROPOSALS_REL_DIR,
    SESSIONS_REL,
    extract_patterns,
    generate_proposals,
    scan_sessions,
    write_patterns_md,
)


def _mk_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    (vault / "记忆" / "L0-核心").mkdir(parents=True)
    (vault / SESSIONS_REL / "claude-code" / "2026" / "05" / "14").mkdir(parents=True)
    return vault


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for obj in lines:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def test_scan_sessions_empty(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    # sessions dir 不存在 → 返空, 不抛
    eps = scan_sessions(vault, lookback_days=7)
    assert eps == []


def test_scan_sessions_lookback_filter(tmp_path: Path) -> None:
    vault = _mk_vault(tmp_path)
    fresh = vault / SESSIONS_REL / "claude-code" / "2026" / "05" / "14" / "fresh.jsonl"
    old = vault / SESSIONS_REL / "claude-code" / "2025" / "01" / "01" / "old.jsonl"
    _write_jsonl(fresh, [{"role": "user", "content": "hi"}])
    _write_jsonl(old, [{"role": "user", "content": "hi"}])
    # 让 old 文件 mtime 倒退 30 天
    old_ts = time.time() - 30 * 86400
    import os
    os.utime(old, (old_ts, old_ts))

    eps = scan_sessions(vault, lookback_days=7)
    rels = [e.rel_path for e in eps]
    assert any("fresh.jsonl" in r for r in rels)
    assert not any("old.jsonl" in r for r in rels)


def test_extract_pattern_below_threshold(tmp_path: Path) -> None:
    vault = _mk_vault(tmp_path)
    # 仅 2 个 sessions 触发同 signature → < MIN_APPLICATIONS=3 → 不入
    for i in range(2):
        p = (vault / SESSIONS_REL / "claude-code" / "2026" / "05" / "14"
             / f"s{i}.jsonl")
        _write_jsonl(p, [
            {"role": "user", "content": "frontmatter schema 缺字段问题反复出现"},
        ])
    eps = scan_sessions(vault, lookback_days=7)
    pats = extract_patterns(eps)
    assert pats == []


def test_extract_pattern_at_threshold(tmp_path: Path) -> None:
    vault = _mk_vault(tmp_path)
    # 3 个 sessions 同 signature → 入 + 因 frontmatter 关键词 → frontmatter-schema
    for i in range(3):
        p = (vault / SESSIONS_REL / "claude-code" / "2026" / "05" / "14"
             / f"s{i}.jsonl")
        _write_jsonl(p, [
            {"role": "user", "content": "frontmatter 缺 schema 字段"},
        ])
    eps = scan_sessions(vault, lookback_days=7)
    pats = extract_patterns(eps)
    assert len(pats) >= 1
    cat_set = {p.category for p in pats}
    assert "frontmatter-schema" in cat_set
    p = [x for x in pats if x.category == "frontmatter-schema"][0]
    assert p.applications >= MIN_APPLICATIONS


def test_extract_negative_feedback(tmp_path: Path) -> None:
    vault = _mk_vault(tmp_path)
    # 3 sessions 含 "不对" 纠正语 → user-correction high-confidence
    for i in range(3):
        p = (vault / SESSIONS_REL / "claude-code" / "2026" / "05" / "14"
             / f"neg{i}.jsonl")
        _write_jsonl(p, [
            {"role": "assistant", "content": "做了 X 操作"},
            {"role": "user", "content": "不对, 应该是 Y"},
        ])
    eps = scan_sessions(vault, lookback_days=7)
    pats = extract_patterns(eps)
    user_corr = [p for p in pats if p.category == "user-correction"]
    assert len(user_corr) >= 1
    assert user_corr[0].confidence >= 0.9


def test_write_patterns_md_new(tmp_path: Path) -> None:
    vault = _mk_vault(tmp_path)
    # 制造 3 个 sessions 触发 frontmatter-schema
    for i in range(3):
        p = (vault / SESSIONS_REL / "claude-code" / "2026" / "05" / "14"
             / f"f{i}.jsonl")
        _write_jsonl(p, [{"role": "user", "content": "frontmatter schema 缺字段"}])
    eps = scan_sessions(vault, lookback_days=7)
    pats = extract_patterns(eps)
    added, updated = write_patterns_md(pats, vault)
    patterns_md = vault / PATTERNS_REL
    assert patterns_md.exists()
    text = patterns_md.read_text(encoding="utf-8")
    assert "# Patterns" in text
    assert "## frontmatter-schema" in text
    assert added >= 1
    assert updated == 0


def test_write_patterns_md_update(tmp_path: Path) -> None:
    vault = _mk_vault(tmp_path)
    for i in range(3):
        p = (vault / SESSIONS_REL / "claude-code" / "2026" / "05" / "14"
             / f"g{i}.jsonl")
        _write_jsonl(p, [{"role": "user", "content": "frontmatter schema 缺字段"}])
    eps = scan_sessions(vault, lookback_days=7)
    pats = extract_patterns(eps)
    # 第一次写
    write_patterns_md(pats, vault)
    # 第二次写同 patterns → applications 升, updated 命中
    pats2 = extract_patterns(eps)
    added2, updated2 = write_patterns_md(pats2, vault)
    assert updated2 >= 1
    text = (vault / PATTERNS_REL).read_text(encoding="utf-8")
    # 既有 id 仍在
    assert text.count("### pat-") >= 1


def test_generate_proposal_path(tmp_path: Path) -> None:
    vault = _mk_vault(tmp_path)
    # 3 个 sessions 含 negative feedback → confidence 0.9 ≥ 0.8 → 生 proposal
    for i in range(3):
        p = (vault / SESSIONS_REL / "claude-code" / "2026" / "05" / "14"
             / f"n{i}.jsonl")
        _write_jsonl(p, [
            {"role": "assistant", "content": "ai 做了 X"},
            {"role": "user", "content": "不对, 应该是 Y"},
        ])
    eps = scan_sessions(vault, lookback_days=7)
    pats = extract_patterns(eps)
    proposals = generate_proposals(pats, vault)
    assert len(proposals) >= 1
    for rel in proposals:
        assert rel.startswith(PROPOSALS_REL_DIR + "/")
        f = vault / rel
        assert f.exists()
        text = f.read_text(encoding="utf-8")
        assert "pattern_id:" in text
        assert "```diff" in text


def test_generate_proposal_below_threshold(tmp_path: Path) -> None:
    """confidence < 0.8 (普通 skill-trigger 默认 0.65 = 0.5+0.15) → 不生 proposal."""
    vault = _mk_vault(tmp_path)
    for i in range(3):
        p = (vault / SESSIONS_REL / "claude-code" / "2026" / "05" / "14"
             / f"k{i}.jsonl")
        _write_jsonl(p, [{"role": "user", "content": "trigger 检测"}])
    eps = scan_sessions(vault, lookback_days=7)
    pats = extract_patterns(eps)
    # skill-trigger 普通模式 confidence 应低于 0.8
    skill_trig = [p for p in pats if p.category == "skill-trigger"]
    if skill_trig:
        # 仅当其 confidence < MIN_CONFIDENCE 时验证不生 proposal
        assert skill_trig[0].confidence < MIN_CONFIDENCE
        proposals = generate_proposals(pats, vault)
        assert proposals == []


def test_dry_run(tmp_path: Path) -> None:
    vault = _mk_vault(tmp_path)
    for i in range(3):
        p = (vault / SESSIONS_REL / "claude-code" / "2026" / "05" / "14"
             / f"d{i}.jsonl")
        _write_jsonl(p, [
            {"role": "assistant", "content": "X"},
            {"role": "user", "content": "不对, 改成 Y"},
        ])
    eps = scan_sessions(vault, lookback_days=7)
    pats = extract_patterns(eps)
    write_patterns_md(pats, vault, dry_run=True)
    proposals = generate_proposals(pats, vault, dry_run=True)
    # dry_run → patterns.md 不应被写盘 (vault 内未来此文件)
    assert not (vault / PATTERNS_REL).exists()
    # proposals 返列表但文件不存在
    for rel in proposals:
        assert not (vault / rel).exists()


def test_cli_help() -> None:
    """`digest.py --help` / `digest.py evolution --help` 都应正常."""
    cli = PLUGIN_ROOT / "scripts" / "cli" / "digest.py"
    r1 = subprocess.run(
        [sys.executable, str(cli), "--help"], capture_output=True, text=True, timeout=10,
    )
    assert r1.returncode == 0
    assert "evolution" in r1.stdout.lower()

    r2 = subprocess.run(
        [sys.executable, str(cli), "evolution", "--help"],
        capture_output=True, text=True, timeout=10,
    )
    assert r2.returncode == 0
    assert "--lookback-days" in r2.stdout


def test_cli_dry_run_json_schema(tmp_path: Path) -> None:
    """`digest.py evolution --dry-run` 输出合法 JSON, 含必需 keys."""
    vault = _mk_vault(tmp_path)
    for i in range(3):
        p = (vault / SESSIONS_REL / "claude-code" / "2026" / "05" / "14"
             / f"j{i}.jsonl")
        _write_jsonl(p, [
            {"role": "assistant", "content": "X"},
            {"role": "user", "content": "不对, 改成 Y"},
        ])
    cli = PLUGIN_ROOT / "scripts" / "cli" / "digest.py"
    r = subprocess.run(
        [sys.executable, str(cli), "evolution",
         "--vault", str(vault), "--dry-run"],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, r.stderr
    obj = json.loads(r.stdout)
    for key in (
        "vault", "lookback_days", "dry_run",
        "sessions_scanned", "patterns_candidates",
        "patterns_added", "patterns_updated", "proposals_generated",
    ):
        assert key in obj, f"missing key: {key}"
    assert obj["dry_run"] is True
    assert obj["sessions_scanned"] >= 3
    assert isinstance(obj["proposals_generated"], list)
