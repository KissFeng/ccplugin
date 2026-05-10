---
type: meta
title: Questions
tags: [moc]
created: 2026-05-10
updated: 2026-05-10
preset: lyt
up: "[[../00_MOC/home]]"
---

# Questions

开放问题 / 待办探索。

## 开放中

```dataview
LIST
FROM "50_questions"
WHERE type = "question" AND status = "open"
SORT priority DESC, updated DESC
```

## 探索中

```dataview
LIST
FROM "50_questions"
WHERE type = "question" AND status = "exploring"
SORT updated DESC
```
