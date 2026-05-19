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
    """每轮注入 — 按需检索约定 (知识库 作为信息源优先级, 不强制每轮先搜)."""
    return (
        "🔍 cortex 约定 — 当你**需要查资料**时, 知识库是第一信息源 (非每轮强制):\n"
        "\n"
        "**触发场景** (需要外部信息时才走): 不熟悉的概念/API/选型, 历史决策/踩坑, 项目专有约定, 用户偏好/记忆, 跨会话上下文。\n"
        "**无需搜的场景**: 改本地代码逻辑 / 读项目文件 / 执行明确指令 / 写显而易见的代码 / 纯对话。\n"
        "\n"
        "**需要查时的优先级**:\n"
        "1. **知识库 首选**: `bash ~/.cortex/scripts/search.sh --query \"<词>\"` (6 层并行: Omnisearch / Obsidian REST / hot / index / SC / rg + 拆词)\n"
        "2. **知识库 补充**: `mcp__obsidian__obsidian_simple_search` / `obsidian_complex_search` — 内置索引或 JsonLogic 过滤\n"
        "3. **记忆**: `mcp__obsidian__obsidian_get_recent_changes` 按时间 / `memory.sh recall` 按 URI\n"
        "4. **本地代码**: Read / Grep / Glob (知识库 无命中且问题是项目内的)\n"
        "5. **外部**: WebSearch / WebFetch / context7 / octocode (知识库 + 本地都无命中)\n"
        "\n"
        "**禁忌**:\n"
        "- 涉及历史决策 / 项目约定 / 用户偏好时直接 WebSearch / 训练记忆答 — 应先 知识库\n"
        "- 用 qmd MCP 替代 obsidian MCP (qmd 索引不全)\n"
        "- 绕过 search.sh 用 Bash rg / Grep 搜 vault 内容 (rg 是 search.sh 第 6 层)"
    )


# 主体: 每轮注入硬契约
msg = build_search_contract_msg()

# 触发词命中 → 额外加项目 hint (仅提示, 不强制)
if hits and project_hint:
    src_tag = "git remote" if project_src == "git" else "相对 $HOME"
    msg += f"\n💡 项目 = `知识库/项目/{project_hint}/` ({src_tag}); 需查项目历史/约定时可按 path 过滤 + memory.sh recall 召回。"
elif hits:
    msg += f"\n💡 触发词命中 {hits[:3]} — 涉及历史/约定时优先 知识库。"
elif project_hint:
    msg += f"\n💡 项目 = `知识库/项目/{project_hint}/` (需查项目历史时入口)。"

# 记忆指令快捷
if any(k in prompt_lower for k in ["记住", "remember", "别忘了", "永远", "暂时"]):
    msg += "\n⚡ 含记忆指令 → `memory.sh write --uri <u> --content <c> --level <l>`."
elif any(k in prompt_lower for k in ["忘了", "forget"]):
    msg += "\n⚡ 含遗忘指令 → `memory.sh forget --uri <u>`."

# 整体注入 cap (1200 + 容差)
if len(msg) > 1200:
    msg = msg[:1197] + "..."

payload = {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": msg,
    }
}
sys.stdout.write(json.dumps(payload, ensure_ascii=False))
PYEOF

exit 0
