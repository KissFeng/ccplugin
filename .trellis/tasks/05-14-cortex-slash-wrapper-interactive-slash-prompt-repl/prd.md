---
title: slash wrapper --interactive 注入预设 slash prompt
status: planning
priority: P3
owner: nico
created: 2026-05-14
---

# 背景

上一 task `05-14-cortex-ingest-sh-help-cli-p` 给 10 slash wrapper 加了 `-i/--interactive` flag, 行为是 `exec claude --settings "$SETTINGS"` 进空 REPL。

用户反馈: REPL 启动后应该也**注入对应 slash command 作为第一条消息**, 让 claude 自动跑预设流程 (用户可继续追问), 而非完全空白会话。

# 设计

Claude CLI 签名: `claude [options] [command] [prompt]` — 不带 `-p` 时进交互模式, 但 positional `prompt` 仍作为第一条 user 消息发送。

## 改动

`plugins/tools/cortex/scripts/install_wrappers.sh:emit_slash()` heredoc 模板内 `--interactive` 分支:

```bash
# 改前
exec claude --settings "$SETTINGS"

# 改后
exec claude --settings "$SETTINGS" "/cortex:__NAME__"
```

1 行 (positional prompt 替换原空 REPL)。`__NAME__` 占位由 `emit_slash` 替换为具体 slash 名。

## 验收

1. 重生 wrapper: `bash plugins/tools/cortex/scripts/install_wrappers.sh --install-path <abs>`
2. 抽查 wrapper 内 `--interactive` 分支含 `exec claude --settings "$SETTINGS" "/cortex:<name>"`
3. `bash -n` 全 22 wrapper pass
4. pytest 314 pass + 9 subtests

## 风险 / 范围

- 不破坏现状 (`-p` 默认 / `--help` / `--no-commit` 行为不变)
- claude CLI positional prompt 在 interactive 模式即作初始消息, 行为已 documented
