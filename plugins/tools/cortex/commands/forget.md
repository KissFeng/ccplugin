---
description: 跑遗忘扫描 — 低权重/过期记忆移到归档 tombstone (无入参)
---

# /cortex:forget

[AUTO_MODE strict: 禁询问, fail-fast]

按 cortex-forget SKILL 流程跑遗忘扫描:

1. 从 `~/.cortex/config.json` 读 vault
2. 扫 L3/L2 记忆: weight < 阈值 (见 `_meta/memory-policy.yaml`) 且 last_recalled 超期
3. 候选 → 移到 `归档/forgotten/<date>/` 留 tombstone (保留 URI + 简要)
4. 写 ledger 留痕 (forget 事件)
5. L0/L1 受保护永不遗忘

输出: 遗忘候选列表 + 移除文件数 + tombstone 路径。

## 严格禁止 (违反 = 契约失败)

shell wrapper 触发, 禁:

1. **任何"修复建议"/"建议"/"推荐操作"章节、表格、列表** (`## 修复建议`, `| 类型 | 操作 |`, `### 建议`)
2. **任何用户确认问句** (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号)
3. **AskUserQuestion 调用** (allowed-tools 已禁)
4. **"下一步" / "后续" / "如需" / "可选"导引语**
5. **针对未 autofix / 非自动项的人工操作引导**

遇歧义按**推荐默认值**直接执行, 不询问用户。
