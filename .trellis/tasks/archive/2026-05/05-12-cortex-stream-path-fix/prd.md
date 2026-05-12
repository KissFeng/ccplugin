# PRD — cortex_stream_runner 多路径探测

## 背景

用户实测:
```
$ bash ~/.cortex/scripts/lint.sh
[cortex-lint] cortex-stream not in PATH (pipx install cortex-mcp), no progress UI
```

但用户已 `pipx install`。诊断:
- `~/.local/pipx/venvs/cortex-mcp/bin/` 只含 `cortex-mcp`,**无 cortex-stream**
- 用户装的是 Phase A **之前**版本,新 pyproject.toml entry `cortex-stream` 未生效
- 或 cron / 非交互 shell 的 PATH 不含 `~/.local/bin`

## 目标

`cortex_stream_runner` 不依赖 console-script + PATH,直接探测 pipx venv python 并跑 `mcp/cortex_stream.py` 绝对路径。三级 fallback。

## 范围

### 修改

- `plugins/tools/cortex/scripts/lib/stream_progress.sh` — `cortex_stream_runner` 改多路径探测

### 不在范围

- 不动 `mcp/cortex_stream.py` (Phase A 已交付,逻辑稳)
- 不动 `mcp/pyproject.toml` (cortex-stream entry 仍留,新装会生效)
- 不动 install.sh / hooks / P0-P6

## 详细规范

### `cortex_stream_runner` 新逻辑

```bash
cortex_stream_runner() {
  local label="${CORTEX_JOB_LABEL:-cortex}"

  # 推断 plugin_root (基于 stream_progress.sh 自身路径)
  local _sp_dir
  _sp_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || _sp_dir=""
  local plugin_root="${CORTEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}"
  if [[ -z "$plugin_root" && -n "$_sp_dir" ]]; then
    plugin_root="$(cd "$_sp_dir/../.." 2>/dev/null && pwd)"
  fi
  local stream_script="$plugin_root/mcp/cortex_stream.py"

  # 1. PATH 内 cortex-stream
  if command -v cortex-stream >/dev/null 2>&1; then
    cortex-stream --label "$label" -- "$@"
    return $?
  fi

  # 2. pipx venv python 直跑脚本
  local venv_pys=(
    "$HOME/.local/pipx/venvs/cortex-mcp/bin/python"
    "$HOME/.local/pipx/venvs/cortex-mcp/bin/python3"
  )
  if [[ -f "$stream_script" ]]; then
    for py in "${venv_pys[@]}"; do
      if [[ -x "$py" ]]; then
        "$py" "$stream_script" --label "$label" -- "$@"
        return $?
      fi
    done
  fi

  # 3. 系统 python3 + import rich 探测
  if [[ -f "$stream_script" ]] && command -v python3 >/dev/null 2>&1; then
    if python3 -c "import rich" 2>/dev/null; then
      python3 "$stream_script" --label "$label" -- "$@"
      return $?
    fi
  fi

  # 4. fallback: warn + raw exec (保 stream-json 让 run.sh tee 仍可工作)
  echo "[${label}] no rich-capable python found (try: pipx install --force <plugin>/mcp/), no progress UI" >&2
  "$@" --output-format stream-json --verbose
  return $?
}
```

### 关键点

- `_sp_dir` 推断:`stream_progress.sh` 在 `<plugin_root>/scripts/lib/`,`../..` 即 plugin_root。Phase A 假设的 CORTEX_PLUGIN_ROOT env 可能未设,自推保兜底
- venv python 路径列举:macOS pipx 标准位置;Linux 大多相同 (Ubuntu 也用 `~/.local/pipx/`)
- 系统 python3 + rich 已装是非 pipx 用户的退化路径 (rare,但保完整性)
- fallback 4 仍跑 claude --output-format stream-json,run.sh tee 路径不破

## 验收

1. `bash -n stream_progress.sh` 语法绿
2. mock scenarios:
   - cortex-stream 在 PATH → 路径 1
   - PATH 无 cortex-stream + venv python 存在 + script 存在 → 路径 2
   - 仅系统 python3 + rich → 路径 3
   - 都没 → 路径 4 warn
3. 用户实测 `bash ~/.cortex/scripts/lint.sh` 应见 rich Live UI (走路径 2,无需重装 pipx)
4. `bash plugins/tools/cortex/tests/run.sh` 不回归

## 不变量

- 纯 bash, 不引外部 dep
- bash 3.2 兼容 (no `[[ ${arr[*]@Q} ]]`, no `mapfile`)
- 路径优先级保持: PATH console-script > pipx venv python > 系统 python3 > fallback
- 输出 stream-json + verbose 在 fallback 也保 (run.sh 上层 tee 依赖)

## 风险

- **pipx 装非默认位置**:用户 `PIPX_HOME` 自定义 → 路径 2 miss。**缓解**:加 `${PIPX_HOME:-$HOME/.local/pipx}` 展开
- **venv python 存在但 rich 未装**:跑会 ImportError. **缓解**:venv 路径 import rich 隐含 OK (pipx 装 cortex-mcp 自带 rich dep, 假设 pyproject 已含)
- **bash 数组 venv_pys 迭代**:bash 3.2 支持 `for py in "${arr[@]}"`,OK
