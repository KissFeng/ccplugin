#!/usr/bin/env bash
# cortex/scripts/migrate.sh — 一次性 schema v2 评分迁移 wrapper (PR6).
#
# 一次性脚本: 旧 score 1-5 整数 → 0-10 浮点 (× 2.0), patterns confidence 0-1 → 0-10 (× 10),
# 知识库 / 记忆 .md 缺评分字段加 stub。不进 install_wrappers EXPECTED 集 (用完即归档)。
set -euo pipefail

if [ -t 2 ] && [ -z "${NO_COLOR:-}" ]; then
  _CX_R=$'\033[1;31m'; _CX_C=$'\033[1;36m'; _CX_0=$'\033[0m'
else
  _CX_R=""; _CX_C=""; _CX_0=""
fi
err()    { printf '%s✗%s %s\n' "$_CX_R" "$_CX_0" "$1" >&2; exit "${2:-4}"; }
banner() { printf '%s▸%s cortex %s  %s\n' "$_CX_C" "$_CX_0" "$*" "$(date '+%H:%M:%S')" >&2; }

print_usage() {
  cat <<'USAGE'
Usage: migrate.sh [-h|--help] --to=v2 [--vault PATH] [--dry-run] [--no-backup]

cortex 一次性评分字段迁移 (旧 score 1-5 → 0-10 / patterns conf 0-1 → 0-10 / 缺字段加 stub):

Options:
  -h, --help     Show this help and exit
  --to=v2        Target schema version (only v2 supported)
  --vault PATH   vault 根 (默认从 ~/.cortex/config.json 解析)
  --dry-run      仅扫不写, 输出 JSON 报告
  --no-backup    跳过 tar.gz 备份 (默认 backup /tmp/cortex-migration-backup-<TS>.tar.gz)

Rollback: tar xzf /tmp/cortex-migration-backup-<TS>.tar.gz -C <parent-of-vault>
USAGE
}

PASS_ARGS=()
VAULT_OVERRIDE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) print_usage; exit 0 ;;
    --vault) VAULT_OVERRIDE="${2:-}"; shift 2 ;;
    --vault=*) VAULT_OVERRIDE="${1#--vault=}"; shift ;;
    *) PASS_ARGS+=("$1"); shift ;;
  esac
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CLI="$PLUGIN_ROOT/scripts/migrate/migrate_scores_to_v2.py"
[ -f "$CLI" ] || err "missing CLI: $CLI"

if [[ -z "$VAULT_OVERRIDE" ]]; then
  VAULT_OVERRIDE="$(python3 -c 'import json,os; p=os.path.expanduser("~/.cortex/config.json"); print(json.load(open(p)).get("vault","")) if os.path.exists(p) else print("")' 2>/dev/null || echo "")"
fi
[ -n "$VAULT_OVERRIDE" ] || err "vault not set; pass --vault or configure ~/.cortex/config.json"

banner "migrate v2 (vault=$VAULT_OVERRIDE)"
printf '%s$%s python3 %q --vault %q %s\n' \
  "$_CX_C" "$_CX_0" "$CLI" "$VAULT_OVERRIDE" "${PASS_ARGS[*]:-}" >&2

exec python3 "$CLI" --vault "$VAULT_OVERRIDE" "${PASS_ARGS[@]}"
