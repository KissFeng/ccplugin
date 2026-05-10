#!/usr/bin/env bash
# cortex/scripts/cron/dashboard.sh — weekly dashboard refresh via claude --bare.
#
# Usage:
#   dashboard.sh [--dry-run] [--vault <path>] [--lang <code>] [--settings <path>]

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

PROMPT="Run cortex-dashboard refresh on the vault at \$CORTEX_VAULT.
Pick Bases if available, fall back to Dataview otherwise.
Refresh only existing dashboard pages; do not invent new ones.
Tool budget: Bash Read Write Edit Glob.
Output one-line JSON summary: { refreshed: <list of dashboard paths>, skipped: M }."

exec "$DIR/run.sh" dashboard -- "$PROMPT" \
  --allowed-tools "Bash Read Write Edit Glob"
