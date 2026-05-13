---
type: index
title: 学习
role: 学习领域知识
namespace: 知识库
parent: 领域
children:
- 语言
- 读书
- 课程
last_updated: '{{UPDATED}}'
tags:
- 领域
- 学习
icon: 📖
template_version: 1
---

<section data-role="header" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
  <span style="font-size:24px">📖</span>
  <h1 style="margin:0">学习</h1>
</section>

> [!info] 学习
> 学习方法与素材

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

## 子类

<section data-role="subcategories" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0">
  <a href="知识库/领域/学习/语言" data-type="subcat-card" style="padding:12px;background:#dbeafe;border-radius:8px;text-decoration:none;color:inherit">
    <div style="font-weight:600">语言</div>
    <div style="font-size:12px;color:#666">英语/日语/其他</div>
  </a>
  <a href="知识库/领域/学习/读书" data-type="subcat-card" style="padding:12px;background:#fef3c7;border-radius:8px;text-decoration:none;color:inherit">
    <div style="font-weight:600">读书</div>
    <div style="font-size:12px;color:#666">笔记/书摘/书单</div>
  </a>
  <a href="知识库/领域/学习/课程" data-type="subcat-card" style="padding:12px;background:#dcfce7;border-radius:8px;text-decoration:none;color:inherit">
    <div style="font-weight:600">课程</div>
    <div style="font-size:12px;color:#666">MOOC/视频/讲座</div>
  </a>
</section>

## 子目录

<section data-role="children-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
  <!-- cortex-dashboard 注入: 每个子目录一张 card -->
  {{CHILDREN_CARDS}}
</section>

## 最近条目

<details open>
<summary>近 7 天 (top 10)</summary>

```base
filters:
  - field: path
    op: startswith
    value: "知识库/领域/学习/"
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
    value: "知识库/领域/学习/"
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
  <a href="[[领域]]">⬅ 领域</a>
  <a href="{{NEW_LINK}}">➕ 新建</a>
  <a href="{{REFRESH_LINK}}">🔄 刷新</a>
</section>

<!-- TEMPLATE_END -->
