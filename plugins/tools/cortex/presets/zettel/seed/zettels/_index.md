---
type: meta
title: Zettels
tags: [moc, zettel]
created: 2026-05-10
updated: 2026-05-10
preset: zettel
---

# Zettels

扁平笔记池。每篇单一原子概念。命名: `YYYYMMDDHHMM-<slug>.md`, frontmatter 必含 `uid` 字段。

```dataview
TABLE WITHOUT ID file.link AS Zettel, uid, updated
FROM "zettels"
SORT updated DESC
LIMIT 30
```
