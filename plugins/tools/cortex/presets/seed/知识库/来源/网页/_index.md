---
type: index
title: 网页
role: 网页来源笔记
namespace: 知识库
parent: 来源
children: []
last_updated: "{{UPDATED}}"
tags: [meta, index, 网页, web]
icon: "🔗"
---

<section data-role="header" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
  <span style="font-size:24px">🔗</span>
  <h1 style="margin:0">网页</h1>
</section>

> [!info] 网页
> 网页剪藏 (按 domain 分组)

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

<section data-role="kpi-extra" style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:12px 0">
  <div data-type="stat" style="padding:12px;background:#fff7ed;border-radius:8px">
    <div style="font-size:12px;color:#666">🌍 domain 分布</div>
    <div style="font-size:14px">{{DOMAIN_DIST}}</div>
  </div>
  <div data-type="stat" style="padding:12px;background:#ecfeff;border-radius:8px">
    <div style="font-size:12px;color:#666">🔥 热度 top</div>
    <div style="font-size:14px">{{HOT_TOP}}</div>
  </div>
</section>

## 子目录

<section data-role="children-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
  <!-- cortex-dashboard 注入: 每个子目录一张 card -->
  {{CHILDREN_CARDS}}
</section>

## web 过滤视图

<details open>
<summary>按 source_kind=web 过滤</summary>

```base
filters:
  - field: source_kind
    op: eq
    value: "web"
  - field: path
    op: startswith
    value: "知识库/来源/网页/"
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
    value: "知识库/来源/网页/"
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
    value: "知识库/来源/网页/"
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
  <a href="[[来源]]">⬅ 来源</a>
  <a href="{{NEW_LINK}}">➕ 新建</a>
  <a href="{{REFRESH_LINK}}">🔄 刷新</a>
</section>
