---
type: meta
title: Entities
tags: [moc]
created: 2026-05-10
updated: 2026-05-10
preset: lyt
up: "[[../00_MOC/home]]"
---

# Entities

人 / 工具 / 项目对象 / 组织 / 服务。

```dataview
TABLE WITHOUT ID file.link AS Name, entity_kind AS Kind, updated AS Updated
FROM "20_entities"
WHERE type = "entity"
SORT updated DESC
```
