---
type: index
title: 技术
role: 技术领域知识
namespace: 知识库
parent: 领域
children: [编程语言, 数据库, 基础设施, 大数据, 人工智能, 前端, 后端, 移动端, 运维]
last_updated: "{{UPDATED}}"
tags: [meta, index, 领域, 技术]
icon: "💻"
template_version: 1

---

<section data-role="header" style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
  <span style="font-size:24px">💻</span>
  <h1 style="margin:0">技术</h1>
</section>

> [!info] 技术
> 技术与工程领域

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
  <a href="知识库/领域/技术/编程语言" data-type="subcat-card" style="padding:12px;background:#dbeafe;border-radius:8px;text-decoration:none;color:inherit">
    <div style="font-weight:600">编程语言</div>
    <div style="font-size:12px;color:#666">Python/JS/Go/Rust 等</div>
  </a>
  <a href="知识库/领域/技术/数据库" data-type="subcat-card" style="padding:12px;background:#fef3c7;border-radius:8px;text-decoration:none;color:inherit">
    <div style="font-weight:600">数据库</div>
    <div style="font-size:12px;color:#666">SQL/NoSQL/时序/图</div>
  </a>
  <a href="知识库/领域/技术/基础设施" data-type="subcat-card" style="padding:12px;background:#dcfce7;border-radius:8px;text-decoration:none;color:inherit">
    <div style="font-weight:600">基础设施</div>
    <div style="font-size:12px;color:#666">云/容器/网络</div>
  </a>
  <a href="知识库/领域/技术/大数据" data-type="subcat-card" style="padding:12px;background:#fce7f3;border-radius:8px;text-decoration:none;color:inherit">
    <div style="font-weight:600">大数据</div>
    <div style="font-size:12px;color:#666">数据处理与分析</div>
  </a>
  <a href="知识库/领域/技术/人工智能" data-type="subcat-card" style="padding:12px;background:#e0e7ff;border-radius:8px;text-decoration:none;color:inherit">
    <div style="font-weight:600">人工智能</div>
    <div style="font-size:12px;color:#666">ML/LLM/CV/NLP</div>
  </a>
  <a href="知识库/领域/技术/前端" data-type="subcat-card" style="padding:12px;background:#fee2e2;border-radius:8px;text-decoration:none;color:inherit">
    <div style="font-weight:600">前端</div>
    <div style="font-size:12px;color:#666">Web/UI/框架</div>
  </a>
  <a href="知识库/领域/技术/后端" data-type="subcat-card" style="padding:12px;background:#f3e8ff;border-radius:8px;text-decoration:none;color:inherit">
    <div style="font-weight:600">后端</div>
    <div style="font-size:12px;color:#666">服务/API/架构</div>
  </a>
  <a href="知识库/领域/技术/移动端" data-type="subcat-card" style="padding:12px;background:#cffafe;border-radius:8px;text-decoration:none;color:inherit">
    <div style="font-weight:600">移动端</div>
    <div style="font-size:12px;color:#666">iOS/Android/跨端</div>
  </a>
  <a href="知识库/领域/技术/运维" data-type="subcat-card" style="padding:12px;background:#fed7aa;border-radius:8px;text-decoration:none;color:inherit">
    <div style="font-weight:600">运维</div>
    <div style="font-size:12px;color:#666">DevOps/SRE/可观测</div>
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
    value: "知识库/领域/技术/"
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
    value: "知识库/领域/技术/"
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
