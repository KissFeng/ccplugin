---
type: index
title: 疑问
role: 疑问反思笔记
namespace: 知识库
parent: 反思
children: []
last_updated: "{{UPDATED}}"
tags: [meta, index, 反思, 疑问]
icon: "❓"
template_version: 1

---

<section data-role="header" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
  <span style="font-size:24px">❓</span>
  <h1 style="margin:0">疑问</h1>
</section>

> [!warning] 疑问
> 悬而未决的问题 (question)

<section data-role="kpi" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:12px 0">
  <div data-type="stat" style="padding:12px;background:#f8fafc;border-radius:8px">
    <div style="font-size:12px;color:#666">📁 子目录</div>
    <div style="font-size:24px;font-weight:600">{{SUB_COUNT}}</div>
  </div>
  <div data-type="stat" style="padding:12px;background:#f8fafc;border-radius:8px">
    <div style="font-size:12px;color:#666">📄 条目</div>
    <div style="font-size:24px;font-weight:600">{{ITEM_COUNT}}</div>
  </div>
  <div data-type="stat" style="padding:12px;background:#f8fafc;border-radius:8px">
    <div style="font-size:12px;color:#666">🕐 更新</div>
    <div style="font-size:14px">{{LAST_UPDATED}}</div>
  </div>
</section>

<section data-role="breadcrumb" style="font-size:12px;color:#6b7280;margin:8px 0">
  {{BREADCRUMB}} · 路径: <code>{{CURRENT_PATH}}</code>
</section>

## 状态分组

<section data-role="status-groups" style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:12px 0">
  <div data-type="status-open" style="padding:12px;background:#fef2f2;border-radius:8px">
    <div style="font-weight:600;color:#dc2626">❓ Open</div>
    <div style="font-size:24px">{{OPEN_COUNT}}</div>
  </div>
  <div data-type="status-resolved" style="padding:12px;background:#ecfdf5;border-radius:8px">
    <div style="font-weight:600;color:#16a34a">✅ Resolved</div>
    <div style="font-size:24px">{{RESOLVED_COUNT}}</div>
  </div>
</section>

## 子目录

<section data-role="children-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
  <!-- cortex-dashboard 注入: 每个子目录一张 card -->
  {{CHILDREN_CARDS}}
</section>

## 疑问 过滤视图

<details open>
<summary>按 type=question 过滤</summary>

```base
filters:
  - field: type
    op: eq
    value: "question"
sort:
  - field: last_updated
    dir: desc
views:
  - type: cards
```

</details>

## 最近条目

<details open>
<summary>近 7 天 (top 10)</summary>

```base
filters:
  - field: path
    op: startswith
    value: "知识库/反思/疑问/"
sort:
  - field: last_updated
    dir: desc
limit: 10
views:
  - type: list
```

</details>

## 全部条目

<details>
<summary>展开全部</summary>

```base
filters:
  - field: path
    op: startswith
    value: "知识库/反思/疑问/"
sort:
  - field: created
    dir: desc
views:
  - type: cards
```

</details>

## 相关

<section data-role="related" style="display:flex;gap:6px;flex-wrap:wrap;margin:12px 0">
  {{RELATED_LINKS}}
</section>

<section data-role="operations" style="display:flex;gap:8px;margin-top:16px">
  <a href="[[反思]]">⬅ 反思</a>
  <a href="{{NEW_LINK}}">➕ 新建</a>
  <a href="{{REFRESH_LINK}}">🔄 刷新</a>
</section>

<!-- TEMPLATE_END -->
