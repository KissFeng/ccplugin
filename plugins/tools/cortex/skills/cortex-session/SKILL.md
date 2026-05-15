---
name: cortex-session
description: 导入 claude code / cli transcript → 记忆/L4-流水账/sessions/, 同步关键事件 append 到 ledger。Triggers on "import session", "导入会话", "归档会话", Stop hook 自动触发.
disable-model-invocation: true
allowed-tools: Bash Read Write Glob
---

# cortex-session

解析 CLI transcript (claude code jsonl / 其他) → 写入 `记忆/L4-流水账/sessions/<cli>/<YYYY-MM>/<sid>.md` 摘要骨架; 同步 append 关键事件到 `ledger/<date>.jsonl`。

## 触发场景

- Claude Code Stop hook 自动触发 (SessionEnd 事件)
- 用户显式 "import this session" / "归档会话" / "导入 transcript"

## 关键决策树

```
1. 解析 transcript_path (hook stdin / $CLAUDE_TRANSCRIPT_PATH / --transcript)
   路径必在用户 home 内 (防 path injection); 不存在 → 退 1
2. 推导日期 → YYYY-MM 桶
3. 按 jsonl 逐行解析 (空/损坏行跳过)
4. 提取摘要: title (首条 user prompt) / tool 计数 / files_touched / errors
5. 写 session md (frontmatter + 时间线 body) — 已存且无 --since 跳过
6. append ledger jsonl (file_write / error / clarification 等关键事件)
```

frontmatter / body / ledger 格式详见 references/session-format.md。

## AUTO_MODE (wrapper / Stop hook 自动场景)

- 全自动执行, 无交互
- 已存 session md → 静默跳过
- persistent: error 自决降级 / 重试, 禁询问, 禁中止
- ledger 文件锁冲突 → 重试 3 次 (50ms), 仍失败 → warning, 不阻塞 session md 写入

## References (按需加载)

| 文件 | 用途 |
|---|---|
| [`references/session-format.md`](references/session-format.md) | transcript 解析 + frontmatter schema + ledger jsonl 格式 + 输出示例 + 错误处理 |
| [`references/hook-integration.md`](references/hook-integration.md) | Stop hook stdin 协议 + `--since` 增量导入 + 幂等保证 |
