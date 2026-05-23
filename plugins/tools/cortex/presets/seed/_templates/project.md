---
type: concept
created: 2026-05-20
tags:
- type/concept
- created/2026
- topic/{{TITLE}}
- topic/概要
- topic/架构
- topic/状态-路线图
- topic/依赖
- topic/链接
- topic/关联
- keyword/组织
- keyword/仓库名
- keyword/项目
- keyword/主语言
- keyword/主题
- keyword/技术栈
---

<!-- cortex template: project -->
---
lint-skip: true
type: project
title: {{TITLE}}
aliases: []
tags:
  - type/project
  - host/<github.com|gitlab.com|local>
  - org/<组织>
  - repo/<仓库名|项目basename>
  - lang/<主语言>
  - topic/<主题>
  - stack/<技术栈>
  - source/git
  - score/<1-5>
  - maturity/<draft|stable|deprecated>
  - keyword/<关键词>
created: {{CREATED}}
updated: {{UPDATED}}
lang: {{LANG}}
cli: {{CLI}}
cli_session: {{CLI_SESSION}}
host: ""           # github.com | gitlab.com | <自建 gitlab host> | local
org: ""            # 组织 / 用户 / 团队 (local 时取项目 basename)
repo: ""           # 仓库名 (local 且单层时可空)
source_url: ""     # git remote URL (local 时可空)
score: 3
maturity: draft    # draft | stable | deprecated
status: active     # active | dormant | archived
related: []
template_version: 1
---

# {{TITLE}}

> [!info]+ {{TITLE}}
> **远程仓库**: <!-- source_url -->
> **本地路径**: <!-- 本机 checkout 位置 -->
> **状态**: active

## 概要

<!-- 一句话定位 + 项目目标。 -->

## 架构

<!-- 总览。详见 [[架构]]。 -->

## 状态 / 路线图

-

## 依赖

<!-- 关键依赖。详见 [[依赖]]。 -->

## 链接

- 子文档: [[架构]] · [[决策]] · [[陷阱]] · [[依赖]]
- 笔记目录: `笔记/`
- 决策记录: `决策/`

## 关联

- 涉及概念: [[]]
- 关键实体 / 工具: [[]]
- 外部来源: [[]]

<!-- TEMPLATE_END -->
