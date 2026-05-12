---
description: cortex-refactor 子命令 (dry-run 默认) — 无入参时列建议
---

# /cortex:refactor

[AUTO_MODE strict: 禁询问, fail-fast]

cortex-refactor 操作。

1. 从 `~/.cortex/config.json` 读 vault
2. **若 wrapper 无入参调用 (默认)**: 扫 vault 列重构建议 (top 20):
   - rename 候选 (typo / locale 不一致)
   - merge 候选 (相似 title / overlap > 70%)
   - split 候选 (单文件 > 5KB)
   - dedupe 候选 (相同内容)
   - 输出 plan JSON, **dry-run 不落盘**
3. 若有显式 args: 执行子命令 `rename / merge / split / fold / migrate-locale / restructure / dedupe / extract / inline / graph-rebalance`
   - 默认 dry-run, 仅当 `--apply` 时落盘

输出: plan JSON (候选列表 + 影响范围 + 风险等级)。

## 严格禁止 (违反 = 契约失败)

shell wrapper 触发, 禁:

1. **任何"修复建议"/"建议"/"推荐操作"章节、表格、列表** (`## 修复建议`, `| 类型 | 操作 |`, `### 建议`)
2. **任何用户确认问句** (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号)
3. **AskUserQuestion 调用** (allowed-tools 已禁)
4. **"下一步" / "后续" / "如需" / "可选"导引语**
5. **针对未 autofix / 非自动项的人工操作引导**

遇歧义按**推荐默认值**直接执行, 不询问用户。
