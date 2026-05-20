<!-- cortex template: dashboard -->
---
lint-skip: true
type: dashboard
title: {{TITLE}}
aliases: []
view_query:
  # kind: memory|knowledge|ledger|cron|bridge|distribution|promotion|warden
  kind: memory
  # level 仅 memory/ledger 使用: L0|L1|L2|L3|L4
  level: L2
  limit: 30
  # window: 30d|7d|all
  window: 30d
# view_chart: pie|sankey|heatmap|timeline|mindmap|table|grid
view_chart: table
view_kpi:
  - {name: "总数", source: "count(记忆/<level>-*/*.md)"}
  - {name: "本周新增", source: "count(记忆/<level>-*/*.md where mtime>-7d)"}
  - {name: "过期 (>30d)", source: "count(记忆/<level>-*/*.md where mtime>+30d)"}
  - {name: "晋级候选", source: "count(记忆/<level>-*/*.md where fm.weight>=0.7)"}
view_legend: "本图怎么读 ... 刷新: bash ~/.cortex/scripts/dashboard.sh"
view_stale_after: 24
tags:
  - 仪表盘
  - dashboard
created: {{CREATED}}
updated: {{UPDATED}}
lang: {{LANG}}
cli: {{CLI}}
cli_session: {{CLI_SESSION}}
refresh: manual   # manual | daily | weekly
namespace: 仪表盘
template_version: 2
---

# {{TITLE}}

> [!info] {{TITLE}}
> 描述本仪表盘的用途与数据范围

<!-- DASH:BEGIN -->
> [!info] 数据待刷新
> 运行 `bash ~/.cortex/scripts/dashboard.sh` 或 `/cortex:dashboard` 后此区将被填充。
<!-- DASH:END -->

<!-- 备注: 维护说明、刷新策略、查询调整记录 -->

<!-- TEMPLATE_END -->
