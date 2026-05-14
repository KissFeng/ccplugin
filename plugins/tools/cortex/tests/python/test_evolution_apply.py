"""Tests for cortex-refactor evolution_apply (PR4).

覆盖: list_proposals / check_safety_gate (白名单/黑名单/git dirty/不存在) /
delete_proposal / diff block 解析.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
REFACTOR_DIR = PLUGIN_ROOT / "scripts" / "refactor"
sys.path.insert(0, str(REFACTOR_DIR))

import evolution_apply  # noqa: E402,F401 — needed for patch() target
from evolution_apply import (  # noqa: E402
    PROPOSALS_REL_DIR,
    check_safety_gate,
    delete_proposal,
    list_proposals,
)


def _mk_vault(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    v.mkdir()
    return v


def _write_proposal(
    vault: Path,
    filename: str = "2026-05-14-test.md",
    target_skill: str = "plugins/tools/cortex/skills/cortex-save/SKILL.md",
    include_diff: bool = True,
    pattern_id: str = "pat-test1",
) -> Path:
    d = vault / PROPOSALS_REL_DIR
    d.mkdir(parents=True, exist_ok=True)
    diff_block = (
        "```diff\n"
        f"--- a/{target_skill}\n"
        f"+++ b/{target_skill}\n"
        "@@ -10,3 +10,4 @@\n"
        " context line\n"
        f"+# auto-proposal from {pattern_id}\n"
        " context line\n"
        "```\n"
    ) if include_diff else ""
    text = (
        "---\n"
        f"pattern_id: {pattern_id}\n"
        f"target_skill: {target_skill}\n"
        "confidence: 0.85\n"
        "applications: 5\n"
        "category: vault-write\n"
        "sources:\n"
        "  - sessions/claude-code/2026/05/13/abc.jsonl\n"
        "---\n\n"
        f"# Proposal: test\n\n"
        f"## Suggested Patch\n\n{diff_block}\n"
    )
    p = d / filename
    p.write_text(text, encoding="utf-8")
    return p


def test_list_proposals_empty(tmp_path):
    """_assets/evolution-proposals/ 不存在 → 空 list."""
    v = _mk_vault(tmp_path)
    assert list_proposals(v) == []


def test_list_proposals_parse_yaml(tmp_path):
    """创建 proposal → list 正确解析 frontmatter + diff_summary."""
    v = _mk_vault(tmp_path)
    _write_proposal(v, filename="a.md", pattern_id="pat-a")
    _write_proposal(v, filename="b.md", pattern_id="pat-b")
    items = list_proposals(v)
    assert len(items) == 2
    assert items[0]["pattern_id"] == "pat-a"
    assert items[1]["pattern_id"] == "pat-b"
    assert items[0]["target_skill"].endswith("SKILL.md")
    assert items[0]["confidence"] == "0.85"
    assert items[0]["applications"] == "5"
    assert "@@" in items[0]["diff_summary"] or items[0]["diff_summary"].startswith("+")


def test_safety_gate_whitelist_skill_ok(tmp_path):
    v = _mk_vault(tmp_path)
    p = _write_proposal(v, target_skill="plugins/tools/cortex/skills/cortex-save/SKILL.md")
    with patch.dict(os.environ, {"CORTEX_SKIP_GIT_GATE": "1"}):
        ok, msg, diff = check_safety_gate(p)
    assert ok is True
    assert msg == "ok"
    assert "auto-proposal from pat-test1" in diff


def test_safety_gate_whitelist_references_ok(tmp_path):
    v = _mk_vault(tmp_path)
    p = _write_proposal(
        v, target_skill="plugins/tools/cortex/skills/cortex-ingest/references/exclude.md",
    )
    with patch.dict(os.environ, {"CORTEX_SKIP_GIT_GATE": "1"}):
        ok, _, _ = check_safety_gate(p)
    assert ok is True


def test_safety_gate_agent_md_ok(tmp_path):
    v = _mk_vault(tmp_path)
    p = _write_proposal(v, target_skill="plugins/tools/cortex/AGENT.md")
    with patch.dict(os.environ, {"CORTEX_SKIP_GIT_GATE": "1"}):
        ok, msg, _ = check_safety_gate(p)
    assert ok is True
    # bare AGENT.md form too
    p2 = _write_proposal(v, filename="agent2.md", target_skill="AGENT.md")
    with patch.dict(os.environ, {"CORTEX_SKIP_GIT_GATE": "1"}):
        ok2, _, _ = check_safety_gate(p2)
    assert ok2 is True


def test_safety_gate_blacklist_commands(tmp_path):
    v = _mk_vault(tmp_path)
    p = _write_proposal(v, target_skill="plugins/tools/cortex/commands/save.md")
    with patch.dict(os.environ, {"CORTEX_SKIP_GIT_GATE": "1"}):
        ok, msg, diff = check_safety_gate(p)
    assert ok is False
    assert "黑名单" in msg or "commands" in msg
    assert diff == ""


def test_safety_gate_blacklist_scripts(tmp_path):
    v = _mk_vault(tmp_path)
    p = _write_proposal(v, target_skill="plugins/tools/cortex/scripts/cli/save.py")
    with patch.dict(os.environ, {"CORTEX_SKIP_GIT_GATE": "1"}):
        ok, msg, _ = check_safety_gate(p)
    assert ok is False
    assert "黑名单" in msg or "scripts" in msg


def test_safety_gate_blacklist_meta_templates(tmp_path):
    v = _mk_vault(tmp_path)
    p = _write_proposal(v, target_skill="plugins/tools/cortex/_meta/version.json")
    with patch.dict(os.environ, {"CORTEX_SKIP_GIT_GATE": "1"}):
        ok, _, _ = check_safety_gate(p)
    assert ok is False
    p2 = _write_proposal(v, filename="t.md",
                         target_skill="plugins/tools/cortex/_templates/foo.md")
    with patch.dict(os.environ, {"CORTEX_SKIP_GIT_GATE": "1"}):
        ok2, _, _ = check_safety_gate(p2)
    assert ok2 is False


def test_safety_gate_not_whitelisted(tmp_path):
    v = _mk_vault(tmp_path)
    p = _write_proposal(v, target_skill="plugins/some/other/path.md")
    with patch.dict(os.environ, {"CORTEX_SKIP_GIT_GATE": "1"}):
        ok, msg, _ = check_safety_gate(p)
    assert ok is False
    assert "白名单" in msg


def test_safety_gate_proposal_not_exist(tmp_path):
    v = _mk_vault(tmp_path)
    ok, msg, _ = check_safety_gate(v / "nonexistent.md")
    assert ok is False
    assert "不存在" in msg


def test_safety_gate_no_diff_block(tmp_path):
    v = _mk_vault(tmp_path)
    p = _write_proposal(v, include_diff=False)
    with patch.dict(os.environ, {"CORTEX_SKIP_GIT_GATE": "1"}):
        ok, msg, _ = check_safety_gate(p)
    assert ok is False
    assert "diff" in msg.lower()


def test_safety_gate_git_dirty(tmp_path):
    """Mock subprocess.run to return dirty git status → safety gate fails."""
    v = _mk_vault(tmp_path)
    p = _write_proposal(v)
    repo = tmp_path / "fakerepo"
    (repo / ".git").mkdir(parents=True)
    (repo / "plugins" / "tools" / "cortex").mkdir(parents=True)

    class FakeResult:
        returncode = 0
        stdout = " M plugins/tools/cortex/skills/foo.md\n"
        stderr = ""

    with patch.dict(os.environ, {"CORTEX_REPO_ROOT": str(repo)}, clear=False):
        os.environ.pop("CORTEX_SKIP_GIT_GATE", None)
        with patch("evolution_apply.subprocess.run", return_value=FakeResult()):
            ok, msg, _ = check_safety_gate(p)
    assert ok is False
    assert "dirty" in msg or "commit" in msg


def test_safety_gate_git_clean(tmp_path):
    v = _mk_vault(tmp_path)
    p = _write_proposal(v)
    repo = tmp_path / "cleanrepo"
    (repo / ".git").mkdir(parents=True)
    (repo / "plugins" / "tools" / "cortex").mkdir(parents=True)

    class FakeResult:
        returncode = 0
        stdout = ""
        stderr = ""

    with patch.dict(os.environ, {"CORTEX_REPO_ROOT": str(repo)}, clear=False):
        os.environ.pop("CORTEX_SKIP_GIT_GATE", None)
        with patch("evolution_apply.subprocess.run", return_value=FakeResult()):
            ok, msg, diff = check_safety_gate(p)
    assert ok is True
    assert diff


def test_delete_proposal(tmp_path):
    v = _mk_vault(tmp_path)
    p = _write_proposal(v)
    assert p.exists()
    assert delete_proposal(p) is True
    assert not p.exists()
    # idempotent: delete again → True
    assert delete_proposal(p) is True


def test_check_returns_diff_block(tmp_path):
    """check 返 diff 字符串可被外部 Edit 工具消费."""
    v = _mk_vault(tmp_path)
    p = _write_proposal(v, pattern_id="pat-XYZ")
    with patch.dict(os.environ, {"CORTEX_SKIP_GIT_GATE": "1"}):
        ok, _, diff = check_safety_gate(p)
    assert ok is True
    assert "--- a/" in diff
    assert "+++ b/" in diff
    assert "pat-XYZ" in diff


def test_cli_list_help():
    """`python3 evolution_apply.py list --help` 输出 usage 且 rc=0."""
    r = subprocess.run(
        [sys.executable, str(REFACTOR_DIR / "evolution_apply.py"), "list", "--help"],
        capture_output=True, text=True, timeout=15,
    )
    assert r.returncode == 0
    assert "evolution-proposals" in r.stdout or "vault" in r.stdout


def test_cli_list_empty_vault(tmp_path):
    """`python3 evolution_apply.py list --vault <empty>` → []."""
    v = _mk_vault(tmp_path)
    r = subprocess.run(
        [sys.executable, str(REFACTOR_DIR / "evolution_apply.py"),
         "list", "--vault", str(v)],
        capture_output=True, text=True, timeout=15,
    )
    assert r.returncode == 0
    assert json.loads(r.stdout) == []


def test_cli_check_blacklist_returns_rc1(tmp_path):
    v = _mk_vault(tmp_path)
    p = _write_proposal(v, target_skill="plugins/tools/cortex/commands/x.md")
    env = {**os.environ, "CORTEX_SKIP_GIT_GATE": "1"}
    r = subprocess.run(
        [sys.executable, str(REFACTOR_DIR / "evolution_apply.py"),
         "check", str(p), "--vault", str(v)],
        capture_output=True, text=True, timeout=15, env=env,
    )
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["ok"] is False
    assert out["diff"] == ""
