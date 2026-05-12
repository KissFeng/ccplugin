# PRD — stream_runner 系统 python3 优先 + rich 可用探测

## 背景

用户实测跑 lint.sh:
```
ModuleNotFoundError: No module named 'rich'
```

诊断链:
- 上次修 (`238ecd83`) 加 4 级探测,路径 2 选了 pipx venv python
- `~/.local/pipx/venvs/cortex-mcp/bin/python -c "import rich"` → ImportError
- pipx venv 是 Phase A **之前**装的,未含 rich
- 用户系统 python3 = miniconda 3.13,**已装 rich 14.2.0**

用户明示:
> 我不希望使用 venv, 我希望使用系统默认错 pip 安装到全局

意思:放弃 pipx venv 路径,优先系统 python3。

## 目标

`cortex_stream_runner` 路径优先级反转:
1. **优先** 系统 python3 + `import rich` 探测 (用户偏好)
2. PATH cortex-stream (兼容)
3. pipx venv python + rich 探测 (兜底,且必须探测 import rich 才走)
4. fallback warn + raw exec

`install.sh` 加 rich 检测提示。

## 范围

### 修改

- `plugins/tools/cortex/scripts/lib/stream_progress.sh` — 反转优先级 + 每路径加 rich 探测
- `plugins/tools/cortex/install.sh` — 加 rich 可用检测 step,缺则提示 `pip3 install rich`

### 不在范围

- 不动 `mcp/cortex_stream.py` (Phase A 已交付,逻辑稳)
- 不动 `mcp/pyproject.toml` (cortex-mcp 仍 pipx)
- 不动 P0-P6 / Phase A

## 详细规范

### 1. stream_progress.sh 新优先级

```bash
cortex_stream_runner() {
  local label="${CORTEX_JOB_LABEL:-cortex}"

  local _sp_dir
  _sp_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || _sp_dir=""
  local plugin_root="${CORTEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}"
  if [[ -z "$plugin_root" && -n "$_sp_dir" ]]; then
    plugin_root="$(cd "$_sp_dir/../.." 2>/dev/null && pwd)"
  fi
  local stream_script="$plugin_root/mcp/cortex_stream.py"

  # 1. (优先) 系统 python3 + import rich 探测
  if [[ -f "$stream_script" ]] && command -v python3 >/dev/null 2>&1; then
    if python3 -c "import rich" 2>/dev/null; then
      python3 "$stream_script" --label "$label" -- "$@"
      return $?
    fi
  fi

  # 2. PATH cortex-stream (兼容)
  if command -v cortex-stream >/dev/null 2>&1; then
    cortex-stream --label "$label" -- "$@"
    return $?
  fi

  # 3. pipx venv python (必须 import rich 成功才走)
  if [[ -f "$stream_script" ]]; then
    local pipx_home="${PIPX_HOME:-$HOME/.local/pipx}"
    local venv_pys=(
      "$pipx_home/venvs/cortex-mcp/bin/python"
      "$pipx_home/venvs/cortex-mcp/bin/python3"
    )
    for py in "${venv_pys[@]}"; do
      if [[ -x "$py" ]] && "$py" -c "import rich" 2>/dev/null; then
        "$py" "$stream_script" --label "$label" -- "$@"
        return $?
      fi
    done
  fi

  # 4. fallback warn
  echo "[${label}] rich not available (try: pip3 install rich), no progress UI" >&2
  "$@" --output-format stream-json --verbose
  return $?
}
```

关键改动:**所有 python 路径都加 `import rich` 探测**,确保不会跑到 ImportError。

### 2. install.sh rich 检测 step

新增函数 (在 `step_mcp_install` 后调):

```bash
step_rich_install() {
  if command -v python3 >/dev/null 2>&1 && python3 -c "import rich" 2>/dev/null; then
    log_info "rich 已装 (system python3)"
    return 0
  fi
  log_warn "rich 未在 system python3 中可用. cortex-stream 进度 UI 不可用."
  log_hint "装: pip3 install rich  (或 pip3 install --user rich)"
  return 0  # 不阻塞 install
}
```

`main()` 中 `step_mcp_install` 后追加 `step_rich_install`。

## 验收

1. 用户实测 `bash ~/.cortex/scripts/lint.sh` 应见 rich Live UI (走路径 1,系统 python3 miniconda 已装 rich)
2. `bash -n stream_progress.sh` + `bash -n install.sh` 语法绿
3. mock: 系统 python3 import rich 成功 → 路径 1
4. mock: 系统 python3 缺 rich + cortex-stream 在 PATH → 路径 2
5. mock: 都缺 → 路径 4 warn
6. `bash plugins/tools/cortex/tests/run.sh` 不回归

## 不变量

- 纯 bash, bash 3.2 兼容
- 每个 python 路径必探测 import rich 才用 (防 ImportError)
- fallback 仍 stream-json + verbose (run.sh tee 依赖)
- install.sh rich 缺不阻塞 (warn 不 exit)
- 不动 cortex_stream.py / pyproject.toml / hooks / P0-P6

## 风险

- **路径 1 失败 (系统 python3 缺 rich) + 路径 2 cortex-stream entry 未注册 (用户当前情况) → 路径 3 pipx venv 也缺 rich → 路径 4 fallback**:用户实际场景。**缓解**:系统 python3 已装 rich (诊断已确认),路径 1 直接成
- **miniconda python3 不在 PATH 的 shell**:cron 环境可能用 /usr/bin/python3,缺 rich. **缓解**:install.sh `step_rich_install` 提示 `pip3 install --user rich`
