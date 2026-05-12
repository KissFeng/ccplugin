---
description: 更新 ccplugin-market + cortex plugin 到最新版 (无入参)
---

# /cortex:update

[AUTO_MODE strict: 禁询问, fail-fast]

更新 cortex plugin 到最新版本。

**必须**用 Bash 工具按序执行:

```bash
claude plugins marketplace update ccplugin-market
claude plugins update cortex@ccplugin-market
```

报告各命令 exit code + stdout 摘要。

## 严格禁止 (违反 = 契约失败)

shell wrapper 触发, 禁:

1. **任何"修复建议"/"建议"/"推荐操作"章节、表格、列表** (`## 修复建议`, `| 类型 | 操作 |`, `### 建议`)
2. **任何用户确认问句** (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号)
3. **AskUserQuestion 调用** (allowed-tools 已禁)
4. **"下一步" / "后续" / "如需" / "可选"导引语**
5. **针对未 autofix / 非自动项的人工操作引导**

遇歧义按**推荐默认值**直接执行, 不询问用户。
