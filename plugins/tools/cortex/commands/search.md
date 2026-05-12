---
description: 搜索 cortex vault — 多级回退 (hot → index → SC → rg → MCP); 无入参时列最近 10 条
---

# /cortex:search

[AUTO_MODE strict: 禁询问, fail-fast]

在 cortex vault 内搜索内容。

1. 从 `~/.cortex/config.json` 读 vault
2. 若用户提供 query (slash command 后跟参数), 按 cortex-search SKILL 多级回退:
   - hot.md (最近高频) → URI index → semantic 检索 → rg 正则 → MCP obsidian
3. **若无 query (wrapper 无入参调用)**: 列最近 10 条 ledger 事件 (按时间倒序) + vault stats (文件数 / 各 level 计数)

输出: 引用页路径 + 片段 (≤ 200 char)。

## 严格禁止 (违反 = 契约失败)

shell wrapper 触发, 禁:

1. **任何"修复建议"/"建议"/"推荐操作"章节、表格、列表** (`## 修复建议`, `| 类型 | 操作 |`, `### 建议`)
2. **任何用户确认问句** (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号)
3. **AskUserQuestion 调用** (allowed-tools 已禁)
4. **"下一步" / "后续" / "如需" / "可选"导引语**
5. **针对未 autofix / 非自动项的人工操作引导**

遇歧义按**推荐默认值**直接执行, 不询问用户。
