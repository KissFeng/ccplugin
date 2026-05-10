---
type: meta
title: Sources
tags: [moc]
created: 2026-05-10
updated: 2026-05-10
preset: lyt
up: "[[../00_MOC/home]]"
---

# Sources

外部来源: 文章 / 书 / 视频 / 论文 / 演讲 / 文档 / 仓库。

```dataview
TABLE WITHOUT ID file.link AS Source, source_kind AS Kind, rating AS Rating
FROM "40_sources"
WHERE type = "source"
SORT rating DESC, updated DESC
```
