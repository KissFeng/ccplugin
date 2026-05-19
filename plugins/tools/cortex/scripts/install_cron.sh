#!/usr/bin/env bash
# cortex/scripts/install_cron.sh
#
# 不自动写用户 crontab/launchd, 仅打印 snippet 供用户自决复制。
# 支持: macOS launchd / Linux cron / GitHub Actions
#
# 用法:
#   bash install_cron.sh [--plugin-root <path>] [launchd|cron|gha]   # 默认 cron
#   bash install_cron.sh --help
#
# 任务清单:
#   daily   01:00       cortex lint
#   daily   02:30       cortex dashboard refresh
#   daily   03:00       cortex consolidate (log/session 读+析+处+更新+清理)
#
# 所有命令以 `claude --bare -p` 触发对应 skill, 用户需先安装 claude CLI。

set -euo pipefail

print_help() {
  cat <<'EOF'
install_cron.sh — 打印 cortex 周期任务 snippet (不写 crontab/launchd)

USAGE:
  bash install_cron.sh [--plugin-root <path>] [launchd|cron|gha]
  bash install_cron.sh --help

OPTIONS:
  --help, -h             显示本帮助

PLUGIN_ROOT 强制写死为 marketplace 规范路径:
  ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex
EOF
}

# -------- 参数解析 --------
KIND=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      print_help
      exit 0
      ;;
    cron|launchd|gha)
      KIND="$1"
      shift
      ;;
    *)
      echo "usage: $0 [cron|launchd|gha]" >&2
      exit 2
      ;;
  esac
done
KIND="${KIND:-cron}"

# 强制 marketplace 规范路径, 字面量 ~/, 不接受任何覆盖
PLUGIN_ROOT=~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex

# Load ~/.cortex/config.json (env > config > fallback) so the printed snippets
# default to the user's configured vault/lang/settings. JSON syntax errors
# fail-fast here (cortex_config_init exits 1 with stderr message).
# shellcheck source=./lib/config.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/config.sh"
cortex_config_init

# vault: config only (env-free per PRD).
VAULT="$(cx_get_vault)"
if [[ -z "$VAULT" ]]; then
  echo "[install_cron.sh] no vault configured: set 'vault' in ~/.cortex/config.json" >&2
  exit 3
fi

# lang/settings flow into the printed snippet so users get the same resolution
# rules as cron/run.sh — but as CLI flags (not env exports).
LANG_OVERRIDE="$(cx_config_get lang "")"
SETTINGS="$(cx_config_get settings "")"

print_task_table() {
  cat <<'EOF' >&2
┌──────────────────┬───────────────┬───────────────────────────────────────┐
│ 脚本             │ 频率          │ 功能                                  │
├──────────────────┼───────────────┼───────────────────────────────────────┤
│ lint.sh          │ 每日 01:00    │ 17 规则 autofix 循环至 clean          │
│ dashboard.sh     │ 每日 02:30    │ 重渲 index/hot/canvas 仪表盘          │
│ digest.sh        │ 每日 03:00    │ log/session 读+析+处+更新+清理+归档   │
│ refresh_projects │ 每周一 03:00  │ 知识库/项目/ 批量增量刷 (git/website) │
└──────────────────┴───────────────┴───────────────────────────────────────┘
EOF
}

cron_lines() {
  # 输出 4 行 cortex cron job, 调 ~/.cortex/scripts/ 用户级 wrapper (统一入口)
  # 3 daily + 1 weekly (refresh_projects, Mon 03:00, flock 防并发)
  printf '0 1 * * * bash "%s/.cortex/scripts/lint.sh"\n' "$HOME"
  printf '30 2 * * * bash "%s/.cortex/scripts/dashboard.sh"\n' "$HOME"
  printf '0 3 * * * bash "%s/.cortex/scripts/digest.sh"\n' "$HOME"
  printf '0 3 * * 1 flock -n /tmp/cortex-refresh.lock bash "%s/.cortex/scripts/refresh_projects.sh" >> "%s/.cortex/logs/refresh.log" 2>&1\n' "$HOME" "$HOME"
}

install_cron_auto() {
  # 读现有 crontab → 比对 cortex 段是否与期望一致 → 一致 no-op, 不一致才写.
  # 表格无论是否修改都输出.
  print_task_table

  if ! command -v crontab >/dev/null 2>&1; then
    echo "[install_cron] crontab 未安装, 无法自动注册." >&2
    echo "[install_cron] 手工 snippet:" >&2
    cron_lines
    return 1
  fi

  local existing filtered desired new
  existing=$(crontab -l 2>/dev/null || true)
  # 取 existing 中所有 cortex 行 (含旧/新路径)
  local cur_cortex
  cur_cortex=$(printf '%s\n' "$existing" \
    | grep -E '(\.cortex/scripts/|cortex/scripts/cron/)(lint|dashboard|digest|fold|consolidate|refresh_projects)\.sh' \
    || true)
  desired=$(cron_lines)

  if [[ "$cur_cortex" == "$desired" ]]; then
    echo "✓ crontab cortex 段已是最新, no-op (3 daily + 1 weekly job)" >&2
    crontab -l 2>/dev/null | grep -E '\.cortex/scripts/' | sed 's/^/    /' >&2
    return 0
  fi

  # 不同 → 替换: 去掉所有旧 cortex 行 + 追加 desired
  filtered=$(printf '%s\n' "$existing" \
    | grep -Ev '(\.cortex/scripts/|cortex/scripts/cron/)(lint|dashboard|digest|fold|consolidate|refresh_projects)\.sh' \
    || true)
  new=$(printf '%s\n%s' "$filtered" "$desired" | sed -e 's/^[[:space:]]*$//' | awk 'NF || prev{print; prev=NF}')

  if printf '%s\n' "$new" | crontab -; then
    echo "✓ crontab 已更新 (变更, 写入 3 daily + 1 weekly cortex job)" >&2
    crontab -l 2>/dev/null | grep -E '\.cortex/scripts/' | sed 's/^/    /' >&2
  else
    echo "✗ crontab 写入失败" >&2
    return 2
  fi
}

launchd_plist() {
  # $1 = job name (lint/dashboard/digest), $2 = Hour, $3 = Minute
  local job="$1" hour="$2" minute="$3"
  cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>dev.lazygophers.cortex.daily-${job}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${HOME}/.cortex/scripts/${job}.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>${hour}</integer>
    <key>Minute</key><integer>${minute}</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${HOME}/.cache/cortex/${job}.log</string>
  <key>StandardErrorPath</key>
  <string>${HOME}/.cache/cortex/${job}.err</string>
</dict>
</plist>
EOF
}

install_launchd_auto() {
  # 写 3 个 plist 到 ~/Library/LaunchAgents/, 卸载旧 + load 新.
  print_task_table

  if ! command -v launchctl >/dev/null 2>&1; then
    echo "[install_cron] launchctl 未找到 (非 macOS?), fallback 输出 plist 内容:" >&2
    launchd_plist lint 1 0
    return 1
  fi

  local agent_dir="$HOME/Library/LaunchAgents"
  mkdir -p "$agent_dir" "$HOME/.cache/cortex"

  # job, hour, minute
  local jobs=(
    "lint:1:0"
    "dashboard:2:30"
    "digest:3:0"
  )

  # 先卸载/删旧 (含 fold / consolidate)
  for old in fold consolidate; do
    local op="$agent_dir/dev.lazygophers.cortex.daily-${old}.plist"
    local ow="$agent_dir/dev.lazygophers.cortex.weekly-${old}.plist"
    for f in "$op" "$ow"; do
      [[ -f "$f" ]] && launchctl unload "$f" 2>/dev/null
      [[ -f "$f" ]] && rm -f "$f" && echo "  - removed $f" >&2
    done
  done

  local changed=0
  for entry in "${jobs[@]}"; do
    IFS=: read -r job hour minute <<< "$entry"
    local plist="$agent_dir/dev.lazygophers.cortex.daily-${job}.plist"
    local desired
    desired=$(launchd_plist "$job" "$hour" "$minute")
    # 比对: 内容一致 → no-op
    if [[ -f "$plist" ]] && [[ "$(cat "$plist")" == "$desired" ]]; then
      echo "  = ${job}.plist 已是最新, 跳过" >&2
      continue
    fi
    changed=1
    [[ -f "$plist" ]] && launchctl unload "$plist" 2>/dev/null
    printf '%s\n' "$desired" > "$plist"
    if launchctl load "$plist"; then
      echo "  + ${job}.plist 已更新 + load 成功" >&2
    else
      echo "  ✗ ${job}.plist load 失败" >&2
    fi
  done
  if [[ "$changed" -eq 0 ]]; then
    echo "✓ launchd cortex 段已是最新, no-op (3 个 daily job)" >&2
  else
    echo "✓ launchd 已更新 (变更, 3 个 daily job)" >&2
  fi
  echo "  当前 cortex agents:" >&2
  ls "$agent_dir" 2>/dev/null | grep -E '^dev\.lazygophers\.cortex\.' | sed 's/^/    /' >&2
}

print_gha() {
  print_task_table
  cat <<'EOF'
# ===== cortex GitHub Actions workflow =====
# 保存为 .github/workflows/cortex:cron.yml (在你的 vault 仓库)
# 要求 vault 是 GitHub repo, 并配置 secrets.OBSIDIAN_API_KEY 等
#
# 注意: CI 环境路径与本机 marketplace 不同。下方 ${GITHUB_WORKSPACE} 由
# Actions runner 注入, 指向 checkout 后的 vault 仓库根。若你的 cortex
# 插件 checkout 到子目录, 请显式调整路径。

name: cortex-cron

on:
  schedule:
    - cron: '0 1 * * *'    # daily lint
    - cron: '30 2 * * *'   # daily dashboard refresh
    - cron: '0 3 * * *'    # daily consolidate (read/analyze/process/update/cleanup)
  workflow_dispatch:

jobs:
  lint:
    if: github.event.schedule == '0 1 * * *'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - name: cortex lint
        run: bash ${GITHUB_WORKSPACE}/plugins/tools/cortex/scripts/cron/lint.sh
      - uses: actions/upload-artifact@v4
        with: { name: lint-report, path: ~/.cache/cortex/cron/ }

  dashboard:
    if: github.event.schedule == '30 2 * * *'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - name: cortex dashboard
        run: bash ${GITHUB_WORKSPACE}/plugins/tools/cortex/scripts/cron/dashboard.sh
      - name: commit
        run: |
          git config user.name "cortex-bot"
          git config user.email "cortex@noreply.local"
          git add -A
          git diff --quiet --staged || git commit -m "cortex: daily dashboard"
          git push

  consolidate:
    if: github.event.schedule == '0 3 * * *'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - name: cortex consolidate
        run: bash ${GITHUB_WORKSPACE}/plugins/tools/cortex/scripts/cron/digest.sh
      - name: commit
        run: |
          git config user.name "cortex-bot"
          git config user.email "cortex@noreply.local"
          git add -A
          git diff --quiet --staged || git commit -m "cortex: daily consolidate"
          git push

EOF
}

case "$KIND" in
  cron)    install_cron_auto ;;
  launchd) install_launchd_auto ;;
  gha)     print_gha ;;
  *)
    echo "usage: $0 [--plugin-root <path>] [cron|launchd|gha]" >&2
    exit 2
    ;;
esac

