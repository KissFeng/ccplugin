# cortex-promote — 晋级阈值与重复检测算法

> SKILL.md 入口的 policy 校验 + 三层重复检测算法详解。

## policy 校验 (`_meta/memory-policy.yaml`)

| 晋级路径 | 阈值 | 审批 |
|---|---|---|
| L4 → L3 | `promote_criteria.ai_detected_pattern=true` | AUTO 可执行 |
| L3 → L2 | `recall_count >= 5 AND recurrence >= weekly` | AUTO 可执行 (`--auto-low=true`) |
| L2 → L1 | `recall_count >= 20 AND stable_days >= 90` | needs_user_approval |
| L1 → L0 | 无定量阈值 | 强制用户审批 + git tag |

## 候选行格式 (`记忆/views/candidates.md`)

```
- [ ] L3://episodic/<date>/<slot> → L2://semantic/<topic>  (recurrence: 5x in 7d, weight 0.6)
```

- 由 cortex-digest 自动写入
- AI 解析每行得到 (source_uri, target_uri, metadata)

## 分级处理决策

- **L4→L3 / L3→L2** (AUTO 可执行):
  - `--auto-low=true` 或 AUTO_MODE → 直接走"执行晋级"步骤
  - 否则汇总待办列表, 不执行
- **L2→L1** (needs_user_approval):
  - AUTO_MODE → **仅汇报**, 不执行
  - 交互 → AskUserQuestion 单条确认 (per uri)
- **L1→L0** (强制审批):
  - AUTO_MODE → **绝不执行**, 输出候选清单, 提示 `~/.cortex/scripts/memory.sh promote --interactive`
  - 交互 → **必须** AskUserQuestion 二次确认 (第 1 次列 brief + 影响, 第 2 次最终批准), 任一选 cancel 即终止

## 晋级算法 (三层重复检测)

扫 L4 ledger 上 7 天, 统计 (entity, topic, context) 三元组:

- freq ≥ 3 → 创建 L3 episodic 候选, auto promote (L4→L3)
- freq ≥ 5 + 跨 ≥3 天 → L3 → L2 候选 (写 candidates.md, 不自动)
- freq ≥ 10 + 跨 ≥30 天 → L2 → L1 候选

扫 L3 episodic 上 30 天: 同 topic ≥ 5 次 + last_recalled 增长 → L2 候选。
扫 L2 semantic 上 365 天: recall_count ≥ 20 + 90 天无 weight 大改 → L1 候选。
L0 永不自动, 必经用户审批。

## 级别边界速查 (详见 `_meta/memory-policy.yaml`)

| level | 边界 | 审批 | review |
|-------|------|------|--------|
| L0 | 性格/价值观/硬约束, ≤1500c, 不可逆 | user 必审 + git tag | monthly hash 检测 |
| L1 | 技能/稳定语义, ≤5000c, recall≥20+90 天稳定 | AI 自动 w≥0.8 | monthly 矛盾告警 |
| L2 | 语义, ≤3000c, 365 天时效 | AI dedupe | monthly 365 天衰减 |
| L3 | 情节, ≤2000c, 90 天时效 | AI 自动 | weekly 同事件 ≥5 抽象 L2 |
| L4 | ledger/sessions, append-only | 系统自动 | weekly 30 天 gzip 60 天归档 |

写入前按 level 校验: L0 拒自动写; L1 weight 须 ≥0.8; L2 必 dedupe; L3 无 dedupe; L4 仅 append。
