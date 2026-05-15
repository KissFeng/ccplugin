---
name: cortex-memory
description: 记忆 CRUD — URI 寻址 (L0-L4) + frontmatter 版本控制 + 遗忘扫描子流程。Triggers on "记忆写入", "memory write", "memory read", "记忆更新", "记忆删除", "forget", "遗忘".
disable-model-invocation: false
allowed-tools: Bash Read Write Edit Glob mcp__obsidian__obsidian_get_file_contents mcp__obsidian__obsidian_list_files_in_dir mcp__obsidian__obsidian_append_content
---

# cortex-memory

通过 URI 对 `记忆/L0-L4` 下的记忆条目执行 CRUD; 维护 frontmatter (weight / recall_count / last_recalled / parents / children / uri / level)。

## 触发场景

- 用户/AI 显式要求写入/读取/更新/删除一条记忆 (含 URI 或描述)
- 其他 skill (cortex-search recall, cortex-digest, cortex-promote) 内部调用做读写
- `/cortex:forget` slash / `forget.sh` wrapper / daily cron → 走 forget references

## 输入

- verb: `read` / `write` / `update` / `delete`
- uri: `L<N>://<path>` (e.g. `L2://semantic/go/goroutine`)
- 仅 write/update 需: content (markdown body), `--level`, `--weight` (0.0-1.0), `--recall_when` (string), `--ref` (知识库路径), `--parents`, `--children`
- 可选: `--full` (read 时返回完整 full 字段, 默认仅 brief)

## 关键决策树

```
verb=read  → 解析 URI → 读 frontmatter + brief (详见 crud-operations.md §read)
verb=write → policy 校验 (L0 拒 / L1 weight≥0.8 / L2 dedupe / L3/L4 自动) → 写 frontmatter + body
verb=update→ 解析 → 校验 immutable_after_confirm → 写回, created 不变
verb=delete→ L0 拒 / L1 force-user / L2-L4 archive_pending=true
forget 流程→ 走 references/forget.md (daily cron / `/cortex:forget` 触发)
```

URI 解析失败 / 路径越界 → 立即拒绝, 不写盘。

## AUTO_MODE (wrapper / cron 传 `auto` 后缀触发)

- 跳 AskUserQuestion, 按 policy 默认值跳过用户决策处
- persistent: error 自决降级 / 重试, 禁询问, 禁中止
- **特殊拒绝**:
  - L0 write/delete → 一律拒, 输出候选清单, 提示 `~/.cortex/scripts/memory.sh <verb> <uri> --interactive`
  - L1 delete → 一律拒 (同上)

## References (按需加载)

| 文件 | 用途 |
|---|---|
| [`references/crud-operations.md`](references/crud-operations.md) | read/write/update/delete 4 verb 详细流程 + URI 解析 + frontmatter 自动填 + 错误处理 |
| [`references/forget.md`](references/forget.md) | 遗忘扫描子流程 (原 cortex-forget skill 合入); `/cortex:forget` slash / `forget.sh` wrapper / daily cron 触发 |
| [`references/scoring.md`](references/scoring.md) | importance / confidence 2 评分字段强制 (lint rule 21) + 启发式 + 衰减规则 |
