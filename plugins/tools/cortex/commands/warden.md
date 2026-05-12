---
description: 跑腐化检测 — 扫记忆/知识库一致性 (无入参)
---

# /cortex:warden

[AUTO_MODE strict: 禁询问, fail-fast, 仅读不写]

跑 cortex vault 腐化检测:

1. 从 `~/.cortex/config.json` 读 vault
2. 扫双 namespace 一致性: 记忆 ↔ 知识库交叉引用
3. 检测 frontmatter 字段缺失 / 类型错误
4. 检测 wiki-link 死链
5. 检测重复 title (同 namespace 内冲突)
6. 检测 weight / freq 异常 (突增/突降)

输出: 腐化等级报告 (✗ corrupted / ⚠ suspect / ✓ healthy) + 修复建议。

## 严格禁止 (违反 = 契约失败)

shell wrapper 触发, 禁:

1. **任何"修复建议"/"建议"/"推荐操作"章节、表格、列表** (`## 修复建议`, `| 类型 | 操作 |`, `### 建议`)
2. **任何用户确认问句** (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号)
3. **AskUserQuestion 调用** (allowed-tools 已禁)
4. **"下一步" / "后续" / "如需" / "可选"导引语**
5. **针对未 autofix / 非自动项的人工操作引导**

遇歧义按**推荐默认值**直接执行, 不询问用户。
