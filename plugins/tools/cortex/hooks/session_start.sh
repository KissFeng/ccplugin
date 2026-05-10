#!/usr/bin/env bash
# session_start.sh
# CC SessionStart hook — 注入 cortex 协作约定 (v2 wrapped JSON)。
# vault 不存在时沉默退出 (退出码 0, stdout 空), 不阻断会话。

set -u

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
LOG_FILE="${HOME}/.cache/cortex/session_start.log"
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

log() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*" >> "$LOG_FILE" 2>/dev/null || true; }

# Consume stdin (don't fail if empty)
cat >/dev/null 2>&1 || true

# Resolve vault
# shellcheck source=./_lib/resolve_vault.sh
source "$PLUGIN_ROOT/hooks/_lib/resolve_vault.sh"
VAULT=$(resolve_vault)

if [[ -z "$VAULT" ]]; then
  log "vault not resolved; silent exit"
  exit 0
fi

log "vault=$VAULT"

# Delegate context build + JSON emit to python (avoids bash quoting hell)
PLUGIN_ROOT="$PLUGIN_ROOT" VAULT="$VAULT" python3 - <<'PYEOF' 2>>"$LOG_FILE" || exit 0
import json
import os
import sys
from pathlib import Path

MAX_BYTES = 5000  # per prd §10.1 — additionalContext soft cap ~10KB total

plugin_root = Path(os.environ["PLUGIN_ROOT"])
vault = Path(os.environ["VAULT"])

agent_md = plugin_root / "AGENT.md"
if not agent_md.is_file():
    sys.exit(0)

template = agent_md.read_text(encoding="utf-8")


def truncated(p: Path) -> str:
    if not p.is_file():
        return ""
    raw = p.read_bytes()
    if len(raw) <= MAX_BYTES:
        return raw.decode("utf-8", errors="replace")
    head = raw[:MAX_BYTES].decode("utf-8", errors="replace")
    return f"{head}\n\n... (truncated, {len(raw)} bytes total)"


hot = truncated(vault / "hot.md")
index_file = vault / "index.md"
index_entries = 0
if index_file.is_file():
    try:
        index_entries = sum(
            1
            for line in index_file.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.startswith("- ")
        )
    except Exception:
        pass

context = (
    template.replace("{{VAULT_PATH}}", str(vault))
    .replace("{{INDEX_ENTRY_COUNT}}", str(index_entries))
    .replace("{{HOT_CACHE_PREVIEW}}", "(已加载, 见下文)" if hot else "(空)")
)

if hot:
    context += f"\n\n### hot.md (前 {MAX_BYTES} bytes)\n\n{hot}\n"

payload = {
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": context,
    }
}
sys.stdout.write(json.dumps(payload, ensure_ascii=False))
PYEOF

exit 0
