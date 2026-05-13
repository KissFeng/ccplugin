#!/usr/bin/env bash
# cortex/scripts/cron/dashboard.sh — daily dashboard refresh via claude.
#
# Usage:
#   dashboard.sh [--dry-run] [--vault <path>] [--lang <code>] [--settings <path>]

set -uo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../lib/config.sh
source "$DIR/../lib/config.sh"
cortex_config_init

DRY_FLAG=()
VAULT_FLAG=()
LANG_FLAG=()
SETTINGS_FLAG=()
CLI_VAULT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)  DRY_FLAG=(--dry-run);              shift ;;
    --vault)    CLI_VAULT="$2"; VAULT_FLAG=(--vault "$2"); shift 2 ;;
    --lang)     LANG_FLAG=(--lang "$2");           shift 2 ;;
    --settings) SETTINGS_FLAG=(--settings "$2");   shift 2 ;;
    *) echo "unknown flag: $1" >&2; exit 4 ;;
  esac
done


VAULT="${CLI_VAULT:-$(cx_get_vault)}"
if [[ -z "$VAULT" ]]; then
  echo "[cortex/dashboard] no vault: pass --vault or set vault in ~/.cortex/config.json" >&2
  exit 3
fi
LANG_CODE="$(cx_config_get lang "" 2>/dev/null || echo "")"
TIMEOUT_FLAG=(--timeout 600)

PROMPT="[AUTO_MODE persistent] Invoke Skill cortex-dashboard on vault=$VAULT lang=${LANG_CODE:-zh-CN}. The skill SKILL.md is the single source of truth for query (8 kinds) / render (7 charts incl mermaid fallbacks) / inject (DASH:BEGIN/END with KPI + chart + table + legend). Follow it strictly, no skip, no ask, 严禁 N/A 占位. Emit the compact JSON described in the skill '## 输出' section."

exec "$DIR/run.sh" dashboard \
  ${VAULT_FLAG[@]+"${VAULT_FLAG[@]}"} ${LANG_FLAG[@]+"${LANG_FLAG[@]}"} ${SETTINGS_FLAG[@]+"${SETTINGS_FLAG[@]}"} ${TIMEOUT_FLAG[@]+"${TIMEOUT_FLAG[@]}"} ${DRY_FLAG[@]+"${DRY_FLAG[@]}"} \
  -- "$PROMPT" \
  --allowed-tools "Bash Read Write Edit Glob"
