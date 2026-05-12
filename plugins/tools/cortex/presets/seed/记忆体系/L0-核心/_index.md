---
type: memory-level
title: L0-核心
role: 核心记忆 · 不可篡改 · 性格/价值观/硬约束
namespace: 记忆体系
level: L0
last_updated: "{{UPDATED}}"
tags: [memory, l0, core]
---

<section data-role="header" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
  <span style="padding:6px 16px;background:#dc2626;color:#fff;border-radius:16px;font-weight:600">L0</span>
  <span style="font-size:18px;font-weight:600">核心</span>
  <span style="color:#666;font-size:14px">· 不可篡改 — identity / user / values / habits / constraints</span>
</section>

> [!warning] 不可篡改 — 性格/价值观/硬约束, 写入需用户确认 + git tag

<section data-role="kpi" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:12px 0">
  <div data-type="stat" style="padding:12px;background:#f8fafc;border-radius:8px">
    <div style="font-size:12px;color:#666">总条目</div>
    <div style="font-size:24px;font-weight:600">{{TOTAL}}</div>
  </div>
  <div data-type="stat" style="padding:12px;background:#f8fafc;border-radius:8px">
    <div style="font-size:12px;color:#666">本月新增</div>
    <div style="font-size:24px;font-weight:600">{{MONTH_NEW}}</div>
  </div>
  <div data-type="stat" style="padding:12px;background:#f8fafc;border-radius:8px">
    <div style="font-size:12px;color:#666">高频 (recall_count ≥ 10)</div>
    <div style="font-size:24px;font-weight:600">{{HOT_N}}</div>
  </div>
</section>

## 全部条目

```base
filters:
  - field: level
    op: eq
    value: L0
sort:
  - field: weight
    dir: desc
views:
  - type: cards
```

<details>
<summary>Policy 摘要</summary>

- 写入: needs_user_confirm=true + git tag + immutable_after_confirm
- 遗忘: never (永不遗忘)
- 晋级来源: L1
- 晋级阈值: 用户手动批准

</details>

<section data-role="operations" style="display:flex;gap:8px;margin-top:12px">
  <a href="../views/candidates.md">🚀 晋级候选</a>
  <a href="../../仪表盘/记忆-L0-核心.md">📊 仪表盘</a>
  <a href="../../主页.md">⬅ 主页</a>
</section>
