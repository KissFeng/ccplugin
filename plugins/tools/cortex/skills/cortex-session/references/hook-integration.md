# cortex-session — Stop hook 集成 + 增量导入

> SKILL.md 入口的 hook 自动触发流程 + `--since` 增量逻辑。

## Stop hook 集成

Claude Code SessionEnd / Stop 事件触发 cortex 注册的 hook → 加载本 skill 跑导入。

### Hook stdin 协议

hook 通过 stdin 传 JSON, 关键字段:

```json
{
  "transcript_path": "/path/to/session.jsonl",
  "session_id": "sess-abc123",
  "cwd": "/path/to/project",
  "exit_reason": "user_stop" | "context_overflow" | "error"
}
```

skill 读 `transcript_path`, 推 `--cli=claude-code` 默认值, `--sid` 取 `session_id`。

### Hook 失败回退

- transcript_path 缺 / 不存在 → 输出 warning 退 0 (不阻塞 hook 链)
- 写盘失败 → 输出 error 退 0 (Stop hook 不该阻塞用户)
- ledger 锁冲突 → 重试 3 次后跳过 ledger append, session md 仍写

## 增量导入 (`--since`)

适用场景:
- 长 session (>2h) 在中途想"先归档已发生事件, 不中断"
- 手动触发再导入, 避免重复 append

行为:
1. 读 session md 已存 frontmatter `ended` 字段 (上次导入截点)
2. `--since <ISO>` 显式覆盖 (默认用上次 `ended`)
3. 仅 append 时间戳 > since 的事件到 ledger
4. 更新 session md frontmatter (`ended` / `duration_sec` / `tool_calls` 累加)
5. body 时间线追加新事件, 不覆盖已有

## 幂等保证

- 首次导入: 写新 session md
- 二次导入无 `--since`: 跳过 (skipped, exists)
- 二次导入有 `--since`: 增量 append, 更新 frontmatter
- 三次同 `--since`: 不会重复 append (按 timestamp 去重)

## 边界

- 不参与 cortex-search / cortex-recall 召回 (L4 不进语义索引)
- cortex-digest 跑时会扫 sessions 抽 pattern / 关键事件 → L0 patterns / L2 候选
