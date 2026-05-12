---
type: memory-level
title: L3-短期
role: 短期记忆 · 情节记忆 90 天时效
namespace: 记忆
level: L3
children: [episodic]
last_updated: "{{UPDATED}}"
tags: [memory, l3, short-term]
template_version: 1

---

<section data-role="header" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
  <span style="padding:6px 16px;background:#16a34a;color:#fff;border-radius:16px;font-weight:600">L3</span>
  <span style="font-size:18px;font-weight:600">短期</span>
  <span style="color:#666;font-size:14px">· 情节记忆, 90 天时效</span>
</section>

> [!note] 情节记忆 · 90 天未召回则归档

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
    <div style="font-size:12px;color:#666">高频 (recall_count ≥ 3)</div>
    <div style="font-size:24px;font-weight:600">{{HOT_N}}</div>
  </div>
</section>

## 子目录

<section data-role="children" style="display:grid;grid-template-columns:repeat(1,1fr);gap:12px">
  <div data-type="card" style="padding:12px;background:#f0fdf4;border-radius:6px;border-left:3px solid #16a34a">
    <a href="episodic/_index.md"><strong>episodic</strong></a>
    <div style="font-size:12px;color:#666">YYYY-MM-DD 情节流</div>
  </div>
</section>

## 全部条目

```base
filters:
  - field: level
    op: eq
    value: L3
sort:
  - field: last_recalled
    dir: desc
views:
  - type: cards
```

<details>
<summary>Policy 摘要</summary>

- 写入: auto (自动)
- 遗忘: 90 天后, unless recall_count ≥ 3
- 晋级来源: L4
- 晋级阈值: ai_detected_pattern=true

</details>

<section data-role="operations" style="display:flex;gap:8px;margin-top:12px">
  <a href="../views/candidates.md">🚀 晋级候选</a>
  <a href="../../仪表盘/记忆-L3-短期.md">📊 仪表盘</a>
  <a href="../../主页.md">⬅ 主页</a>
</section>

<!-- TEMPLATE_END -->
