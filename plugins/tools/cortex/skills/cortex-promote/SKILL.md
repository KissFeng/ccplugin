---
name: cortex-promote
description: 记忆晋级 — 读 views/candidates.md 按 policy 执行 L4→L3 / L3→L2 / L2→L1 / L1→L0; L1→L0 强制 AskUserQuestion 二次确认 (AUTO_MODE 下绝不执行)。Triggers on "promote memory", "晋级", "审批候选".
disable-model-invocation: true
allowed-tools: Read Edit Glob Bash AskUserQuestion
---

# cortex-promote

读 `记忆/views/candidates.md` 中由 cortex-digest 写入的候选, 按 `_meta/memory-policy.yaml` 各级 `promote_criteria` 校验, 执行晋级 (改 frontmatter level/uri + 移文件)。L2→L1 与 L1→L0 必须人工审批。

## 触发场景

- 用户显式 "promote memory" / "审批候选" / "晋级 X"
- 月度复盘 (用户驱动, 非 cron)
- cortex-memory-warden agent 检测稳定候选时提示用户触发

## 关键决策树

```
读 candidates.md
  ↓
逐行 policy 校验 (详见 promotion-rules.md)
  ↓
分级处理:
  L4→L3 / L3→L2  → --auto-low 或 AUTO_MODE → 直接执行; 否则汇报
  L2→L1          → AUTO_MODE 仅汇报; 交互走 AskUserQuestion 单条
  L1→L0          → AUTO_MODE 绝不执行; 交互必 AskUserQuestion 二次确认 + git tag
  ↓
执行 (详见 promotion-flow.md):
  Edit frontmatter → mv 文件 → 更新 _meta/uri-index.json + candidates.md 勾选
  ↓
任一步骤失败 → 回滚 (best-effort)
```

## AUTO_MODE (wrapper / cron 传 `auto` 后缀触发)

**这是与 AUTO_MODE 强对抗的 skill**, 高级别晋级必拦截:

- 跳 AskUserQuestion, AskUserQuestion 调用在 AUTO_MODE 下被 skill 自身拦截 (视为 cancel)
- L4→L3 / L3→L2: 仅在显式 `--auto-low=true` 才执行写盘, 否则仅汇报
- L2→L1: 仅汇报, **不执行**
- L1→L0: **绝不执行**, 仅写候选清单 + 提示 `~/.cortex/scripts/promote.sh --interactive`
- persistent: error 自决降级 / 重试, 禁询问, 禁中止

## References (按需加载)

| 文件 | 用途 |
|---|---|
| [`references/promotion-rules.md`](references/promotion-rules.md) | 各级 policy 阈值 + 三层重复检测算法 + 候选行格式 + 级别边界速查 |
| [`references/promotion-flow.md`](references/promotion-flow.md) | 执行晋级具体步骤 + 索引更新 + 回滚 + 输出示例 + 错误处理 |
