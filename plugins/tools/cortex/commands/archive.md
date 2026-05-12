---
description: 归档执行 — 老旧/已遗忘记忆移到归档目录 (无入参)
---

# /cortex:archive

[AUTO_MODE strict: 禁询问, fail-fast]

按 cortex 归档策略执行:

1. 从 `~/.cortex/config.json` 读 vault
2. 扫 `归档/staging/` 待归档候选 (forget / promote 产物)
3. 按时间分桶: `归档/<year>/<month>/<kind>/`
4. 保留 tombstone 索引 (URI / 原路径 / 归档时间 / 原因)
5. 写 ledger 留痕

输出: 归档文件数 + 各分桶统计。

## 严格禁止 (违反 = 契约失败)

shell wrapper 触发, 禁:

1. **任何"修复建议"/"建议"/"推荐操作"章节、表格、列表** (`## 修复建议`, `| 类型 | 操作 |`, `### 建议`)
2. **任何用户确认问句** (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号)
3. **AskUserQuestion 调用** (allowed-tools 已禁)
4. **"下一步" / "后续" / "如需" / "可选"导引语**
5. **针对未 autofix / 非自动项的人工操作引导**

遇歧义按**推荐默认值**直接执行, 不询问用户。
