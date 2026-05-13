<!-- cortex template: domain -->
<!-- DEPRECATED: domain 类型曾用于代码仓库归档, 现已统一改为 type=project, 落 知识库/项目/<host>/<org>/<repo>/. 新仓库请用 _templates/project.md. 本模板保留作向后兼容 alias. -->
---
lint-skip: true
type: domain
title: {{TITLE}}
aliases: []
tags:
  - type/domain
  - topic/<主题>
  - stack/<技术栈>
  - lang/<语言>
  - status/<active|dormant|archived>
  - host/<域名>
  - org/<组织>
  - score/<1-5>
  - created/<YYYY>
  - keyword/<关键词>
created: {{CREATED}}
updated: {{UPDATED}}
lang: {{LANG}}
cli: {{CLI}}
cli_session: {{CLI_SESSION}}
git_remote: ""    # 如 github.com/org/repo
status: active    # active | dormant | archived
related: []
template_version: 1
---

# {{TITLE}}

> [!info]+ 项目域
> **远程仓库**: <!-- git remote URL -->
> **本地路径**: <!-- 本机 checkout 位置 -->
> **状态**: active

## 概述

<!-- 项目目标、技术栈、当前阶段。 -->

## 决策记录 (decisions)

<!-- 链接到 decisions/ 子目录的页, 或在此直接记录。 -->

-

## Bug 笔记 (bugs)

-

## 通用笔记 (notes)

-

## 关联

- 涉及概念: [[]]
- 关键实体 / 工具: [[]]
- 外部来源: [[]]

<!-- TEMPLATE_END -->
