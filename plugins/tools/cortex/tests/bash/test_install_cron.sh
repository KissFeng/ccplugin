#!/usr/bin/env bash
# Tests for scripts/install_cron.sh
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$DIR/../.." && pwd)"
# shellcheck source=./_assert.sh
source "$DIR/_assert.sh"

SCRIPT="$PLUGIN_ROOT/scripts/install_cron.sh"

# install_cron.sh 路径硬编码 ~/.claude/.../cortex 字面量, 不接受 --plugin-root flag
make_test_home() {
  local home; home=$(mktemp -d)
  mkdir -p "$home/.cortex"
  printf '{"vault":"/tmp/test-vault"}\n' > "$home/.cortex/config.json"
  printf '%s' "$home"
}

run_install() {
  local home; home=$(make_test_home)
  HOME="$home" bash "$SCRIPT" "$@" 2>&1
  rm -rf "$home"
}

test_default_prints_cron() {
  # cron mode: auto-write crontab (HOME isolated). Output has task table + status.
  out=$(run_install)
  assert_contains "lint.sh" "$out"
  assert_contains "dashboard.sh" "$out"
  assert_contains "digest.sh" "$out"
}

test_launchd_prints_plist() {
  # launchd mode: auto-write ~/Library/LaunchAgents (HOME isolated).
  out=$(run_install launchd 2>&1)
  assert_contains "lint" "$out"
}

test_gha_prints_yaml() {
  out=$(run_install gha)
  if [[ "$out" == *"GitHub Actions"* ]] || [[ "$out" == *"name:"* ]] || [[ "$out" == *"workflow"* ]]; then
    _TESTS_RUN=$((_TESTS_RUN + 1))
  else
    _TESTS_FAIL=$((_TESTS_FAIL + 1))
    _TESTS_RUN=$((_TESTS_RUN + 1))
    printf '  FAIL: gha output has no recognizable token: %s\n' "${out:0:200}"
  fi
}

test_unknown_kind_exits_2() {
  local home; home=$(make_test_home)
  HOME="$home" bash "$SCRIPT" totally-unknown >/dev/null 2>&1
  assert_eq "2" "$?"
  rm -rf "$home"
}

test_outputs_table() {
  out=$(run_install 2>&1)
  assert_contains "lint.sh" "$out"
  assert_contains "digest.sh" "$out"
}

run_test test_default_prints_cron                test_default_prints_cron
run_test test_launchd_prints_plist               test_launchd_prints_plist
run_test test_gha_prints_yaml                    test_gha_prints_yaml
run_test test_unknown_kind_exits_2               test_unknown_kind_exits_2
run_test test_outputs_table                      test_outputs_table
# 路径硬编码 ~/.claude/.../cortex 字面量, 不接受 --plugin-root / install_path 覆盖
# 优先级测试 + 覆盖测试 + fallback 测试全部移除

print_summary
