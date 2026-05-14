#!/usr/bin/env bash
# cortex/scripts/ingest_remote.sh — 静态源文件 (install_wrappers.sh PR3 复制到 ~/.cortex/scripts/).
#
# 远程整 repo / 整站 ingest 入口:
#   github/gitlab → shallow clone → 复用 ingest pipeline
#   其他 host → sitemap / BFS crawl → 每页 sanitize+mask+hash
#
# 风格对齐 ingest_url.sh (CLI 类 wrapper, 不调 slash).
set -euo pipefail

if [ -t 2 ] && [ -z "${NO_COLOR:-}" ]; then
  _CX_R=$'\033[1;31m'; _CX_G=$'\033[1;32m'; _CX_C=$'\033[1;36m'; _CX_0=$'\033[0m'
else
  _CX_R=""; _CX_G=""; _CX_C=""; _CX_0=""
fi
err()    { printf '%s✗%s %s\n' "$_CX_R" "$_CX_0" "$1" >&2; exit "${2:-4}"; }
banner() { printf '%s▸%s cortex %s  %s\n' "$_CX_C" "$_CX_0" "$*" "$(date '+%H:%M:%S')" >&2; }

print_usage() {
  cat <<USAGE
Usage: ingest_remote.sh [-h|--help] [-i|--interactive] <url> [--target <path>] [--depth N] [--dry-run]

cortex 远程 ingest 入口:
  github.com/gitlab.com URL → shallow clone → ingest 整 repo
  其他 host (含 github.io)   → sitemap / BFS crawl → 每页 ingest

Options:
  -h, --help          Show this help and exit
  -i, --interactive   Drop CLI exec → 进入 claude REPL + 注入 /cortex:ingest <url>
  --target <path>     显式 vault 落档路径覆盖
  --depth N           website crawl 深度 (default 3, github 忽略)
  --dry-run           仅识别 + 输出 JSON, 不写盘

Examples:
  ingest_remote.sh https://github.com/foo/bar
  ingest_remote.sh https://example.com --depth 2 --dry-run
USAGE
}

INTERACTIVE=0
URL=""
PASS_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) print_usage; exit 0 ;;
    -i|--interactive) INTERACTIVE=1; shift ;;
    *) if [[ -z "$URL" && "$1" != --* ]]; then URL="$1"; shift; else PASS_ARGS+=("$1"); shift; fi ;;
  esac
done
[[ -n "$URL" ]] || err "missing <url> (try --help)" 2

# Resolve plugin root (this file lives at <PLUGIN_ROOT>/scripts/ingest_remote.sh).
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

if [[ $INTERACTIVE -eq 1 ]]; then
  CONFIG="$HOME/.cortex/config.json"
  [[ -f "$CONFIG" ]] || err "config 不存在: $CONFIG" 4
  command -v jq >/dev/null 2>&1 || err "缺 jq, 请装: brew install jq" 4
  SETTINGS="$(jq -r '.settings // empty' "$CONFIG" 2>/dev/null)"
  SETTINGS="${SETTINGS:-$HOME/.claude/settings.json}"
  banner "ingest_remote (interactive REPL)"
  printf '%s$%s claude --settings %q --dangerously-skip-permissions "/cortex:ingest %s"\n' \
    "$_CX_C" "$_CX_0" "$SETTINGS" "$URL" >&2
  exec claude --settings "$SETTINGS" --dangerously-skip-permissions -p "/cortex:ingest $URL"
fi

banner "ingest_remote $URL"
printf '%s$%s python3 %q %q %s\n' "$_CX_C" "$_CX_0" \
  "$PLUGIN_ROOT/scripts/cli/ingest_remote.py" "$URL" "${PASS_ARGS[*]:-}" >&2
exec python3 "$PLUGIN_ROOT/scripts/cli/ingest_remote.py" "$URL" "${PASS_ARGS[@]}"
