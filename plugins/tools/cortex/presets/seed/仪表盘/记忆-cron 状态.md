---
type: dashboard
title: 记忆-cron 状态
role: 9 cron 执行状态 · job / last_run / duration / status / exit_code
view_query: dashboard-cron-status
refresh: daily
namespace: 仪表盘
last_updated: "{{UPDATED}}"
tags: [dashboard, cron, ops]
---

> [!info] 记忆-cron 状态
> 9 个 cron 任务的执行状态 + 健康度

<section data-role="kpi" style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">
  <div data-type="stat" style="padding:12px;background:#f0fdf4;border-radius:8px">
    <div style="font-size:12px;color:#666">✅ 成功</div>
    <div style="font-size:24px;font-weight:600;color:#16a34a">{{OK_N}}</div>
  </div>
  <div data-type="stat" style="padding:12px;background:#fef3c7;border-radius:8px">
    <div style="font-size:12px;color:#666">⏳ 运行中</div>
    <div style="font-size:24px;font-weight:600;color:#f59e0b">{{RUNNING_N}}</div>
  </div>
  <div data-type="stat" style="padding:12px;background:#fee2e2;border-radius:8px">
    <div style="font-size:12px;color:#666">❌ 失败</div>
    <div style="font-size:24px;font-weight:600;color:#dc2626">{{FAIL_N}}</div>
  </div>
  <div data-type="stat" style="padding:12px;background:#f9fafb;border-radius:8px">
    <div style="font-size:12px;color:#666">⏸ 禁用</div>
    <div style="font-size:24px;font-weight:600;color:#6b7280">{{DISABLED_N}}</div>
  </div>
</section>

## 视图

```base
{{QUERY}}
```

## 任务表

<section data-role="table" style="overflow-x:auto">

| job | cron | last_run | duration | status | exit_code |
|-----|------|----------|----------|--------|-----------|
| memory-promote | `0 02 * * *` | {{LR_1}} | {{D_1}} | {{S_1}} | {{E_1}} |
| memory-forget | `0 03 * * *` | {{LR_2}} | {{D_2}} | {{S_2}} | {{E_2}} |
| memory-compact | `0 04 * * 0` | {{LR_3}} | {{D_3}} | {{S_3}} | {{E_3}} |
| memory-consolidate | `30 04 * * 0` | {{LR_4}} | {{D_4}} | {{S_4}} | {{E_4}} |
| memory-warden | `0 05 1,15 * *` | {{LR_5}} | {{D_5}} | {{S_5}} | {{E_5}} |
| memory-archive | `0 06 1 * *` | {{LR_6}} | {{D_6}} | {{S_6}} | {{E_6}} |
| {{JOB_7}} | {{CRON_7}} | {{LR_7}} | {{D_7}} | {{S_7}} | {{E_7}} |
| {{JOB_8}} | {{CRON_8}} | {{LR_8}} | {{D_8}} | {{S_8}} | {{E_8}} |
| {{JOB_9}} | {{CRON_9}} | {{LR_9}} | {{D_9}} | {{S_9}} | {{E_9}} |

</section>

<details>
<summary>近 7 天执行趋势</summary>

```mermaid
{{CHART_TREND}}
```

</details>

<section data-role="operations" style="display:flex;gap:8px;margin-top:12px">
  <a href="../_meta/memory-policy.yaml">⚙️ policy</a>
  <a href="总览.md">📊 总览</a>
  <a href="../主页.md">⬅ 主页</a>
</section>
