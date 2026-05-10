#!/usr/bin/env bash
# cortex/scripts/cron/lint.sh — daily lint of the cortex vault via claude --bare.
#
# Usage:
#   lint.sh [--dry-run] [--vault <path>] [--lang <code>] [--settings <path>]
#
# Wraps run.sh with the lint prompt. Read-only (allowed-tools = Bash Read Glob Grep).

set -uo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$DIR/../.." && pwd)"

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

PROMPT="Run cortex-lint on the vault at \$CORTEX_VAULT (use lang \$CORTEX_LANG if set).
Output the lint summary as compact JSON with errors/warns/rules_hit.
Use the cortex-lint skill (read-only, do not autofix in cron).
Tool budget: Bash Read Glob Grep only."

exec "$DIR/run.sh" lint -- "$PROMPT" \
  --allowed-tools "Bash Read Glob Grep"
