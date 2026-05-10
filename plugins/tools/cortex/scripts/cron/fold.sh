#!/usr/bin/env bash
# cortex/scripts/cron/fold.sh — weekly log fold via claude --bare.
#
# Usage:
#   fold.sh [--dry-run] [--vault <path>] [--lang <code>] [--settings <path>]

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
# fold writes — give a wider timeout than lint
export CORTEX_TIMEOUT="${CORTEX_TIMEOUT:-600}"

PROMPT="Run cortex-fold on the vault at \$CORTEX_VAULT.
Default --days 7 keep window. Apply changes (\\\`--apply\\\`) if invoked from weekly cron.
Tool budget: Bash Read Write Edit Glob.
Output one-line JSON summary: { folded: N, written: <fold paths>, kept: M }."

exec "$DIR/run.sh" fold -- "$PROMPT" \
  --allowed-tools "Bash Read Write Edit Glob"
