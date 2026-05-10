---
type: meta
title: Projects
tags: [moc, para, projects]
created: 2026-05-10
updated: 2026-05-10
preset: para
---

# Projects

有截止日的活跃项目。每个 `<project-name>/` 子目录一个项目。

```dataview
LIST
FROM "1_projects"
WHERE type = "domain" OR type = "meta"
SORT updated DESC
```
