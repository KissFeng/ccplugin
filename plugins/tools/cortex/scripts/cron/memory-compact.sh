#!/usr/bin/env bash
# cortex/scripts/cron/memory-compact.sh — weekly L4 ledger gzip compaction via claude --bare.
#
# Trigger: 0 04 * * 0   (weekly Sun 04:00)
# Frequency: weekly
# Duty: L4-流水账/ledger/*.jsonl mtime>30d → gzip --keep; 60d+ 删原 .jsonl。
#       L4-流水账/sessions/<cli>/YYYY-MM/ 30d+ → tar.gz 整目录。
#
# Usage:
#   memory-compact.sh [--dry-run] [--vault <path>] [--lang <code>] [--settings <path>]

set -uo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

DRY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --vault) export CORTEX_VAULT="$2"; shift 2 ;;
    --lang) export CORTEX_LANG="$2"; shift 2 ;;
    --settings) export CORTEX_SETTINGS="$2"; shift 2 ;;
    *) echo "unknown flag: $1" >&2; exit 4 ;;
  esac
done

[[ "$DRY" == "1" ]] && export CORTEX_DRY_RUN=1
export CORTEX_TIMEOUT="${CORTEX_TIMEOUT:-600}"

PROMPT="[AUTO_MODE: non-interactive shell wrapper. 禁用 AskUserQuestion, 自动决策]

任务: L4 流水账压缩 (memory-compact)。

vault: \$CORTEX_VAULT
policy: <vault>/_meta/memory-policy.yaml (L4.forget.compress_after_days, 默认 30)

具体行动:
1. 找 <vault>/记忆体系/L4-流水账/ledger/*.jsonl 且 mtime > 30 天:
   - 若 <file>.gz 不存在 → 跑 \`gzip --keep <file>\` (保留双备份 .jsonl + .jsonl.gz)
   - 若 mtime > 60 天 且 .gz 已存在 → 删原 .jsonl, 仅保留 .gz
2. 找 <vault>/记忆体系/L4-流水账/sessions/<cli>/YYYY-MM/ 整月目录, mtime > 30 天:
   - 若同名 .tar.gz 不存在 → 跑 \`tar -czf <YYYY-MM>.tar.gz <YYYY-MM>/\`
   - mtime > 60 天 且 .tar.gz 已存在 → 删原目录
3. 不动 ledger 当月文件 (mtime ≤ 30 天) 与 sessions 当月目录。
4. 写日志到 <vault>/_meta/memory-compact.log (append 一行 \`<UTC ISO>: gzip=N, tar=N, removed=N\`)。

输出: 一行 JSON { gzipped: N, tarred: N, removed_originals: N }。
vault 不存在 → { skipped: true, reason: 'no vault' }。

工具预算: Bash Read Glob Write Edit (gzip/tar 通过 Bash 执行)。"

exec "$DIR/run.sh" memory-compact -- "$PROMPT" \
  --allowed-tools "Bash Read Glob Write Edit"
