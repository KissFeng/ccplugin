# PRD — Cortex Wrapper 实时进度可见性

## 背景

cortex wrapper 脚本 (`~/.cortex/scripts/doctor.sh`、`lint.sh`、`fold.sh`、`dashboard.sh` 等) 调用 `exec claude --bare -p` 执行 30–120 秒重型任务。`--bare -p` 默认不加 `--output-format stream-json`,claude 进程将全部输出缓冲至任务结束后一次性吐出,期间 **stdout/stderr 完全静默**。用户无任何反馈,终端看起来像卡死,体验极差。

卡死感的具体来源:

1. `exec claude --bare -p "…"` 替换当前进程,stdout 缓冲直到 claude 退出
2. wrapper 无任何 step 日志,用户不知道当前执行到哪一阶段
3. 无心跳机制,长静默期无法区分"正在工作"与"真正挂死"

## 目标

所有 cortex wrapper 在执行 claude 任务期间提供**三层实时可见性**:

- **L1 Step 进度**:wrapper 自身打阶段日志 (`[step 1/N: 加载 skill]`、`[step 2/N: 调用 claude]`)
- **L2 Stream 实时解析**:claude 以 `--output-format stream-json` 运行,stdout 经 jq filter 实时解析并将 text 增量打到 stderr;tool_use 事件打工具调用摘要
- **L3 心跳**:后台进程每 10 秒检测无新 stream 事件时打 `[still working... (Xs elapsed)]`,让用户确认系统在运行

## 范围

### 新增文件

- `plugins/tools/cortex/scripts/lib/stream_progress.sh` — 通用 stream 解析 + 心跳函数库

### 修改文件

- `plugins/tools/cortex/scripts/install_wrappers.sh` — `emit doctor.sh` 模板改为 source `stream_progress.sh` + 调 `cortex_stream_runner`
- `plugins/tools/cortex/scripts/cron/run.sh` — 末尾 claude 调用段改为通过 `cortex_stream_runner` 执行,实时解析已有 stream-json

### 不在范围

- 不动 hooks/*.sh (stop.sh、start.sh 等)
- 不动 P0–P5 已交付内容
- 不动 install.sh 主流程 (仅其调用 install_wrappers.sh 段不变)
- 不动 update.sh、install_cron.sh、config.sh wrapper (无 claude 调用)

## 详细规范

### 1. `lib/stream_progress.sh`

函数库,无副作用,必须被 source。提供两个公共接口:

```bash
# 检测 jq 可用性; 不可用时设 CORTEX_NO_JQ=1
cortex_check_jq()

# 执行 claude 命令并实时解析 stream-json
# 参数: 完整 claude 命令行 (不含 --output-format)
# 自动注入 --output-format stream-json --verbose
# 成功返回 claude exit code; jq 不可用时 fail-soft 退化为原始输出
cortex_stream_runner() { ... }
```

**心跳实现**

```bash
_cortex_heartbeat() {
  local start=$SECONDS label="${1:-cortex}"
  while true; do
    sleep 10
    echo "[${label}] still working... ($((SECONDS - start))s elapsed)" >&2
  done
}
```

在 `cortex_stream_runner` 入口启动心跳后台进程,通过 `trap EXIT` 杀掉:

```bash
_cortex_heartbeat "$LABEL" &
local HB_PID=$!
trap "kill $HB_PID 2>/dev/null; wait $HB_PID 2>/dev/null" EXIT
```

**jq filter**

```bash
_CORTEX_JQ_FILTER='
  if .type == "assistant" then
    (.message.content // []) | .[] |
    if .type == "text" then
      "[text] \(.text | ltrimstr("\n") | .[0:200])"
    elif .type == "tool_use" then
      "[tool: \(.name)] \(.input | tostring | .[0:120])"
    else empty end
  elif .type == "result" then
    if .is_error then "[FAILED] \(.result // "unknown error")"
    else "[OK] done"
    end
  else empty end
'
```

**执行逻辑**

```bash
cortex_stream_runner() {
  local label="${CORTEX_JOB_LABEL:-cortex}"

  cortex_check_jq || {
    # fail-soft: jq 不可用, 原样执行并传递 stream-json 到 stdout
    "$@" --output-format stream-json
    return $?
  }

  echo "[${label}] step 1/2: 启动 claude (stream-json 模式)" >&2

  _cortex_heartbeat "$label" &
  local HB_PID=$!
  trap "kill $HB_PID 2>/dev/null; wait $HB_PID 2>/dev/null" EXIT

  echo "[${label}] step 2/2: 等待 claude 输出..." >&2

  local rc=0
  "$@" --output-format stream-json --verbose 2>/dev/null \
    | jq -r --unbuffered "$_CORTEX_JQ_FILTER" >&2 \
    || rc=${PIPESTATUS[0]}

  kill "$HB_PID" 2>/dev/null; wait "$HB_PID" 2>/dev/null

  if [[ $rc -eq 0 ]]; then
    echo "[${label}] OK" >&2
  else
    echo "[${label}] FAILED: exit code $rc" >&2
  fi
  return $rc
}
```

`jq -r --unbuffered` 保证行输出立即刷新;stderr 写入在单进程中串行,无需额外 flock。

### 2. `install_wrappers.sh` 修改点

`emit doctor.sh` 模板段从 `exec claude --bare -p …` 改为 source + 调用:

```bash
emit doctor.sh "$(cat <<EOB
SKILL_PATH="$INSTALL_PATH/skills/cortex-doctor/SKILL.md"
[[ ! -f "\$SKILL_PATH" ]] && { echo "cortex-doctor SKILL.md missing: \$SKILL_PATH" >&2; exit 1; }
LIB_PATH="$INSTALL_PATH/scripts/lib/stream_progress.sh"
[[ ! -f "\$LIB_PATH" ]] && { echo "stream_progress.sh missing: \$LIB_PATH" >&2; exit 1; }
# shellcheck source=../lib/stream_progress.sh
source "\$LIB_PATH"
export CORTEX_JOB_LABEL="cortex-doctor"
cortex_stream_runner claude --bare -p \\
  --append-system-prompt "\$(cat "\$SKILL_PATH")" \\
  "运行 cortex 健康检查 (cortex-doctor skill), 报告 vault/config/links/dead-links 等问题, 输出可读结果" "\$@"
EOB
)"
```

wrapper 不再使用 `exec` (改为函数调用),保留当前 shell 上下文以执行 `trap EXIT`。

同样模板应用到 lint.sh / fold.sh / dashboard.sh 各 emit 段。

### 3. `cron/run.sh` 修改点

在 `source lib/config.sh` 之后追加 source stream_progress.sh,找到末尾 claude 执行段 (当前已含 `--output-format stream-json`) 替换为 `cortex_stream_runner`:

```bash
# 追加于 source config.sh 之后
source "$(dirname "${BASH_SOURCE[0]}")/../lib/stream_progress.sh"
export CORTEX_JOB_LABEL="$JOB"

# 原: claude ... --output-format stream-json
# 改: 由 cortex_stream_runner 统一注入 --output-format, 不重复传
cortex_stream_runner claude --bare -p \
  "${EXTRA_FLAGS[@]}" \
  "$PROMPT"
```

确保移除原有的 `--output-format stream-json` 参数 (避免重复)。

### 4. 心跳与 stream 交错策略

两者均写 stderr,存在输出交错风险。评估后不引入 flock:
- jq `--unbuffered` 保证行级原子写入
- 心跳每 10s 一行,stream 增量为短行,视觉上可接受交错
- 若未来需严格序列化,可在 `_cortex_heartbeat` 中加 `flock /tmp/cortex-stderr.lock`,但当前不实施

## 验收标准

| # | 条件 |
|---|------|
| 1 | `~/.cortex/scripts/doctor.sh` 执行 30s+ 任务,stderr 每 ≤5s 有新输出 (stream text 或心跳) |
| 2 | 静默超过 10s 后出现 `[cortex-doctor] still working... (Xs elapsed)` |
| 3 | 任务成功结束打 `[cortex-doctor] OK`;失败打 `[cortex-doctor] FAILED: exit code N` |
| 4 | jq 不存在时 fail-soft:claude 仍执行,不崩溃 |
| 5 | `bash -n` 检查三文件全绿 (stream_progress.sh、install_wrappers.sh、run.sh) |
| 6 | P0–P5 已交付功能不回归 (cron mutex、timeout、log rotation、git sync 等) |
| 7 | 心跳后台进程在正常/异常/超时任何退出路径均被 trap EXIT 杀掉,无僵尸进程 |
| 8 | `CORTEX_DRY_RUN=1` 路径不启动 claude,不启动心跳 |

## 不变量

- 纯 bash + jq;jq 已是 cortex 依赖,不引任何外部 progress 库
- `stream_progress.sh` 无全局副作用,可重复 source
- `cortex_stream_runner` 失败不阻塞 claude 实际执行 (fail-soft 退化)
- 心跳 PID 通过 `trap EXIT` 清理,覆盖正常退出、`set -e` 触发、信号中断
- 不破坏 `install_wrappers.sh` 的 `--no-overwrite` 语义

## 风险

| 风险 | 缓解 |
|------|------|
| claude stream-json schema 漂移,jq filter 匹配失败 | jq 解析失败不中断管道;stream 行不出现但 claude 仍执行,退化为无解析输出 |
| jq 不存在 (极简环境) | `cortex_check_jq` 检测,缺则 `CORTEX_NO_JQ=1`,fail-soft 直接 exec claude |
| `--append-system-prompt` 大 skill 文件 + 大 stream 输出双向管道阻塞 | jq 管道流式处理不积压;`--verbose` 保证 claude 持续写 stdout。测试用 30KB+ skill 覆盖 |
| 心跳与 stream stderr 交错 | 接受行级交错 (视觉可接受);不引 flock 避免 macOS 兼容问题 |
| wrapper 从 `exec` 改为函数调用后信号转发行为变化 | 验证 Ctrl-C 仍能中断 claude 子进程;必要时加 `trap 'kill $CLAUDE_PID' INT TERM` |
