#!/usr/bin/env bash
# stop.sh
# CC Stop hook — 启发式判定是否落档当前会话。
# v1 stub: 只记录触发事件, 不执行落档 (落档由 cortex-save skill / /cortex:save 命令负责)。
# v2 (M4): 集成 transcript 解析 + 关键词启发式 + 自动调用 cortex-save。

set -u

LOG_FILE="${HOME}/.cache/cortex/stop.log"
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

log() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*" >> "$LOG_FILE" 2>/dev/null || true; }

# Consume stdin payload but don't block
HOOK_INPUT=$(cat 2>/dev/null || true)
TRANSCRIPT_PATH=$(printf '%s' "$HOOK_INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('transcript_path', ''))
except Exception:
    pass
" 2>/dev/null || true)

log "stop hook fired transcript=$TRANSCRIPT_PATH"

# v1: silent. v2 will heuristic-detect and dispatch save.
exit 0
