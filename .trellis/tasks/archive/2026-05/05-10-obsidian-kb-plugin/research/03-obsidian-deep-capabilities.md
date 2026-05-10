# Research 03 — Obsidian 深度能力地图 + cortex 利用清单

- **Query**: Obsidian 本体 + 主流插件可榨取能力 → cortex 挂钩点
- **Scope**: external (Obsidian docs / 插件 README) + internal (本机 vault + obsidian-skills)
- **Date**: 2026-05-10
- **Env**: Obsidian 1.12.7 (core: bases/canvas/templates/properties enabled), `obsidian` CLI in `/usr/local/bin/obsidian`, vault `~/persons/knowledge/obsidian`
- **Source priority**: 已安装插件 manifest > obsidian-skills 官方 SKILL.md > 上游 README > help docs URL
- **Pre-reqs read**: `research/01-obsidian-pkm-patterns.md` · `research/02-ccplugin-arch-baseline.md` · `prd.md`

---

## A. Obsidian 原生能力 × cortex 挂钩

### A.1 Properties (frontmatter) — 类型系统

Source: `obsidian-skills/skills/obsidian-markdown/references/PROPERTIES.md`

| 类型 | 字面量 | cortex 用法 |
|---|---|---|
| Text | `title: My Title` | `title`, `id` (zettel UID) |
| Number | `rating: 4.5`, `confidence: 0.8` | log 评分 / fold quality score |
| Checkbox | `archived: true` | preset 切换、stale 标记 |
| Date | `created: 2026-05-10` | **必填**（lint rule #2） |
| Datetime | `due: 2026-05-10T14:30:00` | question.md `due`, log 时间戳 |
| List | `tags: [a, b]`, `aliases:` | aliases / sources / related / up |
| Links | `parent: "[[MOC]]"` | Breadcrumbs `up`/`down`/`siblings` 字段 |

**cortex schema 增量** (覆盖 prd §3.2.1)：

```yaml
# v1 必填 7 项
type: concept|entity|source|comparison|question|fold|meta
id: 20260510-1432  # zettel UID, 文件名 fallback
title: ""
aliases: []
created: 2026-05-10
updated: 2026-05-10
status: seed|developing|mature|stale  # checkbox 等价
tags: []

# v1.1 选填 (Breadcrumbs / Metadata Menu / Dataview 共生)
up: "[[MOC]]"            # Breadcrumbs hierarchy
related: ["[[A]]"]
sources: ["[[s/abc]]"]
preset: lyt|zettel|para|blank   # 改版追溯
confidence: 0.0-1.0      # number, dataview 排序用
fileClass: <name>        # Metadata Menu schema 名
```

> 设计点：`fileClass` 让用户安装 Metadata Menu 后自动获得字段表单；不安装时该字段 lint 跳过。

### A.2 Wikilink 高级语法

Source: `obsidian-skills/skills/obsidian-markdown/SKILL.md` §Internal Links

| 语法 | 含义 | cortex 用法 |
|---|---|---|
| `[[Note]]` | 基本链接 | 普通引用 |
| `[[Note\|Display]]` | 别名展示 | log 提及实体时给 friendly name |
| `[[Note#Heading]]` | 章节锚 | dashboard 引用 `[[index#最近]]` |
| `[[Note#^block-id]]` | block 引用 | **stop hook 落档时给每个 log paragraph 自动塞 `^cortex-<sha8>`** → 后续 fold 可精准引段 |
| `[[#Heading]]` | 同文档锚 | 模板内 TOC |

**block-id 约定** (新增 lint 友好性规则)：
- 形如 `^cortex-<sha8>`（`sha8 = sha1(file_path + paragraph_text)[:8]`）
- 自动写入由 `cortex-save` skill 与 stop hook 完成；用户手写不强制
- 让 fold rollup 可写 `参见 [[2026-05/...#^cortex-a3f2c1d0]]` 而不是整页引用

### A.3 Embeds

Source: `obsidian-skills/skills/obsidian-markdown/references/EMBEDS.md`

| 语法 | cortex 用法 |
|---|---|
| `![[Note]]` | hot.md 嵌入 `![[index]]` 全文 |
| `![[Note#Heading]]` | dashboard 嵌入 `![[overview#当前焦点]]` |
| `![[Note#^block]]` | log fold 嵌入关键段 |
| `![[image.png\|300]]` | concept 模板嵌入截图、宽 300 |
| `![[doc.pdf#page=3]]` | source 类型嵌入 PDF 节选 |
| ` ```query …``` ` | 嵌入搜索结果 — dashboard 模板可用 |

### A.4 Callouts (13 类)

Source: `obsidian-skills/.../CALLOUTS.md`

类型：`note / abstract(=summary,tldr) / info / todo / tip(=hint,important) / success(=check,done) / question(=help,faq) / warning(=caution,attention) / failure(=fail,missing) / danger(=error) / bug / example / quote(=cite)`

修饰：`[!type]-` (折叠默认收起) / `[!type]+` (默认展开) / 自定义标题 / 嵌套。

**cortex 模板规范化使用**：

| 场景 | callout |
|---|---|
| 一句话定义 | `> [!abstract]` |
| 关键场景 | `> [!example]` |
| 风险/反模式 | `> [!warning]` 或 `> [!danger]` |
| 引用来源 | `> [!quote]` |
| TODO / 待发展 | `> [!todo]-` 折叠 |
| 答疑 | `> [!question]` |

> **改 prd §4.7 的 HTML 卡片为 callout** — Obsidian 原生渲染（GitHub 也支持 `> [!note]` GFM 子集），减少 HTML 维护成本。HTML grid 仅在需要并排 4+ 卡片时保留。

### A.5 Block IDs / Footnotes / Math / Mermaid / Tags

| 能力 | 语法 | cortex 用法 |
|---|---|---|
| Block ID | `段落 ^id` (单独行 for list/quote) | 见 A.2，自动 `^cortex-<sha8>` |
| Footnote | `[^1]` + `[^1]: text` 或 inline `^[note]` | source 模板批注 |
| Inline math | `$E=mc^2$` | KaTeX，concept 公式 |
| Block math | `$$ \int $$` | meta 推导 |
| Mermaid | ` ```mermaid\nflowchart ...\n``` ` | dashboard 流程；支持 sequence/class/state/gantt/flowchart/erDiagram/mindmap/timeline |
| Tag | `#a/b/c`（嵌套） | 轻用；preset 默认仅 `#concept`/`#log`/`#question` |
| Aliases | frontmatter `aliases: []` | 多别名同页（lint rule #5 防跨页冲突） |

### A.6 搜索操作符

Source: https://help.obsidian.md/plugins/search

| 操作符 | 例子 | cortex 用法 |
|---|---|---|
| `path:` | `path:wiki/concepts` | scope-restricted query |
| `tag:` | `tag:#concept` | dashboard 收集 |
| `file:` | `file:.canvas` | bases/canvas 排查 |
| `line:(a b)` | `line:(error timeout)` | log 跨行 AND |
| `block:(...)` | `block:(decision)` | block-level AND |
| `task:`, `task-todo:`, `task-done:` | `task-todo:cortex` | question.md 跨页聚合 |

`mcp__obsidian__complex_search` 接受 dataview-like 高级语法（参考 research/02 §D.2）。`obsidian search` CLI 用同套语法。

### A.7 Templates / Daily Notes / Periodic Notes

| 系统 | 来源 | cortex 关系 |
|---|---|---|
| **Templates** (核心) | `obsidian template:read/insert` | 静态变量 `{{title}} {{date}} {{time}}`；cortex 提供静态 md 模板，挂在 Templates 目录 |
| **Templater** (社区 SilentVoid13/Templater 2.20.0) | 见 §B | 动态 JS 模板；cortex 提供 `_templates/cortex-*.md` 含 `<% tp.* %>`，用户启用 Templater 后即活 |
| **Daily Notes** (核心) | `obsidian daily:read/append` | log 后端可选；cortex stop hook 把 session 摘要 `daily:append` |
| **Periodic Notes** (社区 liamcain/calendar 协同) | `obsidian periodic-note` MCP tool | wiki/log/YYYY-MM/ 目录映射 monthly periodic |

### A.8 Canvas (.canvas) — JSON Canvas 1.0

Source: `obsidian-skills/skills/json-canvas/SKILL.md` + https://jsoncanvas.org/spec/1.0/

```json
{ "nodes": [ {"id":"hex16","type":"text|file|link|group","x":0,"y":0,"width":400,"height":300} ],
  "edges": [ {"id":"hex16","fromNode":"...","toNode":"...","fromSide":"right","toSide":"left","label":"…"} ] }
```

**cortex-canvas 命令** (新增, prd §4.4 增项)：从 frontmatter `related:` + `up:` 自动布局子图 → 写 `wiki/canvases/<topic>.canvas`。布局算法用 force-directed grid (5 列、宽 400、间距 40)。

### A.9 Bases (.base) — 1.7+ 核心，已在 1.12.7 启用

Source: `obsidian-skills/skills/obsidian-bases/SKILL.md` (12.6K) + `obsidian bases` / `base:query` CLI

```yaml
# wiki/dashboards/concepts.base
filters:
  and:
    - file.path.startsWith("wiki/concepts/")
    - status != "stale"
formulas:
  age_days: 'date.now() - file.created'
properties:
  formula.age_days:
    displayName: "Age (days)"
views:
  - type: table
    name: "Concepts by status"
    order: [file.name, status, formula.age_days, updated]
    sort: [{property: updated, direction: desc}]
  - type: cards
    name: "Card view"
    order: [file.name, tags]
```

**cortex-dashboard 模板规范化用 Bases 而非 Dataview** — 理由：
1. Bases 是核心，无需用户装第三方插件；
2. CLI 原生 `base:query format=json` 让 cortex 能离线取结果；
3. Dataview 仍可在用户装了的情况下并存（`templates/dashboard-dataview.md` 备份）。

### A.10 其他核心能力快表

| 能力 | 触发 | cortex 用法 |
|---|---|---|
| Outgoing/Backlinks pane | `obsidian backlinks file=X` | lint orphan 检测（rule #4 已用 `obsidian orphans`） |
| Bookmarks | `obsidian bookmark/bookmarks` | dashboard 入口 — `cortex-setup` 自动 bookmark `index.md` / `hot.md` |
| Workspaces | `obsidian workspace:save/load` | preset 切换时保存工作区 |
| Snippets (.css) | `obsidian snippet:enable` | 可选：cortex 提供 `assets/cortex.css` 给 callout 上色，`cortex-setup` 复制并启用 |
| Hotkeys / Command Palette | `obsidian command id=` | install 后注册一组快捷命令 |
| URI scheme `obsidian://` | `obsidian://open?vault=…&file=…` | **stop hook 输出可点击链接** "已落档 → obsidian://open?vault=knowledge&file=wiki/log/2026-05/…" |
| Vault stats | `obsidian vault info=files` / `wordcount` | doctor 命令报告 |
| Web Clipper (官方扩展) | 浏览器插件输出 md → vault | cortex-ingest 接受 Web Clipper 产物目录 (`wiki/clippings/`) |
| Sync (官方付费) / Obsidian Git / Syncthing | 见 §B | 与 cortex auto-commit 协调；详见 §B.13 |
| Publish (付费) | frontmatter `publish: true` | cortex 不主推，仅文档说明哪些字段控制 |

---

## B. 主流社区插件 × cortex 挂钩点

| # | 插件 (id, version) | cortex 挂钩 | source |
|---|---|---|---|
| 1 | **Dataview** (`dataview` 0.5.68) | dashboard 备选模板（用户装则启用），写符合 `TABLE / LIST FROM` 的 frontmatter；DataviewJS 不强制 | `~/persons/knowledge/obsidian/.obsidian/plugins/dataview/manifest.json` · https://blacksmithgu.github.io/obsidian-dataview/ |
| 2 | **Templater** (`templater-obsidian` 2.20.0) | `_templates/cortex-*.md` 内嵌 `<% tp.date.now() %>` `<% tp.file.title %>`；cortex 不调 Templater API，仅产出兼容模板 | https://silentvoid13.github.io/Templater/ |
| 3 | **Bases** (core 1.12.7) | dashboard **首选** — 见 A.9 | https://help.obsidian.md/bases |
| 4 | **Smart Connections** (`smart-connections` 4.3.0) | `cortex-query` 可选调用：本地 embedding (`bge-micro-v2`，非 bge-m3) 已在 `.smart-env/multi/*.ajson`；通过 Local REST API `/smart-connections/*` 或 `obsidian command id=smart-connections:open-connections` | `~/persons/knowledge/obsidian/.smart-env/smart_env.json` |
| 5 | **Breadcrumbs** (`breadcrumbs` 4.8.3) | frontmatter 字段约定：`up` / `down` / `siblings` (cortex 模板预填 `up`)；不依赖 BC 也不冲突 | https://publish.obsidian.md/breadcrumbs-docs |
| 6 | **Metadata Menu** (`metadata-menu` 0.8.12) | cortex 模板填 `fileClass: cortex-concept` 等；用户装后自动获得字段表单与校验。**lint 不与之冲突**：cortex-lint 检 vault 结构，MM 检字段类型 | https://mdelobelle.github.io/metadatamenu/ |
| 7 | **Linter** (`obsidian-linter` 1.31.2) | 分工：Linter 管单文件格式 (yaml/heading/spacing)，cortex-lint 管 vault 结构 (orphan/dead-link/index 同步)。模板里加 `disable_yaml_check: true` if needed | https://platers.github.io/obsidian-linter/ |
| 8 | **QuickAdd** (`quickadd` 2.12.0) | `obsidian quickadd choice=<name>` CLI 可调；cortex 提供示例 `_quickadd/cortex-new-concept.json` 给用户导入；不强依赖 | https://quickadd.obsidian.guide/docs/ |
| 9 | **Tasks** (`obsidian-tasks-plugin` 8.0.0) | question.md 后端方案：用 `- [ ] #cortex/question 文本 📅 2026-05-15` 兼容 Tasks 查询；cortex-dashboard 模板嵌入 ` ```tasks\nnot done\ntag includes #cortex\n``` ` | https://publish.obsidian.md/tasks/ |
| 10 | **Kanban** (`obsidian-kanban` 2.0.51) | dashboard 备选 view：`templates/dashboard-kanban.md`，frontmatter `kanban-plugin: basic` | https://publish.obsidian.md/kanban/Obsidian+Kanban+Plugin |
| 11 | **Calendar** (`calendar` 1.5.10) | 与 `wiki/log/YYYY-MM/` 映射；提供 daily-note format `YYYY-MM-DD` 让 calendar 跳转 | — |
| 12 | **Excalidraw** (`obsidian-excalidraw-plugin` 2.22.3) | concept 模板可嵌入 `![[drawing.excalidraw\|600]]`；cortex 不创建 .excalidraw（二进制风险），仅引用 | https://github.com/zsviczian/obsidian-excalidraw-plugin |
| 13 | **Markmap / MarkMind** (`obsidian-markmind` 3.4.9) | 大纲转脑图；cortex 不强用 — fold 报告可选 markmap 渲染 | — |
| 14 | **Omnisearch** (`omnisearch` 1.28.2) | `obsidian command id=omnisearch:show-modal` 开搜索面板；cortex-query 优先 Smart Connections (语义) → MCP simple_search (关键字) → Omnisearch fallback | — |
| 15 | **Local REST API** (`obsidian-local-rest-api` 3.6.2) | port `27123` (HTTP) / `27124` (HTTPS, 自签证书) — cortex 在 MCP 不够时的 HTTP fallback；endpoint：`/vault/{path}` GET/PUT/POST/DELETE、`/search/simple/`、`/search/`、`/periodic/{period}/`、`/commands/`、`/active/`、`/open/{path}` | data.json 在 `~/persons/knowledge/obsidian/.obsidian/plugins/obsidian-local-rest-api/data.json` |
| 16 | **Obsidian Git** (`obsidian-git` 2.38.2) | 协调 auto-commit：若用户装了 OG 并启用 auto-backup，**cortex hook 不再主动 commit**；通过 vault 是否有 `.obsidian/plugins/obsidian-git/data.json` 检测，存在则 skip | — |
| 17 | **Advanced URI** (社区 alx-plt/obsidian-advanced-uri) | 未安装但常见：`obsidian://advanced-uri?...&commandid=...` 程序化触发任意命令；cortex 文档列为 power-user 选项 | https://vinzent03.github.io/obsidian-advanced-uri/ |
| 18 | **Supercharged Links** (`supercharged-links-obsidian`) | 已安装；cortex 不依赖；frontmatter `cssclass:` 兼容 |
| 19 | **Claudian** (`claudian`) | 已安装；与 CC 协作的另一插件，cortex 启动时检测并避免端口/命令冲突 |

---

## C. 三层接口能力差异矩阵

| 能力 | mcp__obsidian__\* | obsidian CLI (1.7+) | Local REST API | 推荐路径 |
|---|---|---|---|---|
| 列文件 | `list_files_in_dir/vault` | `files folder= ext=` | `GET /vault/{folder}/` | MCP |
| 读文件 | `get_file_contents` / `batch_get_file_contents` | `read file= path=` | `GET /vault/{path}` | MCP |
| 创建 | `append_content` (新文件视作追加) | `create name= content= template= silent` | `POST /vault/{path}` | **CLI** (支持 template) |
| 写覆盖 | — | `create overwrite` | `PUT /vault/{path}` | CLI / REST |
| 追加 | `append_content` | `append file= content=` | `POST /vault/{path}` (Operation: append) | MCP |
| 前置 | — | `prepend file= content=` | — | CLI |
| Patch (heading/block/frontmatter) | `patch_content` | `property:set/remove` (仅 frontmatter) | `PATCH /vault/{path}` heading/block/frontmatter | MCP / REST |
| 删除 | `delete_file` | `delete file=` | `DELETE /vault/{path}` | MCP |
| 重命名 | — | `rename file= name=` (自动更新 wikilink) | — | **CLI** (唯一会更新 backlinks) |
| 移动 | — | `move file= to=` (自动更新 wikilink) | — | **CLI** |
| 简单搜索 | `simple_search` | `search query=` | `POST /search/simple/` | MCP |
| 高级搜索 | `complex_search` (dataview) | `search:context` | `POST /search/` (dataview/jsonlogic) | MCP |
| Daily / Periodic | `periodic_note` | `daily:read/append`, `periodic-note` | `GET/POST /periodic/{period}/` | MCP |
| 近期变更 | `recent_changes` | `recents` | — | MCP |
| Properties 类型化 | (写入即 yaml) | `property:set type=` | PATCH frontmatter | **CLI** (能强制类型) |
| Backlinks | — | `backlinks file=` | — | **CLI only** |
| Outgoing links | — | `links file=` | — | **CLI only** |
| Orphans / dead-ends | — | `orphans`, `deadends`, `unresolved` | — | **CLI only** (lint 必备) |
| Tags | — | `tags`, `tag name=` | — | CLI |
| Tasks | — | `tasks`, `task ref= toggle` | — | CLI |
| Templates | — | `templates`, `template:read/insert` | — | CLI |
| Bases | — | `bases`, `base:query format=json`, `base:create`, `base:views` | — | **CLI only** |
| Canvas (.canvas) | (read/write as text) | (read/write as text) | (read/write as text) | 三者皆可 — 写 JSON |
| 命令调用 | — | `command id=` | `POST /commands/{id}/` | CLI / REST |
| 打开/聚焦文件 | — | `open file=`, `tab:open` | `POST /open/{path}` | CLI |
| Plugin reload | — | `plugin:reload id=` | — | **CLI only** |
| JS eval | — | `eval code=` | — | **CLI only** |
| 截图 / DOM | — | `dev:screenshot/dom/css` | — | **CLI only** (开发用) |
| Workspaces | — | `workspace:save/load` | — | **CLI only** |
| Bookmarks | — | `bookmark`, `bookmarks` | — | **CLI only** |
| Snippets | — | `snippet:enable/disable` | — | **CLI only** |
| Aliases | — | `aliases` | — | CLI |
| Outline | — | `outline format=tree\|md\|json` | — | CLI |
| Vault info | — | `vault info=`, `wordcount` | `GET /` | CLI |

> **结论**：CLI 是超集。MCP 覆盖 CRUD + search 已够用 v1；rename/move/orphans/bases/backlinks/eval **必须 CLI**；REST 仅在远程或 Obsidian 已运行场景有边际价值（HTTPS 自签 + apikey 校验复杂度 > CLI）。

> **教训**：prd §4.5 cortex-lint 必须依赖 CLI（`orphans` `deadends` `unresolved`），MCP 没有等价工具。需在 doctor 命令中检测 `which obsidian` 并给降级建议。

---

## D. cortex 利用清单（对 prd §3 / §4 的具体增量补丁）

| # | Patch 位置 | 具体增项 | 理由 / source |
|---|---|---|---|
| 1 | prd §3.2.1 frontmatter schema | 新增 `id` (zettel UID)、`fileClass` (Metadata Menu)、`up` (Breadcrumbs)、`confidence` (number) — 见 §A.1 | 与三个主流插件共生最低公约数 |
| 2 | prd §4.7 模板美化策略 | 把 HTML grid 改为 Obsidian callout 优先（`> [!abstract]` / `> [!example]` / `> [!warning]`），仅 4+ 卡片并排时保留 HTML | §A.4；Obsidian 原生渲染、GitHub GFM 兼容、维护成本低 |
| 3 | prd §4.4 commands | 新增 `/cortex:canvas <topic>` — 从 frontmatter `related/up` 自动生成 `.canvas` JSON | §A.8；canvas 是核心，已有 json-canvas skill 可复用 |
| 4 | prd §4.4 commands | `/cortex:install` 默认产出 `wiki/dashboards/*.base` 而非 dataview 查询；`templates/dashboard-dataview.md` 作备选 | §A.9；Bases 是核心 plugin |
| 5 | prd §4.5 skills | 新增 `cortex-bases` skill（trigger: "build dashboard", "做个仪表盘"）— 调 `obsidian base:query` 拿结果，渲染 markdown 报告 | §C 唯一-CLI 能力 |
| 6 | prd §4.2 stop.sh 行为 | 步骤 3 后追加：① 给落档每个 paragraph 自动塞 `^cortex-<sha8>` block-id；② 输出 `obsidian://open?vault=<name>&file=<path>` URI 让用户一键跳转 | §A.2 + §A.10；提升落档可引用粒度与可达性 |
| 6b | prd §4.2 hooks 全套 | 采纳 research/02 §F.4 建议：补 `PostCompact` (重注 hot.md) + `PostToolUse:Write\|Edit` (auto-commit `wiki/`)，与本研究无新增冲突 | research/02 |
| 7 | prd §4.6 lint rules | 新增 rule #11: dead-end 检测（`obsidian deadends`）；rule #12: unresolved link 同步 (`obsidian unresolved`)；rule #13: 仅 cortex 写入的 block-id 命名规范 `^cortex-<sha8>` | §C lint 必依赖 CLI |
| 8 | prd §3.1 插件目录 | 增 `assets/cortex.css` (callout 配色) + `assets/quickadd/*.json` (示例宏) — `cortex-setup` 复制并 `obsidian snippet:enable name=cortex` | §A.10 |
| 9 | prd §4.3 vault 解析 | resolve_order 第 6 步：检测 `.obsidian/plugins/obsidian-git/data.json` 存在则关闭 cortex 自动 commit (避免双写冲突) | §B.16 协调 auto-commit |
| 10 | prd §4.5 cortex-query | 三级回退：① Smart Connections (`.smart-env/` ajson 直读 OR `obsidian command id=smart-connections:*`) → ② MCP `simple_search` → ③ Omnisearch (`obsidian command id=omnisearch:show-modal`) | §B.4 + §B.14 |
| 11 | prd §4.4 commands | `/cortex:doctor` 输出表格：MCP server reachable / CLI version / 4 个核心插件状态 (bases/canvas/templates/properties) / 5 个共生社区插件检测 | §A.10 + §B 全表 |
| 12 | prd §3.2.1 hot.md 模板 | 嵌入 `![[index#最近]]` (embed) + Tasks 查询块 (` ```tasks\nnot done\ntag includes #cortex\n``` ` ) | §A.3 + §B.9 |
| 13 | 新增 prd §4.8 兼容矩阵 | 一张"用户装 X 时 cortex 行为变化"表（Obsidian Git → 关 auto-commit / Templater → 启用 `<% %>` 模板 / Metadata Menu → 启用 fileClass / Smart Connections → 启用语义 query） | §B 全表 |

---

## E. 风险 / 反模式（不要做的事）

| # | 反模式 | 原因 | source |
|---|---|---|---|
| 1 | 依赖 Dataview 渲染输出 | MCP/CLI 都拿不到渲染结果，只能拿源；用 Bases `base:query format=json` 替代 | research/02 §D.3 + §A.9 |
| 2 | 依赖 Smart Connections 的 `bge-m3` | 实测本机用 `bge-micro-v2` (`smart_env.json`)；不要 hardcode 模型名，仅引 ajson 文件 | `~/persons/knowledge/obsidian/.smart-env/smart_env.json` |
| 3 | 依赖 Obsidian Publish | 付费功能；frontmatter `publish:` 字段对未付费用户无效；仅文档提及 |
| 4 | 在 hooks 里强写 frontmatter `cssclass: cortex-*` | Linter / 用户主题可能干扰；放 callout + 默认主题色 | §B.7 |
| 5 | 自造 Tasks 语法 | 与 obsidian-tasks 8.0.0 不兼容会让用户无法聚合；用社区标准 `📅 due / ⏫ priority / #tag` | §B.9 |
| 6 | hooks 里 commit/push | 与 Obsidian Git 自动备份冲突；先检测后 skip (Patch #9) | §B.16 |
| 7 | 大量 HTML grid 模板 | 维护成本高、移动端渲染不一致；callout 优先 (Patch #2) | §A.4 |
| 8 | 用 MCP `complex_search` 模拟 dataview 渲染 | 仅返 metadata 不是渲染表格；想要表格必须 Bases | §C |
| 9 | 自动 `obsidian plugin:reload/install` | 副作用大且要求 Obsidian 运行；只在 `/cortex:doctor --fix` 提示而非自动执行 |
| 10 | 写入 `.canvas` / `.excalidraw` 二进制路径 | excalidraw 是 base64 嵌入的 .md，不是二进制；`.canvas` 是 JSON 文本可写 — 但避免在 stop hook 自动改 canvas 防止用户布局被覆盖 | §B.12 + §A.8 |
| 11 | 在 Stop hook 跑长 obsidian eval | `obsidian eval` 阻塞 main thread，session 结束不应卡顿；仅快速命令 |
| 12 | 假设用户的 daily-note 路径在 `Daily/` | Periodic Notes 用户可能改成 `wiki/log/YYYY-MM-DD`；通过 `obsidian periodic-note` MCP / `daily:read` 询问而非硬编码 |

---

## Caveats / Not Found

- 未实测 Local REST API HTTPS 自签证书在 macOS keychain 的握手行为（仅看了 `data.json` cert 字段）；HTTP 27123 端口默认 enabled，apikey 已知。建议 cortex doctor 命令实际 `curl` 一次确认。
- Smart Connections 的官方 `.smart-env/multi/*.ajson` schema 没有公开文档，需直读样本结构后再决定是否 cortex-query 直接消费 ajson（备选：仅通过 `obsidian command id=smart-connections:*` 间接调用）。
- Bases 的 `formula` 表达式语法仍在演进 (Obsidian 1.7+)；本研究采纳 `obsidian-skills/skills/obsidian-bases/SKILL.md` v1 schema，未覆盖 1.8+ 可能新增。
- "Web Clipper" 仅查到官方扩展存在，未实测产物目录命名约定，cortex-ingest 接入应留 `--clippings-dir` 参数。
- Advanced URI 插件未安装本机；URI 列表来自上游 docs，未实地验证 commandid 兼容性。

---

## 参考来源汇总

- Obsidian help 1.12.7：`obsidian help` 全命令清单（本机 `/usr/local/bin/obsidian`）
- 已安装插件 manifests：`~/persons/knowledge/obsidian/.obsidian/plugins/<id>/manifest.json`
- 官方 obsidian-skills bundle：`~/.claude/plugins/marketplaces/obsidian-skills/skills/{obsidian-cli,obsidian-markdown,obsidian-bases,json-canvas,defuddle}/SKILL.md`
- claude-obsidian-marketplace：`~/.claude/plugins/marketplaces/claude-obsidian-marketplace/`
- 本任务上下文：`research/01-obsidian-pkm-patterns.md` · `research/02-ccplugin-arch-baseline.md` · `prd.md`
- 上游文档 URL：本表格内对应行均带 helpUrl/authorUrl
