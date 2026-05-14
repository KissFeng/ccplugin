# Extraction — 析 (4 类) + 6 信号识别 + 路由表

> cortex-digest 五阶段中 §2 析 (Analyze) 与 §3 处 (Process) 路由表的详细规范。

## 1. 析 (Analyze)

**新增数据**:
- 模式聚合: 同事件类型 ≥ 5 → 抽象为 L2 语义候选
- 实体频度: 抽取高频 wikilink / tag / 标题关键词
- 决策提炼: 含 "决定/决策/选择/采纳" 段落 → 决策候选
- 疑问识别: 含 "?" / "怎么/为何" 段落 → 反思候选

**新增 vs 既有交叉**:
- 命中既有 L1/L2/L3 概念 → 标 `update_target` (待阶段 3 加深)
- 命中既有 知识库/领域 概念 → 标 `enrich_target` (待阶段 3 补例/补连)
- 与既有条目矛盾 → 标 `conflict` (待阶段 3 写反思页, 不动既有)
- 既有疑问页反向链接 ≥ 3 → 标 `concretize` (待阶段 5 清理)

## 2. repo 归属识别 (6 信号)

反思/连接/矛盾/决策 候选必跑, 6 信号并集, 任一命中即归属:

| # | 信号 | 强度 | 示例 |
|---|------|------|------|
| 1 | frontmatter `host` / `org` / `repo` 三字段齐 | 强 | `host: github.com, org: anthropics, repo: claude-code` |
| 2 | frontmatter `source_url` 含 repo 模式 | 强 | `github.com/<org>/<repo>` · `gitlab.*/<org>/<repo>` · `<host>:<port>/<org>/<repo>` |
| 3 | 正文 wikilink `[[知识库/项目/<host>/<org>/<repo>/...]]` 或 `[[<repo-name>]]` 命中已知 repo | 中 | `[[ccplugin]]` 命中 `知识库/项目/persons/lyxamour/ccplugin/` |
| 4 | 正文含 git URL | 中 | `git@github.com:<org>/<repo>.git` · `https://github.com/<org>/<repo>` |
| 5 | tag `repo/<name>` · `host/<host>` · `org/<org>` | 中 | `tags: [repo/ccplugin, org/lyxamour]` |
| 6 | 关键词匹配 `<repo-name>` 出现 ≥ 3 次 (repo 名单从 `知识库/项目/**` 现有目录拉) | 弱 | "ccplugin" 在正文出现 ≥3 次 |

识别结果落候选元数据: `route_target = 知识库/项目/<host>/<org>/<repo>/` (命中) 或 `route_target = inbox` (全无信号)。
多 repo 命中按**强信号优先** (1 > 2 > 3 > 4 > 5 > 6) 选首要 repo, 余者保留为次要 (阶段 3 加 backlink)。

## 3. 处 (Process) — 路由表

**新写 (按候选 `route_target` 路由, 反思/连接/矛盾/决策 4 类)**:

| 候选类型 | 命中 repo (`route_target` ≠ inbox) | 未命中 (fallback inbox) |
|---|---|---|
| 反思 | `知识库/项目/<host>/<org>/<repo>/笔记/<YYYY-MM-DD>-反思-<topic>.md` | `知识库/日记/日/<YYYY-MM>/<YYYY-MM-DD>-反思-<topic>.md` |
| 连接 | a/b 同 repo: `知识库/项目/<repo>/笔记/<YYYY-MM-DD>-连接-<a-b>.md`; 跨 repo: 落 a 端 (首要), b 端写 backlink (`## 相关` 列 `[[a-side-path]]`) | `知识库/收件箱/<date>-连接-<a-b>.md` |
| 矛盾 | `知识库/项目/<repo>/笔记/<YYYY-MM-DD>-矛盾-<topic>.md` (frontmatter 列既有条目 path) | `知识库/收件箱/<date>-矛盾-<topic>.md` |
| 决策 | `知识库/项目/<repo>/主题/决策.md` append 新段 (文件不存在则新建) | `知识库/收件箱/<date>-决策-<topic>.md` |

其他新写:
- `记忆/views/consolidated/<YYYY-MM-DD>.md` 当日摘要 (主题/高频实体/决策清单)
- 概念候选 → `记忆/views/candidates.md` (待 cortex-promote 审批, **不路由到 项目/**, 记忆层独立)

**路由 fallback 规则**:
- **多 repo 候选**: 路由首要 repo (信号强度: frontmatter > source_url > wikilink > URL > tag > keyword), 其他 repo 各加 backlink 兜底 (b 端 `## 相关` 写 `[[a-side-path]]`)
- **repo 目录不存在** (`知识库/项目/<host>/<org>/<repo>/` 缺): 自动 `mkdir -p`, 同时若 `_index.md` 不存在则建 minimal stub (frontmatter 5 字段: `type: project` / `host` / `org` / `repo` / `created`, body 1 行说明)
- **笔记目录** (`知识库/项目/<repo>/笔记/`) **不存在**: 自动 `mkdir -p`
- **弱信号防误判**: 信号 6 (keyword) 单独命中且无其他强信号 → 不路由, 留 inbox

**更新既有 (学习 + 完善, 不删原文)**:
- `update_target` (L1/L2/L3 命中) → `bash ~/.cortex/scripts/memory.sh write --uri <u> --content <c> --level <l>` append 新例证/新连接, weight += 0.05 (cap 1.0)
- `enrich_target` (知识库/领域 命中) → patch 文件追加 `## 新增例证 <YYYY-MM-DD>` + 加 `[[wikilink]]`
- `conflict` → 新建 `知识库/收件箱/<date>-矛盾-<topic>.md` 列对照 (不直接改既有条目, 待人工分发)
