---
description: 落档到 cortex vault — 处理 inbox 全部 (无入参) 或写指定 body
---

# /cortex:save

[AUTO_MODE strict: 禁询问, fail-fast]

落档内容到 cortex vault。

1. 从 `~/.cortex/config.json` 读 vault
2. **若 wrapper 无入参调用 (默认)**: 处理 `inbox/` 全部待归档文件:
   - 扫 `inbox/*.md` (cap 20)
   - 每个走 cortex-save SKILL 流程: masking → 推断 kind → 写盘到对应 namespace
   - 处理完移到 `inbox/.processed/<date>/`
3. 若有显式 args (用户在 claude 内调): 按 args 解析 kind/title, body 经 masking 后写盘

输出: 落档文件数 + 各 kind 分布 + 路径列表。

## 严格禁止 (违反 = 契约失败)

shell wrapper 触发, 禁:

1. **任何"修复建议"/"建议"/"推荐操作"章节、表格、列表** (`## 修复建议`, `| 类型 | 操作 |`, `### 建议`)
2. **任何用户确认问句** (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号)
3. **AskUserQuestion 调用** (allowed-tools 已禁)
4. **"下一步" / "后续" / "如需" / "可选"导引语**
5. **针对未 autofix / 非自动项的人工操作引导**

遇歧义按**推荐默认值**直接执行, 不询问用户。
