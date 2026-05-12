#!/usr/bin/env bash
# cortex/scripts/cron/lint.sh — daily lint of the cortex vault via claude --bare.
#
# Usage:
#   lint.sh [--dry-run] [--sync-templates] [--vault <path>] [--lang <code>] [--settings <path>]
#
# Wraps run.sh with the lint prompt. Default read-only (allowed-tools = Bash Read Glob Grep).
# With --sync-templates: also allows Write/Edit so AI can auto-sync template/seed drift
# (rules: template-outdated / template-missing / seed-outdated only).

set -uo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$DIR/../.." && pwd)"

DRY=0
SYNC_TEMPLATES=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --sync-templates) SYNC_TEMPLATES=1; shift ;;
    --vault) export CORTEX_VAULT="$2"; shift 2 ;;
    --lang) export CORTEX_LANG="$2"; shift 2 ;;
    --settings) export CORTEX_SETTINGS="$2"; shift 2 ;;
    *) echo "unknown flag: $1" >&2; exit 4 ;;
  esac
done

[[ "$DRY" == "1" ]] && export CORTEX_DRY_RUN=1
[[ "$SYNC_TEMPLATES" == "1" ]] && export CORTEX_SYNC_TEMPLATES=1

SYNC_HINT=""
ALLOWED_TOOLS="Bash Read Glob Grep"
if [[ "$SYNC_TEMPLATES" == "1" ]]; then
  ALLOWED_TOOLS="Bash Read Glob Grep Write Edit"
  SYNC_HINT="

NOTE: caller passed --sync-templates (CORTEX_SYNC_TEMPLATES=1). Before the read-only
report, invoke lint/run.py with --sync-templates once to auto-sync template-outdated /
template-missing / seed-outdated drift (those rules only; other fixable findings remain
reported, not modified). Then run the regular lint report."
fi

PROMPT="Run cortex-lint on the vault at \$CORTEX_VAULT (use lang \$CORTEX_LANG if set).
Output the lint summary as compact JSON with errors/warns/rules_hit.
Use the cortex-lint skill (read-only by default, do not autofix in cron unless --sync-templates set).
Tool budget: ${ALLOWED_TOOLS}.${SYNC_HINT}"

exec "$DIR/run.sh" lint -- "$PROMPT" \
  --allowed-tools "$ALLOWED_TOOLS"
