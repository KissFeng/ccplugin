---
description: 注册 cortex 定时任务 (lint/fold/dashboard/memory-*) 到 crontab (无入参)
---

# /cortex:install_cron

[AUTO_MODE strict: 禁询问, fail-fast]

注册 cortex 定时任务到系统 crontab。

**必须**用 Bash 工具执行:

```bash
INSTALL_PATH="$(jq -r .install_path ~/.cortex/config.json)"
bash "$INSTALL_PATH/scripts/install_cron.sh"
```

默认任务:
- `lint --check` 每日 03:00
- `fold` 每周日 02:00
- `dashboard` 每周日 02:30
- `memory-promote` 每周一 02:15
- `memory-forget` 每月 1 号 02:45
- `memory-consolidate` 每周日 03:00

报告注册了哪些 cron 行 + 完整 crontab 摘要。

## 严格禁止 (违反 = 契约失败)

shell wrapper 触发, 禁:

1. **任何"修复建议"/"建议"/"推荐操作"章节、表格、列表** (`## 修复建议`, `| 类型 | 操作 |`, `### 建议`)
2. **任何用户确认问句** (`需确认?`, `是否执行?`, `要继续吗?`, `ok?`, 末尾问号)
3. **AskUserQuestion 调用** (allowed-tools 已禁)
4. **"下一步" / "后续" / "如需" / "可选"导引语**
5. **针对未 autofix / 非自动项的人工操作引导**

遇歧义按**推荐默认值**直接执行, 不询问用户。
