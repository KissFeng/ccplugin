---
name: cortex-session
description: 导入 claude code / cli transcript → 记忆/L4-流水账/sessions/, 同步关键事件 append 到 ledger。触发: "import session" / "导入会话" / Stop hook 自动触发。
disable-model-invocation: true
allowed-tools: Bash Read Write Glob
---

# cortex-session

解析 CLI transcript (claude code jsonl / 其他) → 写入 `记忆/L4-流水账/sessions/<cli>/<YYYY-MM>/<sid>.md` 摘要骨架; 同步 append 关键事件到 `ledger/<date>.jsonl`。

## 触发场景
- Claude Code Stop hook 自动触发 (SessionEnd 事件)
- 用户显式 "import this session" / "归档会话" / "导入 transcript"
- cortex-historian agent 多月汇总前的预处理

## 输入
- transcript_path: 默认从 hook stdin 的 `transcript_path` 字段, 或 `$CLAUDE_TRANSCRIPT_PATH`
- --cli: 默认 `claude-code`; 可 `aider` / `cursor` / 自定义
- --sid: 默认 transcript 文件名去后缀; 可显式覆盖
- --since: 仅导入此时间点后的事件 (用于增量, 默认全量)

## 流程

1. **解析路径**:
   - transcript 必须可读 + 在用户 home 内 (防 path injection)
   - 推导日期: 取 transcript 第一条事件的 timestamp → `YYYY-MM`
2. **读 transcript** (jsonl 每行一 event):
   - 解析: `type` (user / assistant / tool_use / tool_result / system), `timestamp`, `content`, `tool_name`, `cwd`
   - 跳过空/损坏行
3. **提取摘要**:
   - 首条 user prompt 作为 title
   - 工具调用统计: 各 tool_name 次数
   - 文件变更: 抽 Edit/Write tool 的 file_path
   - 关键 timestamps: session_start / session_end / errors
4. **写 session md**: `记忆/L4-流水账/sessions/<cli>/<YYYY-MM>/<sid>.md`
   - frontmatter:
     ```yaml
     ---
     uri: L4://session/<cli>/<sid>
     level: L4
     cli: <cli>
     sid: <sid>
     started: <ISO>
     ended: <ISO>
     duration_sec: <int>
     tool_calls: {Edit: 5, Read: 12, Bash: 3}
     files_touched: [...]
     errors: <count>
     created: <ISO>
     ---
     ```
   - body: title + 关键事件时间线 (折叠详情, 不全文)
5. **append ledger**: 每个关键事件 (tool error / file write / user clarification) → `记忆/L4-流水账/ledger/<YYYY-MM-DD>.jsonl` 一行:
   ```json
   {"ts":"...","sid":"...","kind":"file_write","path":"...","level":"L4"}
   ```
6. **幂等**: 若目标 session md 已存且 `--since` 未指定 → 跳过, 标 `(skipped, exists)`

## 输出
```
[session] import: <transcript_path>
  cli: claude-code  sid: sess-abc123  duration: 1842s
  events: 87 (user 12, assistant 12, tool 63)
  tool calls: Read=22, Edit=8, Bash=15, Glob=18
  files touched: 6
  errors: 1
  written: 记忆/L4-流水账/sessions/claude-code/2026-05/sess-abc123.md
  ledger appended: 9 events to 记忆/L4-流水账/ledger/2026-05-12.jsonl
```

## 错误处理
- transcript 不存在/不可读 → 退出 1, 不部分写入
- transcript 行 JSON 解析失败 → 跳过, 末尾汇总 invalid_lines
- 目标目录创建失败 → 退出 1
- 路径校验失败 (越界) → 拒绝
- ledger 文件锁冲突 → 重试 3 次 (50ms), 仍失败 → warning, 不阻塞 session md 写入

## AUTO_MODE 兼容
[AUTO_MODE: ...] (Stop hook 默认场景) 全自动执行, 无交互。已存 session md → 静默跳过。
