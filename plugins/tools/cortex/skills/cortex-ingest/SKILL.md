---
name: cortex-ingest
description: 外部源 (文件/URL/目录) 摄取进 vault — 抽实体, 套模板 (cli=manual), wikilink 回填; URL 走 defuddle。Triggers on "ingest", "摄取".
allowed-tools: Bash Read Write Edit Glob WebFetch mcp__obsidian__obsidian_get_file_contents mcp__obsidian__obsidian_append_content mcp__obsidian__obsidian_simple_search
---

# cortex-ingest

把外部内容 (本地文件 / 网页 / 目录批量) 转成结构化 wiki 页面写入 Obsidian vault。

## 触发场景

- 用户给 URL 说 "ingest this" / "把这篇文章存到知识库"
- 用户给本地 md/pdf/txt 路径 "process this source"
- `/cortex:ingest <path|url|dir>` 显式调用
- Web Clipper 输出目录批量摄取

## 输入信号

- 位置参数 `<path|url|dir>`
- `--type concept|source|entity` 强制类型 (默认 source)
- `--dry-run` 打印计划不写盘
- `--depth N` 目录递归层数 (默认 2)

## 支持源类型

| 源 | 入口 | 默认 type |
|----|------|-----------|
| `https?://...` | `WebFetch` (或外部 `obsidian:defuddle` skill 拿 clean markdown 优先) | source |
| `*.md` `*.txt` | `Read` | source |
| `*.pdf` | `Read` (Read 自带 pdf 解析) | source |
| 目录 | `Glob` 收集 → 单文件循环 | 各文件 source |

## 流程

1. **解析 vault**

   ```bash
   VAULT="$(bash ${CLAUDE_PLUGIN_ROOT}/hooks/_lib/resolve_vault.sh)"
   ```

2. **抽要点 (启发式)**
   - H1 → 标题候选
   - H2/H3 → 段标题, 留作目录
   - frontmatter (源若是 md) → aliases / sources / authors 直接传递
   - 命名实体短语 (人名 / 工具名 / 项目名) → 候选独立 entity 页
   - 段首一句话 → "一句话定义" → 落入 `> [!info]` callout

3. **选目录 (按 prd §3.2.7 + preset)**

   | 推断类型 | LYT 路径 | Zettel | PARA |
   |----------|----------|--------|------|
   | source (URL / 文章) | `40_sources/<kebab>.md` | `references/<UID>-<slug>.md` | `3_resources/sources/<kebab>.md` |
   | concept (新概念页) | `10_concepts/<kebab>.md` | `zettels/<UID>-<slug>.md` | `3_resources/<topic>/<kebab>.md` |
   | entity (人/工具/项目对象) | `20_entities/<kebab>.md` | `zettels/<UID>-<entity>.md` | `2_areas/<area>/<kebab>.md` |

   preset 从 `<vault>/_meta/version.json:.preset` 读, 缺省 `lyt`。

4. **重名检测**
   - 用 `mcp__obsidian__obsidian_simple_search` 查标题与 alias
   - 命中 → 不覆盖, 改名 `<title>-2.md` `<title>-3.md` ...
   - 同时把发现的旧页路径塞进新页 frontmatter `related: [[old-page]]`

5. **套模板**
   - 优先读 `<vault>/_templates/<type>.md`
   - 不存在则读 `${CLAUDE_PLUGIN_ROOT}/templates/<type>.md`
   - 替换 `{{TITLE}}` `{{CREATED}}` `{{UPDATED}}` (UTC `YYYY-MM-DD`) `{{PRESET}}` `{{URL}}` `{{AUTHOR}}`
   - 必填 frontmatter: `type`, `title`, `created`, `updated`, `tags: [cortex-auto, ingested]`
   - source 类型加 `url:` `ingested_at:` 字段

6. **写入**
   - `mcp__obsidian__obsidian_put_content` 优先, fallback `Write`
   - 检测 `<vault>/.obsidian/plugins/obsidian-git/data.json` 存在 → 文件末尾加 `<!-- cortex-pending-commit -->` (不自动 git commit, prd §10.8)

7. **反向 wikilink 回填**

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/hooks/_lib/backlink_sync.py \
     --vault "$VAULT" --source "<rel-path>"
   ```
   - JSON 输出: `{updated: [...], skipped: [...], missing: [...]}`
   - missing 列表保留为输出报告 (lint rule #3 会另行报告 dead link)

8. **更新索引**
   - `<vault>/index.md` — type 对应章节加新条目 (无章节 → 创建)
   - `<vault>/log/_index.md` — 加一条 ingest 记录 (`<UTC> ingested <rel-path> from <src>`)
   - hot.md `## 最近落档` 段顶部插入

9. **批量场景 (目录)**
   - 每个文件独立走步骤 2-8
   - 进度条形式输出: `[3/12] 处理 docs/foo.md → 40_sources/foo.md ✓`
   - 单文件失败不阻断后续, 末尾报告失败清单

## 输出格式

```markdown
摄取完成: 源 = <path|url>

新建 N 个页面:
- [[40_sources/foo.md]] (source) · obsidian://open?vault=...&file=...
- [[10_concepts/bar.md]] (concept)
- ...

反向 wikilink:
- 更新 K 处 backlinks
- 待补 dead link M 条 (见末尾)

dead links (建议: 跑 /cortex:lint --fix):
- [[Nonexistent Page]] (在 [[40_sources/foo.md]] 提及)
```

## 错误处理

- WebFetch 失败 → 单 URL 模式直接报错; 批量模式跳过该 URL 继续
- 模板缺失 → 用最小骨架 (frontmatter + H1) 写入并警告
- 写入失败 → 保留原文到 `~/.cache/cortex/ingest/<ts>-<slug>.md` 供用户手处理

## 不做

- 不修改源文件 (源是只读)
- 不调 `git commit`
- 不抓 URL 二级链接 (用户显式跑 `/cortex:ingest` 才追)
- 不抽过 5 个 entity (避免噪音; 多了让用户后续手工拆)
