---
type: memory-level
title: L2-中期
role: 中期记忆 · 可演化语义网络
namespace: 记忆体系
level: L2
children: [semantic]
last_updated: "{{UPDATED}}"
tags: [memory, l2, mid-term]
---

<section data-role="header" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
  <span style="padding:6px 16px;background:#ca8a04;color:#fff;border-radius:16px;font-weight:600">L2</span>
  <span style="font-size:18px;font-weight:600">中期</span>
  <span style="color:#666;font-size:14px">· 可演化语义记忆, 365 天时效</span>
</section>

> [!info] 语义记忆 · 可演化, 365 天未召回则归档

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
    <div style="font-size:12px;color:#666">高频 (recall_count ≥ 5)</div>
    <div style="font-size:24px;font-weight:600">{{HOT_N}}</div>
  </div>
</section>

## 子目录

<section data-role="children" style="display:grid;grid-template-columns:repeat(1,1fr);gap:12px">
  <div data-type="card" style="padding:12px;background:#fefce8;border-radius:6px;border-left:3px solid #ca8a04">
    <a href="semantic/_index.md"><strong>semantic</strong></a>
    <div style="font-size:12px;color:#666">topic-based 语义条目</div>
  </div>
</section>

## 全部条目

```base
filters:
  - field: level
    op: eq
    value: L2
sort:
  - field: weight
    dir: desc
views:
  - type: cards
```

<details>
<summary>Policy 摘要</summary>

- 写入: min_weight ≥ 0.5, dedupe
- 遗忘: 365 天后, unless recall_count ≥ 5
- 晋级来源: L3
- 晋级阈值: recall_count ≥ 5 且 recurrence=weekly

</details>

<section data-role="operations" style="display:flex;gap:8px;margin-top:12px">
  <a href="../views/candidates.md">🚀 晋级候选</a>
  <a href="../../仪表盘/记忆-L2-中期.md">📊 仪表盘</a>
  <a href="../../主页.md">⬅ 主页</a>
</section>
