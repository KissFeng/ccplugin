#!/usr/bin/env bash
# Claude Code UserPromptSubmit hook — 每次用户输入触发
# 注入触发词检测 + 强制 reminder, 推动 AI 主动调 ~/.cortex/scripts/memory.sh recall / search.sh

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

# 短列表 cap
hits = hits[:10]


def detect_project_hint() -> str:
    """推当前项目 host/org/repo, 用作搜索 query 收敛词。"""
    # 1. git remote (github/gitlab)
    try:
        r = subprocess.run(
            ["git", "-C", str(cwd), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        url = (r.stdout or "").strip()
        if url:
            # git@host:org/repo.git or https://host/org/repo[.git]
            s = url.rstrip("/")
            if s.endswith(".git"):
                s = s[:-4]
            if s.startswith("git@"):
                # git@host:org/repo
                host_rest = s[4:].split(":", 1)
                if len(host_rest) == 2:
                    host = host_rest[0]
                    parts = host_rest[1].split("/")
                    if len(parts) >= 2:
                        return f"{host}/{parts[-2]}/{parts[-1]}"
            elif "://" in s:
                tail = s.split("://", 1)[1]
                parts = tail.split("/")
                if len(parts) >= 3:
                    return f"{parts[0]}/{parts[-2]}/{parts[-1]}"
    except Exception:
        pass
    # 2. 相对 $HOME 路径策略 (~/persons/<org>/<repo>) → host=最顶段
    try:
        home = Path.home()
        rel = cwd.resolve().relative_to(home)
        parts = list(rel.parts)
        if len(parts) >= 3:
            return f"{parts[0]}/{parts[-2]}/{parts[-1]}"
        if len(parts) >= 1:
            # 补 _local
            pad = parts + ["_local"] * (3 - len(parts))
            return f"{pad[0]}/{pad[1]}/{pad[2]}"
    except Exception:
        pass
    return ""


project_hint = detect_project_hint()
project_repo = project_hint.split("/")[-1] if project_hint else ""

msg = ""
if hits:
    shown = hits[:5]
    if project_hint:
        proj_line = (
            f'   - 步骤 a: --scope domains --query "<主题>" (限 知识库/项目/, 当前项目 = {project_hint})\n'
            f'     · 命中后 grep path 含 "{project_repo}" 取项目内结果\n'
            f'   - 步骤 b: 项目内无果, --scope domains 全项目结果照看 (跨项目复用经验)\n'
            f'   - 步骤 c: 仍无果, --scope all 泛搜 知识库/\n'
        )
    else:
        proj_line = (
            '   - 步骤 a: --scope domains --query "<主题>" (限 知识库/项目/)\n'
            '   - 步骤 b: 无果, --scope all 泛搜 知识库/\n'
        )
    msg = (
        f"⚠️ 用户问题含触发词 {shown}。**禁止直接询问用户**, 第一个工具调用**必须先搜**:\n"
        f"1. bash ~/.cortex/scripts/memory.sh recall --query <主题> — 召回记忆 (L0-L4)\n"
        f"2. bash ~/.cortex/scripts/search.sh --query <主题> --scope <scope> — 搜知识库\n"
        f"{proj_line}"
        f"3. 仅当全部**无命中**才允许向用户提问 (引用 hits/path 证明搜过)。"
    )
    if any(k in prompt_lower for k in ["记住", "remember", "别忘了", "永远", "暂时"]):
        msg += "\n⚡ 含记忆指令 → bash ~/.cortex/scripts/memory.sh write --uri <u> --content <c> --level <l>。"
    elif any(k in prompt_lower for k in ["忘了", "forget"]):
        msg += "\n⚡ 含遗忘指令 → bash ~/.cortex/scripts/memory.sh forget --uri <u>。"
else:
    if len(prompt) > 20:
        if project_repo:
            msg = (
                f"💡 上下文/记忆查询顺序: search.sh --scope domains --query <主题> "
                f"(限项目, 过滤 path 含 '{project_repo}') → --scope domains 全项目 → "
                f"--scope all 泛搜。记忆走 memory.sh recall。"
            )
        else:
            msg = "💡 如需上下文/记忆, 调 bash ~/.cortex/scripts/memory.sh recall / bash ~/.cortex/scripts/search.sh。"
    else:
        msg = ""

# 整体注入 cap (800 + 容差)
if msg and len(msg) > 800:
    msg = msg[:797] + "..."

if msg:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": msg,
        }
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
PYEOF

exit 0
