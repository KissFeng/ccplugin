# Memory 评分字段 (强制 frontmatter)

cortex L0-L4 记忆层强制 2 字段, 全 0.0-10.0 浮点。

## 字段定义

| 字段 | 含义 | 范围 |
|---|---|---|
| importance | 重要程度 — 核心约束/价值观 = 10, 流水账日志 = 1-3 | 0.0-10.0 |
| confidence | 可信度 — 用户明确肯定 = 10, AI 推测 = 4-6, 失败 episode = 0-3 | 0.0-10.0 |

## 按 L0-L4 层默认范围

| Level | 层 | 期望 importance | 期望 confidence |
|---|---|---|---|
| L0 | 核心 (性格/价值观/硬约束) | ≥ 8.0 | ≥ 9.0 |
| L1 | 长期 (技能/稳定语义) | ≥ 6.0 | ≥ 7.0 |
| L2 | 中期 (语义) | ≥ 4.0 | ≥ 5.0 |
| L3 | 短期 (情节) | ≥ 2.0 | ≥ 3.0 |
| L4 | 流水账 (ledger/sessions) | ≤ 3.0 | 不限 |

## digest 双路更新规则 (P8)

cortex-digest 每天跑 evolution 第 6 阶段时, 双路调整记忆评分:

### 使用信号 → importance ↑

```
new_importance = clamp(old + log10(召回次数 + wikilink 反向引用 + 1) - 0.1, 0, 10)
                                                                       ↑ 每周自然衰减
```

### 反馈信号 → confidence ↑↓

- 用户纠正语 ("不对" / "错了" / "应该是") + 引用该记忆 → confidence -= 1.0
- 用户加强语 ("对的" / "正确" / "很好") + 引用该记忆 → confidence += 0.5

## refresh_projects 不动记忆 (D5)

refresh_projects 仅作用于 `知识库/项目/`, 不动 `记忆/`。记忆评分仅 digest 调。

## lint rule frontmatter-required-scores

- 缺字段 → warn + autofix 加 stub `importance: 0.0 # TODO AI 自评` / `confidence: 0.0 # TODO AI 自评`
- 范围越界 → clamp [0, 10]
- 类型错 (str/int) → 转 float

## 一次性 migration (PR6)

旧 patterns.md `confidence: 0-1` → × 10 转 0-10 浮点。
入口: `bash ~/.cortex/scripts/migrate.sh --to=v2 [--dry-run]`。
