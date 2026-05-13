---
description: 刷新 cortex 仪表盘 (按 cortex-dashboard SKILL.md 单一真相)
---

# /cortex:dashboard

[AUTO_MODE persistent: 禁询问, 自决执行, 禁中止]

执行 cortex-dashboard skill (`--dry-run` / `--force` / 路径 参数透传)。

SKILL.md 是单一真相: 8 kind 数据查询 (memory/knowledge/ledger/cron/bridge/distribution/promotion/warden) + 7 chart 渲染 (pie/sankey/heatmap/timeline/mindmap/table/grid, 含 mermaid fallback) + DASH:BEGIN/END 区注入 (KPI callout + chart + Top-N + LEGEND)。

严禁 N/A / 占位; 数据源缺失 → 报 error 不写盘, 保留上次渲染。

输出单行 JSON: `{refreshed: [...paths], skipped: N, errors: [{path, reason}]}`。
