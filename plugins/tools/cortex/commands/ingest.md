---
description: 摄取源 (url/file/git/dir) 到 cortex vault — 处理 inbox urls (无入参)
---

# /cortex:ingest

[AUTO_MODE strict: 禁询问, fail-fast]

摄取外部源到 cortex vault。

1. 从 `~/.cortex/config.json` 读 vault
2. **若 wrapper 无入参调用 (默认)**: 读 `inbox/urls.txt` (一行一 URL) 全部处理:
   - 按 cortex-ingest SKILL 流程: url_security → fetch → html_sanitize → masking → save (kind=log)
   - 处理完追加到 `inbox/.processed-urls.log`
3. 若有显式 args: auto-detect url/file/git/dir 直接摄取

输出: 摄取条数 + 失败条数 + 各源路径。

## 严格禁止 (违反 = 契约失败)

shell wrapper 触发, 禁:

1. **任何"修复建议"/"建议"/"推荐操作"章节、表格、列表** (`## 修复建议`, `| 类型 | 操作 |`, `### 建议`)
2. **任何用户确认问句** (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号)
3. **AskUserQuestion 调用** (allowed-tools 已禁)
4. **"下一步" / "后续" / "如需" / "可选"导引语**
5. **针对未 autofix / 非自动项的人工操作引导**

遇歧义按**推荐默认值**直接执行, 不询问用户。
