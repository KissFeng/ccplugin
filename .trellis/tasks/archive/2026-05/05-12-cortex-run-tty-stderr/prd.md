# PRD — cron/run.sh stderr 路由 + 所有 claude 调用统一 stream-json 流式

## 背景

用户实测 `~/.cortex/scripts/lint.sh` 仍无终端输出。

链路:
```
~/.cortex/scripts/lint.sh
  → exec bash $INSTALL/scripts/cron/lint.sh
  → exec $DIR/run.sh lint -- "$PROMPT" --allowed-tools "..."
  → run.sh 末端: cortex_stream_runner claude --bare -p ...
```

**根因**: run.sh line ~129 用 `if ! cortex_stream_runner ... 2>>"$ERR_FILE" > "$TMP_NDJSON"`。
`stream_progress.sh` 内 jq filter + 心跳 + step 日志全打到 stderr,被 `2>>"$ERR_FILE"` 吞到 `~/.cache/cortex/cron/lint-DAY.err` 文件,用户终端见不到。

用户附加要求:**所有** wrapper 调 claude 的写法,必须经 `cortex_stream_runner` 走 stream-json 流式解析(而非 raw `--bare -p`),保证 stream parse 一致。

## 目标

1. `run.sh` 修 stderr 路由: 检测 stderr 是 tty → tee 到 ERR_FILE + 终端;非 tty (cron) → 仅 ERR_FILE
2. `install_wrappers.sh` audit 所有 emit 段, 确保 wrapper 不绕开 `cortex_stream_runner` 直接 exec claude
3. `cortex-doctor` 直调 wrapper (不走 cron/run.sh) 已经 OK,无需改

## 范围

### 修改

- `plugins/tools/cortex/scripts/cron/run.sh` — stderr tty 路由
- `plugins/tools/cortex/scripts/install_wrappers.sh` — 若 audit 发现 emit 段有 raw `exec claude` 残留,改用 `cortex_stream_runner`

### 不在范围

- 不动 stream_progress.sh (已正确)
- 不动 hooks .sh / P0-P5 模块

## 详细规范

### 1. run.sh stderr 路由

当前 (~line 129):
```bash
if ! cortex_stream_runner "${CMD[@]}" 2>>"$ERR_FILE" > "$TMP_NDJSON"; then
```

改后:
```bash
# stderr: tty 则 tee 到 ERR_FILE + 终端 fd2; 非 tty (cron) 仅 ERR_FILE
if [[ -t 2 ]]; then
  # 用 process substitution + tee
  if ! cortex_stream_runner "${CMD[@]}" \
       2> >(tee -a "$ERR_FILE" >&2) \
       > "$TMP_NDJSON"; then
    rc=$?
    ...
  fi
else
  if ! cortex_stream_runner "${CMD[@]}" 2>>"$ERR_FILE" > "$TMP_NDJSON"; then
    rc=$?
    ...
  fi
fi
```

注意:
- `2> >(tee -a "$ERR_FILE" >&2)` 用 bash process substitution,把 stderr 复制到 ERR_FILE (append) 同时再发回 fd2 (终端)
- bash 3.2 支持 process substitution (zsh/bash 都 ok,sh/dash 不支持但 shebang 已是 bash)
- 双分支避免 process substitution 在 cron 无 tty 时多 fork

### 2. install_wrappers.sh emit 段 audit

grep emit_exec / emit 段确认:
- doctor.sh emit: 已用 `cortex_stream_runner claude --bare -p` ✓
- lint.sh / fold.sh / dashboard.sh emit: `exec bash $cron/<job>.sh "$@"` — 不直接调 claude,走 run.sh ✓
- 若发现任何 emit 段含 raw `exec claude ...` 而无 cortex_stream_runner → 改

预计无需改,仅 audit 确认。

### 3. 错误信息保留

cron 模式 (非 tty): ERR_FILE 保留全部 stream_progress.sh 输出, 可日志后查看
交互模式 (tty): ERR_FILE 保留全部 + 终端实时见

## 验收

1. `bash ~/.cortex/scripts/lint.sh` (交互终端) → stderr 实时见 `[cortex-lint] step 1/2 ...` + `[text] ...` + 心跳 + `[OK]` / `[FAILED]`
2. crontab 跑 lint (非 tty) → 终端无输出 (符合 cron 期望), ERR_FILE 含全部
3. ERR_FILE 内容两模式下一致 (都 append)
4. `bash -n scripts/cron/run.sh` 语法绿
5. `bash plugins/tools/cortex/tests/run.sh` 不回归 (204 python + 8 bash)
6. install_wrappers.sh 无 emit 段绕开 cortex_stream_runner 直接 exec claude

## 不变量

- 纯 bash, 禁外部 dep
- bash 3.2 兼容
- cron (非 tty) 行为完全不变 (向后兼容)
- ERR_FILE 内容不丢
- 仅一个文件改动 (run.sh; install_wrappers 仅 audit)

## 风险

- **process substitution + tee 异步**: `2> >(tee ...)` 后台 tee 进程, run.sh 退出时 tee 可能仍在 flush。**缓解**: 验收用 `sleep 0.1` 后查 ERR_FILE 完整;真实场景 claude 退出已等心跳 trap, tee 应跟得上
- **bash 3.2 vs 5 行为差**: process substitution macOS bash 3.2 支持
- **stderr 双写顺序**: tee -a 写 ERR_FILE 与终端 fd2 顺序近似一致 (buffer 大小相关), 不严格保序
