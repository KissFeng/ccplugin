---
type: dashboard
title: 记忆-cron 状态
role: 9 cron 执行状态 · job / last_run / duration / status / exit_code
view_query:
  kind: cron
  limit: 20
  window: 7d
view_chart: table
view_kpi:
  - {name: "job 总数", source: "count(~/.cache/cortex/cron/*.json)"}
  - {name: "成功 (24h)", source: "count(~/.cache/cortex/cron/*.json where exit_code=0 last 24h)"}
  - {name: "失败 (24h)", source: "count(~/.cache/cortex/cron/*.json where exit_code!=0 last 24h)"}
  - {name: "最近成功 job", source: "max_by(last_run, ~/.cache/cortex/cron/*.json where exit_code=0)"}
view_legend: "cron 9 job 状态表 · job 名 / last_run / duration_sec / exit_code / status。读 ~/.cache/cortex/cron/*.json。刷新: bash ~/.cortex/scripts/dashboard.sh"
view_stale_after: 24
refresh: daily
namespace: 仪表盘
last_updated: "{{UPDATED}}"
tags:
  - 仪表盘
  - dashboard
  - 记忆-cron-状态
template_version: 2
---

# 记忆-cron 状态

> [!info] 记忆-cron 状态
> 9 cron 执行状态 · job / last_run / duration / status / exit_code

<!-- DASH:BEGIN -->
> [!info] 数据待刷新
> 运行 `bash ~/.cortex/scripts/dashboard.sh` 或 `/cortex:dashboard` 后此区将被填充。
<!-- DASH:END -->

<!-- TEMPLATE_END -->
