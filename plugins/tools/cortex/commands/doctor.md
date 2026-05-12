---
description: 跑 cortex 健康检查 — vault/config/links/dead-links (无入参)
---

# /cortex:doctor

[AUTO_MODE strict: 禁询问, fail-fast, 仅读不写]

按 cortex-doctor SKILL 流程跑健康检查:

1. 从 `~/.cortex/config.json` 读 vault 与 install_path
2. 检查 vault 结构 (双 namespace / seed 文件 / _meta)
3. 扫死链 (\[\[wiki-link\]\]) 与孤儿文件
4. 校验 frontmatter (kind / locale / last_updated)
5. 报告 config / links / dead-links / 路径异常

输出: 可读分级报告 (✗ critical / ⚠ warning / ✓ healthy)。

## 严格禁止 (违反 = 契约失败)

shell wrapper 触发, 禁:

1. **任何"修复建议"/"建议"/"推荐操作"章节、表格、列表** (`## 修复建议`, `| 类型 | 操作 |`, `### 建议`)
2. **任何用户确认问句** (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号)
3. **AskUserQuestion 调用** (allowed-tools 已禁)
4. **"下一步" / "后续" / "如需" / "可选"导引语**
5. **针对未 autofix / 非自动项的人工操作引导**

遇歧义按**推荐默认值**直接执行, 不询问用户。
