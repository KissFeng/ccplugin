#!/usr/bin/env bash
# Claude Code UserPromptSubmit hook — 每次用户输入触发
# 每轮注入 MCP first 搜索硬契约 + 触发词额外加项目 hint + memory 指令快捷

set -u

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex}"

# 读 user prompt (stdin) — Claude Code 传入 JSON, 提取 prompt 字段; 兼容裸文本
RAW_INPUT="$(cat)"

# Resolve vault, silent exit if missing
# shellcheck source=_lib/resolve_vault.sh
source "$PLUGIN_ROOT/scripts/hooks/_lib/resolve_vault.sh"
VAULT=$(resolve_vault)
[[ -z "$VAULT" ]] && exit 0

# 当前项目目录: Claude Code 注入 CLAUDE_PROJECT_DIR, 兜底 PWD
CWD="${CLAUDE_PROJECT_DIR:-${PWD:-$(pwd)}}"

# Delegate to python
PLUGIN_ROOT="$PLUGIN_ROOT" VAULT="$VAULT" RAW_INPUT="$RAW_INPUT" CWD="$CWD" python3 <<'PYEOF' 2>/dev/null || exit 0
import json, os, sys, subprocess
from pathlib import Path

plugin_root = Path(os.environ["PLUGIN_ROOT"])
vault = Path(os.environ["VAULT"])
raw = os.environ.get("RAW_INPUT", "")
cwd = Path(os.environ.get("CWD") or os.getcwd())

# Claude Code 可能传入 JSON payload {prompt: "..."}, 也可能裸文本
prompt = raw
try:
    obj = json.loads(raw)
    if isinstance(obj, dict) and "prompt" in obj:
        prompt = str(obj.get("prompt") or "")
except Exception:
    pass

# 读触发词 (vault _meta/triggers.yaml > plugin templates/triggers.yaml)
def load_triggers():
    for p in [vault / "_meta" / "triggers.yaml", plugin_root / "presets" / "seed" / "_templates" / "triggers.yaml"]:
        if p.is_file():
            try:
                txt = p.read_text(errors="ignore")
                kws = set()
                for line in txt.splitlines():
                    s = line.strip()
                    if s.startswith("- "):
                        kw = s[2:].strip().strip('"').strip("'")
                        if kw and not kw.startswith("#"):
                            kws.add(kw.lower())
                return kws
            except Exception:
                pass
    return set()

triggers = load_triggers()
prompt_lower = prompt.lower()

# 检测命中
hits = []
for kw in triggers:
    if kw and kw in prompt_lower:
        hits.append(kw)
hits = hits[:10]


def detect_project_hint() -> tuple[str, str]:
    """推当前项目 host/org/repo + 来源 (git|local|""). 用作搜索 query 收敛词。"""
    try:
        r = subprocess.run(
            ["git", "-C", str(cwd), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        url = (r.stdout or "").strip()
        if url:
            s = url.rstrip("/")
            if s.endswith(".git"):
                s = s[:-4]
            if s.startswith("git@"):
                host_rest = s[4:].split(":", 1)
                if len(host_rest) == 2:
                    host = host_rest[0]
                    parts = host_rest[1].split("/")
                    if len(parts) >= 2:
                        return f"{host}/{parts[-2]}/{parts[-1]}", "git"
            elif "://" in s:
                tail = s.split("://", 1)[1]
                parts = tail.split("/")
                if len(parts) >= 3:
                    return f"{parts[0]}/{parts[-2]}/{parts[-1]}", "git"
    except Exception:
        pass
    try:
        home = Path.home()
        rel = cwd.resolve().relative_to(home)
        parts = list(rel.parts)
        if len(parts) >= 3:
            return f"{parts[0]}/{parts[-2]}/{parts[-1]}", "local"
        if len(parts) >= 1:
            pad = parts + ["_local"] * (3 - len(parts))
            return f"{pad[0]}/{pad[1]}/{pad[2]}", "local"
    except Exception:
        pass
    return "", ""


project_hint, project_src = detect_project_hint()


def build_search_contract_msg() -> str:
    """每轮注入 — 极简约定."""
    return (
        "🔍 cortex: 需查资料时依次回退 (前一步无果才走下一步) → "
        "`mcp__obsidian__*_search` → `mcp__qmd__search` → "
        "`bash ~/.cortex/scripts/search.sh --query \"<词>\"` → 本地 Read/Grep → WebSearch。\n"
        "📝 非平凡发现 (架构决策/踩坑/选型/技巧/外部综述) 自动 `cortex-save` 或 `cortex-ingest` 落档, "
        "用户说\"记住\" → `memory.sh write`。"
    )


# 主体: 每轮注入硬契约
msg = build_search_contract_msg()

if project_hint:
    msg += f"\n💡 `知识库/项目/{project_hint}/`"

if len(msg) > 500:
    msg = msg[:497] + "..."

payload = {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": msg,
    }
}
sys.stdout.write(json.dumps(payload, ensure_ascii=False))
PYEOF

exit 0
