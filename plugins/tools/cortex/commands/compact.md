---
description: 压缩 L4 raw ledger — 老 ledger 压缩归档释放空间 (无入参)
---

# /cortex:compact

[AUTO_MODE strict: 禁询问, fail-fast]

跑 L4 ledger 压缩:

1. 从 `~/.cortex/config.json` 读 vault
2. 扫 `记忆/L4-原始/ledger/` 老于 30 天的 `<week>/*.md`
3. 按周聚合为单 `<week>-compact.md` (保留时间戳 + 事件类型 + 简要)
4. 原始 raw 文件移到 `归档/ledger-raw/<year>/<week>/`
5. 更新 ledger 索引

输出: 压缩前 / 后 文件数 + 释放字节数。

## 严格禁止 (违反 = 契约失败)

shell wrapper 触发, 禁:

1. **任何"修复建议"/"建议"/"推荐操作"章节、表格、列表** (`## 修复建议`, `| 类型 | 操作 |`, `### 建议`)
2. **任何用户确认问句** (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号)
3. **AskUserQuestion 调用** (allowed-tools 已禁)
4. **"下一步" / "后续" / "如需" / "可选"导引语**
5. **针对未 autofix / 非自动项的人工操作引导**

遇歧义按**推荐默认值**直接执行, 不询问用户。
