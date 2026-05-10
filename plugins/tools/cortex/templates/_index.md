<!-- cortex template: _index -->
---
type: meta
title: 模板索引
aliases: [templates]
tags: [meta]
created: {{CREATED}}
updated: {{UPDATED}}
preset: {{PRESET}}
lang: {{LANG}}
---

# 模板索引

cortex 提供 6 类模板, 由 `/cortex:new <type> <title>` 自动套用。

| 类型 | 文件 | 用途 |
|------|------|------|
| concept | [[concept]] | 永恒概念 / 知识断言 |
| entity | [[entity]] | 人 / 工具 / 项目对象 |
| domain | [[domain]] | 项目域 (按 git remote) |
| dashboard | [[dashboard]] | 仪表盘 (Bases / Dataview) |
| question | [[question]] | 待办问题 / 开放探索 |
| source | [[source]] | 外部来源 (文章 / 书 / 视频) |

## frontmatter 公共字段

每个模板都含:

```yaml
type: <字面量>
title: <H1 一致>
aliases: []
tags: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
preset: lyt | zettel | para | blank
```

## 美化原语

- 优先 Obsidian **callout** (`> [!info]+`, `> [!warning]-`, `> [!quote]`) — 13 类原生支持, GitHub GFM 兼容
- 多列 KPI 才用内嵌 HTML `<div style="...">` (dashboard 顶部示例)
- 严禁 `<html>/<head>/<body>` 包裹

## 修改提示

用户可直接编辑本目录下模板, cortex-setup 默认 **不覆盖** 已存在文件。
要重置某模板, 删除后重跑 `/cortex:install <preset>`。
