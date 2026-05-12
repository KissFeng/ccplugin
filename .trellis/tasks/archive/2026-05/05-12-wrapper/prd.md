# PRD — wrapper 输出美化统一

## 背景

`~/.cortex/scripts/` 16 wrapper 输出风格不一:
- **已美化** (6): doctor/lint/ingest/search/save/refactor — 走 `cortex_stream_runner` → cortex_stream.py (rich 库) 渲染
- **未美化** (5): init/memory/recall/promote/consolidate — 直 `exec claude --bare`, stream-json 原生输出, 人不友好
- 其他 (5): fold/dashboard/install_cron/config/update — 内部脚本风格各异

## 目标

16 wrapper 输出全部美化:
- claude --bare 调用一律走 `cortex_stream_runner` (rich 渲染: 工具调用/思考/文本/结果)
- 顶部加 banner (job name + vault + 时间)
- 错误用红色 emoji + 退出码
- 成功用绿色 ✓
- 完成后总结 (耗时, 工具数, 写入文件)

### 不在范围
- 不改 cortex_stream.py 渲染逻辑 (已 rich)
- 不改 cron 内部脚本 (cron 自有 log)
- 不改 update.sh (plugin update CLI 自带输出)

## 设计

### 1. 5 个新 wrapper 改走 cortex_stream_runner

`scripts/install_wrappers.sh` 中 init/memory/recall/promote/consolidate 的 emit heredoc:

旧:
```bash
exec claude --bare \
  --no-session-persistence \
  --settings "$SETTINGS" \
  --max-budget-usd 0.30 \
  -p "$PROMPT" \
  --allowed-tools "..."
```

新:
```bash
# 复用 stream_progress.sh 获取 cortex_stream_runner (rich 渲染)
source "$INSTALL_PATH/scripts/lib/stream_progress.sh"

export CORTEX_JOB_LABEL="cortex-<job>"
cortex_stream_runner claude --bare \
  --no-session-persistence \
  --settings "$SETTINGS" \
  --max-budget-usd 0.30 \
  -p "$PROMPT" \
  --allowed-tools "..."
```

### 2. Banner 统一

每个 wrapper 开头 + 结尾:

```bash
banner() {
  printf '\033[1;36m▸ cortex %s\033[0m  vault=%s  %s\n' "$JOB_NAME" "$VAULT" "$(date '+%H:%M:%S')"
}
done_banner() {
  printf '\033[1;32m✓ done\033[0m  %ss\n' "$SECONDS"
}
err_banner() {
  printf '\033[1;31m✗ failed\033[0m  code=%d\n' "$1" >&2
}
```

走 cortex_stream_runner 时 banner 不重复 (stream 自己有 header), 仅 wrapper 边界用 banner。非 stream wrapper (init 等本身已是 stream wrapper, 移除 banner 改用 cortex_stream_runner)。

实际: cortex_stream.py 已渲染 header, banner 由 wrapper 层加 contextual info (job name) — 保持简洁。

### 3. 错误统一

```bash
# wrapper 通用 trap
trap 'err_banner $?' ERR
```

config 缺失/jq 缺失等用 colorized 错误:
```bash
err() { printf '\033[1;31m✗\033[0m %s\n' "$*" >&2; exit "${2:-4}"; }
warn() { printf '\033[1;33m⚠\033[0m %s\n' "$*" >&2; }
ok() { printf '\033[1;32m✓\033[0m %s\n' "$*"; }
```

### 4. cortex_stream.py 配合 (可选)

如果 rich 渲染对 wrapper 不显式, 加 env hint `CORTEX_JOB_LABEL` (已有) → cortex_stream.py 顶 panel 显示 job 名。当前已支持 (run.sh 已用), 仅需 5 新 wrapper 也 export 此 env。

### 5. update.sh 不动 (走 plugin update CLI, 输出已 OK)

### 6. fold/dashboard/install_cron/config 不动 (内部走 run.sh 已美化)

## 实施步骤

### Step 1: install_wrappers.sh helper 函数

加 `lib/colors.sh` 或在 install_wrappers.sh 顶部定义 emit 时注入:
```bash
WRAPPER_PRELUDE='
err() { printf "\033[1;31m✗\033[0m %s\n" "$*" >&2; exit "${2:-4}"; }
warn() { printf "\033[1;33m⚠\033[0m %s\n" "$*" >&2; }
ok() { printf "\033[1;32m✓\033[0m %s\n" "$*"; }
'
```

每个 wrapper heredoc 内开头 echo 此 PRELUDE。

或更简单: 直接每个 wrapper 内 inline `err/warn/ok` 函数 (5 行)。

### Step 2: 5 新 wrapper 改走 cortex_stream_runner

每个 wrapper:
1. `source "$INSTALL_PATH/scripts/lib/stream_progress.sh"`
2. `export CORTEX_JOB_LABEL="cortex-<job>"`
3. 把 `exec claude --bare ...` 改为 `cortex_stream_runner claude --bare ...`
4. 加 ok/err 函数 + banner (顶部 + 结尾)

### Step 3: 已美化 6 wrapper 加 banner 一致

doctor/lint/ingest/search/save/refactor 的 emit:
- 加同样的 err/warn/ok helper (统一风格)
- banner 已通过 cortex_stream_runner 显示, 不重复

### Step 4: install.sh 输出美化

`plugins/tools/cortex/install.sh`:
- 改 `[cortex] ✗ unknown arg:` 等 echo 为 colorized (红/绿/黄)
- 已部分有 ✓/✗ emoji, 加 ANSI 颜色

### Step 5: 测试

新增 `tests/python/test_wrappers_output.py`:
- 跑 install_wrappers.sh 生成
- 验证 16 wrapper 都含 colorized helper (err/warn/ok 或 printf '\033')
- 验证 5 新 wrapper 含 `cortex_stream_runner`

## 验收

- [ ] 5 新 wrapper (init/memory/recall/promote/consolidate) 走 cortex_stream_runner
- [ ] 16 wrapper 全含 err/warn/ok 或 ANSI colorized printf
- [ ] 16 wrapper bash -n PASS
- [ ] install.sh 输出 colorized (✓ ✗ ⚠)
- [ ] 235 tests + 新 wrapper output 测试 PASS
- [ ] 实跑某 wrapper (e.g. memory.sh read /tmp/...) 输出含色彩 (即使 vault 缺失也有 colorized 错误)

## 风险

| 风险 | 缓解 |
|------|------|
| ANSI 在非 tty 输出乱码 | `[ -t 1 ]` 检测, 非 tty 关闭色 |
| stream_progress.sh source 失败 (路径变) | fallback exec claude --bare (退化, 不阻塞) |
| 大量同时改, 风险冲突 | 单 agent 串行执行 |

## 子任务

5 步骤串行, 单 trellis-implement。
