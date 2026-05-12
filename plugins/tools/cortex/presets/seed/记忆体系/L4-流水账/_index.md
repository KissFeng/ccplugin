---
type: memory-level
title: L4-流水账
role: 原始事件流 · append-only · 30 天后压缩
namespace: 记忆体系
level: L4
children: [ledger, sessions]
last_updated: "{{UPDATED}}"
tags: [memory, l4, ledger]
---

<section data-role="header" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
  <span style="padding:6px 16px;background:#6b7280;color:#fff;border-radius:16px;font-weight:600">L4</span>
  <span style="font-size:18px;font-weight:600">流水账</span>
  <span style="color:#666;font-size:14px">· raw append-only, 30 天后压缩</span>
</section>

> [!quote] raw append-only · 不可编辑 · 30 天后 gzip 压缩

<section data-role="kpi" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:12px 0">
  <div data-type="stat" style="padding:12px;background:#f8fafc;border-radius:8px">
    <div style="font-size:12px;color:#666">总条目</div>
    <div style="font-size:24px;font-weight:600">{{TOTAL}}</div>
  </div>
  <div data-type="stat" style="padding:12px;background:#f8fafc;border-radius:8px">
    <div style="font-size:12px;color:#666">今日 append</div>
    <div style="font-size:24px;font-weight:600">{{TODAY_N}}</div>
  </div>
  <div data-type="stat" style="padding:12px;background:#f8fafc;border-radius:8px">
    <div style="font-size:12px;color:#666">已压缩</div>
    <div style="font-size:24px;font-weight:600">{{COMPRESSED_N}}</div>
  </div>
</section>

## 子目录

<section data-role="children" style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px">
  <div data-type="card" style="padding:12px;background:#f9fafb;border-radius:6px;border-left:3px solid #6b7280">
    <a href="ledger/_index.md"><strong>ledger</strong></a>
    <div style="font-size:12px;color:#666">YYYY-MM-DD.jsonl 流水</div>
  </div>
  <div data-type="card" style="padding:12px;background:#f9fafb;border-radius:6px;border-left:3px solid #6b7280">
    <a href="sessions/_index.md"><strong>sessions</strong></a>
    <div style="font-size:12px;color:#666">CLI session transcript</div>
  </div>
</section>

## 全部条目

```base
filters:
  - field: level
    op: eq
    value: L4
sort:
  - field: timestamp
    dir: desc
limit: 50
views:
  - type: cards
```

<details>
<summary>Policy 摘要</summary>

- 写入: append-only, immutable
- 遗忘: compress_after_days=30 (不删, 仅压缩)
- 晋级来源: 无 (L4 是源头)
- 晋级目标: L3 (情节聚合)

</details>

<section data-role="operations" style="display:flex;gap:8px;margin-top:12px">
  <a href="../../仪表盘/记忆-L4-流水.md">📊 仪表盘</a>
  <a href="../../仪表盘/固化流.md">🔄 固化流</a>
  <a href="../../主页.md">⬅ 主页</a>
</section>
