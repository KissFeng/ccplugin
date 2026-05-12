---
type: memory-level
title: L1-长期
role: 长期记忆 · 已固化技能/稳定语义
namespace: 记忆体系
level: L1
children: [procedural, semantic-stable]
last_updated: "{{UPDATED}}"
tags: [memory, l1, long-term]
template_version: 1

---

<section data-role="header" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
  <span style="padding:6px 16px;background:#ea580c;color:#fff;border-radius:16px;font-weight:600">L1</span>
  <span style="font-size:18px;font-weight:600">长期</span>
  <span style="color:#666;font-size:14px">· 高 weight 已固化技能/稳定语义</span>
</section>

> [!tip] 已固化技能与稳定语义 — AI 可提议, 用户审批写入

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

## 子目录

<section data-role="children" style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px">
  <div data-type="card" style="padding:12px;background:#fff7ed;border-radius:6px;border-left:3px solid #ea580c">
    <a href="procedural/_index.md"><strong>procedural</strong></a>
    <div style="font-size:12px;color:#666">技能 / 流程 / how-to</div>
  </div>
  <div data-type="card" style="padding:12px;background:#fff7ed;border-radius:6px;border-left:3px solid #ea580c">
    <a href="semantic-stable/_index.md"><strong>semantic-stable</strong></a>
    <div style="font-size:12px;color:#666">稳定语义 / 概念 / 定义</div>
  </div>
</section>

## 全部条目

```base
filters:
  - field: level
    op: eq
    value: L1
sort:
  - field: weight
    dir: desc
views:
  - type: cards
```

<details>
<summary>Policy 摘要</summary>

- 写入: min_weight ≥ 0.8, AI 可提议
- 遗忘: 仅用户显式删除
- 晋级来源: L2
- 晋级阈值: recall_count ≥ 20 且 stable_days ≥ 90

</details>

<section data-role="operations" style="display:flex;gap:8px;margin-top:12px">
  <a href="../views/candidates.md">🚀 晋级候选</a>
  <a href="../../仪表盘/记忆-L1-长期.md">📊 仪表盘</a>
  <a href="../../主页.md">⬅ 主页</a>
</section>

<!-- TEMPLATE_END -->
