#!/usr/bin/env bash
# cortex/scripts/cron/memory-archive.sh — monthly archive execution via claude --bare.
#
# Trigger: 0 06 1 * *   (1st of month, 06:00)
# Frequency: monthly
# Duty: 扫 archive_pending: true 的记忆条目 → mv 到 归档/<year>/记忆/<level>/<原路径>;
#       更新 _meta/uri-index.json (标 archived: true)。L0 永不归档。
#
# Usage:
#   memory-archive.sh [--dry-run] [--vault <path>] [--lang <code>] [--settings <path>]

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
export CORTEX_TIMEOUT="${CORTEX_TIMEOUT:-900}"

PROMPT="[AUTO_MODE: non-interactive shell wrapper. 禁用 AskUserQuestion, 自动决策]

任务: 归档已标记记忆 (memory-archive)。

vault: \$CORTEX_VAULT

具体行动:
1. 扫 <vault>/记忆体系/**/*.md, 读 frontmatter 找 archive_pending: true 的条目。
2. 对每个候选:
   - 若 level == L0 → 跳过 + 写报警到 <vault>/记忆体系/views/alerts.md (L0 永不归档, 即使被错误标记)
   - 其他 level: 计算目标路径:
       src: <vault>/记忆体系/<level-dir>/<rest>
       dst: <vault>/归档/\$(date +%Y)/记忆/<level-dir>/<rest>
     用 Bash mkdir -p <dst 父目录> + mv <src> <dst>。
3. 更新 <vault>/_meta/uri-index.json (若存在):
   - 对应 uri 节点添加字段 archived: true, archived_at: <UTC ISO>, archived_path: <相对路径>
   - 不删除条目 (仍可通过 uri 解析到归档位置)
4. 不删条目内容, 只迁移路径 + 标 index。
5. 写日志到 <vault>/_meta/memory-archive.log (append 一行 \`<UTC ISO>: archived=N, skipped_l0=N\`)。

输出: 一行 JSON { archived: N, skipped_l0: N, index_updated: true|false }。
vault 不存在 → { skipped: true, reason: 'no vault' }。

工具预算: Bash Read Glob Write Edit。"

exec "$DIR/run.sh" memory-archive -- "$PROMPT" \
  --allowed-tools "Bash Read Glob Write Edit"
