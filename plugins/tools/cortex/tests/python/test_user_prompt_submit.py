"""测试 UserPromptSubmit hook 行为 (PR1: MCP first 硬契约每轮注入)."""
import json
import os
import subprocess
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
HOOK = PLUGIN_ROOT / "scripts" / "hooks" / "user_prompt_submit.sh"


def _run(prompt, vault):
    # Plugin business is env-free: mock ~/.cortex/config.json via HOME override.
    fake_home = vault.parent / "home"
    (fake_home / ".cortex").mkdir(parents=True, exist_ok=True)
    (fake_home / ".cortex" / "config.json").write_text(
        json.dumps({"vault": str(vault)}), encoding="utf-8"
    )
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    return subprocess.run(
        [str(HOOK)],
        input=prompt,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


def _make_vault(tmp_path):
    v = tmp_path / "vault"
    (v / "_meta").mkdir(parents=True)
    (v / "_meta" / "version.json").write_text('{"preset":"lyt","lang":"zh-CN"}')
    (v / ".obsidian").mkdir()
    return v


def _ctx(r):
    assert r.stdout.strip(), "expected hook output"
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]


# === 原有行为兼容 ===

def test_trigger_keyword_hit(tmp_path):
    v = _make_vault(tmp_path)
    r = _run("我在调研 Go 性能优化", v)
    assert r.returncode == 0
    ctx = _ctx(r)
    # 触发词命中提示
    assert "触发词命中" in ctx or "项目 =" in ctx
    # 仍提 memory.sh recall (在硬契约里)
    assert "memory.sh recall" in ctx


def test_remember_directive(tmp_path):
    v = _make_vault(tmp_path)
    r = _run("记住我喜欢 Go 语言", v)
    assert r.returncode == 0
    ctx = _ctx(r)
    assert "memory.sh write" in ctx


def test_forget_directive(tmp_path):
    v = _make_vault(tmp_path)
    r = _run("忘了之前关于 React 的偏好", v)
    assert r.returncode == 0
    ctx = _ctx(r)
    assert "memory.sh forget" in ctx


def test_vault_missing_silent(tmp_path):
    """vault 不存在 → silent exit 0, 无输出."""
    nonexistent = tmp_path / "nope"
    fake_home = tmp_path / "home"
    (fake_home / ".cortex").mkdir(parents=True, exist_ok=True)
    (fake_home / ".cortex" / "config.json").write_text(
        json.dumps({"vault": str(nonexistent)}), encoding="utf-8"
    )
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    r = subprocess.run(
        [str(HOOK)],
        input="Go",
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 0
    assert not r.stdout.strip()


def test_size_under_cap(tmp_path):
    v = _make_vault(tmp_path)
    long_prompt = "Go " * 200 + "性能优化"
    r = _run(long_prompt, v)
    assert r.returncode == 0
    ctx = _ctx(r)
    assert len(ctx) <= 1200


# === PR1 新增: MCP first 硬契约每轮注入 ===

def test_hook_msg_contains_mcp_first(tmp_path):
    """msg 含 mcp__obsidian__obsidian_simple_search (L1 first)."""
    v = _make_vault(tmp_path)
    r = _run("foo bar baz quux", v)
    assert r.returncode == 0
    ctx = _ctx(r)
    assert "mcp__obsidian__obsidian_simple_search" in ctx
    assert "首选" in ctx or "L1" in ctx or "first" in ctx.lower()


def test_hook_msg_warns_not_qmd(tmp_path):
    """msg 含 '非 qmd' 软提示."""
    v = _make_vault(tmp_path)
    r = _run("foo bar baz", v)
    assert r.returncode == 0
    ctx = _ctx(r)
    assert "qmd" in ctx.lower()
    assert "非 qmd" in ctx or "禁" in ctx


def test_hook_msg_lists_fallback_search_sh(tmp_path):
    """msg 含 search.sh fallback."""
    v = _make_vault(tmp_path)
    r = _run("foo bar baz", v)
    assert r.returncode == 0
    ctx = _ctx(r)
    assert "search.sh" in ctx
    assert "fallback" in ctx.lower() or "不可达" in ctx


def test_hook_msg_injected_every_prompt(tmp_path):
    """无触发词的通用 prompt 也注入硬契约 (推翻原触发词限定)."""
    v = _make_vault(tmp_path)
    r = _run("帮我写一个排序算法的伪代码示例", v)
    assert r.returncode == 0
    ctx = _ctx(r)
    # 每轮硬契约必须含 MCP first
    assert "mcp__obsidian__obsidian_simple_search" in ctx
    assert "硬契约" in ctx


def test_hook_msg_with_trigger_adds_project_hint(tmp_path):
    """触发词命中 + 项目可推 → 加项目 hint (或至少加触发词提示)."""
    v = _make_vault(tmp_path)
    r = _run("调研一下 React 性能优化的方案", v)
    assert r.returncode == 0
    ctx = _ctx(r)
    # 触发词命中分支输出, 加项目 / 触发词提示
    assert "触发词命中" in ctx or "项目 =" in ctx


def test_hook_msg_lists_complex_search(tmp_path):
    """msg 含 L2 complex_search (JsonLogic)."""
    v = _make_vault(tmp_path)
    r = _run("question x y z", v)
    assert r.returncode == 0
    ctx = _ctx(r)
    assert "obsidian_complex_search" in ctx
    assert "JsonLogic" in ctx or "次选" in ctx


def test_hook_msg_no_trigger_still_has_contract(tmp_path):
    """短 prompt 不命中触发词, 仍输出硬契约 (推翻 短输入静默)."""
    v = _make_vault(tmp_path)
    r = _run("hi there", v)
    assert r.returncode == 0
    ctx = _ctx(r)
    assert "mcp__obsidian__obsidian_simple_search" in ctx


def test_hook_msg_search_contract_warning(tmp_path):
    """msg 含 '硬契约' / '禁忌' / '禁' 警告关键词."""
    v = _make_vault(tmp_path)
    r = _run("a generic question that should still inject contract", v)
    assert r.returncode == 0
    ctx = _ctx(r)
    assert "硬契约" in ctx
    assert "禁忌" in ctx or "禁止" in ctx or "禁" in ctx
