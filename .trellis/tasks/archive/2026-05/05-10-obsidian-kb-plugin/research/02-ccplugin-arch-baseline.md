# Research: ccplugin 架构基线 + claude-obsidian/kioku 借鉴模式

- **Query**: 调研 ccplugin 现有 CC plugin 架构 + claude-obsidian / kioku 套件，为新 Obsidian KB 插件提供骨架与可借鉴模式
- **Scope**: 内部仓库 + 用户本地已安装的 marketplace plugin 缓存
- **Date**: 2026-05-10
- **Target**: `plugins/tools/obsidian-kb/`（待定名）

---

## A. ccplugin 现有 plugin 骨架对比

### A.1 plugin.json schema（核心字段）

来自 `plugins/template/.claude-plugin/plugin.json:1-45`、`plugins/tools/task/.claude-plugin/plugin.json:1-43`、`plugins/tools/notify/.claude-plugin/plugin.json:1-60`：

| 字段 | 类型 | 用途 | 备注 |
|------|------|------|------|
| `name` | str | 插件名（kebab-case） | 必填 |
| `version` | str | 与仓库根版本同步（`0.0.195`），`scripts/update_version.py` 统一 bump | 必填 |
| `description` / `author` / `homepage` / `repository` / `license` / `keywords` | meta | 市场展示 | `KissFeng` 标准块 |
| `commands` | `string[]` | 显式列出每个 `.md` 文件 | 例：`task` 无 commands；`git` 仅 `./commands/commit.md` |
| `agents` | `string[]` | 显式列出每个 agent | `task` 列 5 个、`deepresearch` 列 4 个 |
| `skills` | str（目录） | 自动扫描子目录的 `SKILL.md` | 几乎所有插件用 `"./skills/"` |
| `mcpServers` | path | 指 `./.mcp.json` | 仅 `template` 启用 |
| `outputStyles` | path | `./styles/` | 仅 `template` 提及 |
| `lspServers` | path | `./.lsp.json` | 仅 `template` 提及 |
| `hooks` | obj | 见 §B |  |

### A.2 目录约定

`plugins/tools/<name>/` 下出现的目录（`plugins/tools/task/` `plugins/tools/git/` `plugins/template/` 实际清单）：

```
.claude-plugin/plugin.json   # manifest（必需）
agents/                      # 子代理 .md（可选）
commands/                    # 斜杠命令 .md（可选）
skills/<skill-name>/SKILL.md # 渐进披露技能（可选）
scripts/                     # python 脚本（可选）
docs/                        # 长文档（可选）
.mcp.json / .lsp.json        # 协议配置（可选）
pyproject.toml + uv.lock     # python 包（当前所有插件都有，但本任务不需要）
.python-version
README.md / llms.txt         # 文档与 LLM 索引
.KissFeng/                # gitignore 区
<pkgname>.egg-info/          # 构建产物（gitignored）
```

### A.3 pyproject 模板（task / git / template 高度一致）

参考 `plugins/template/pyproject.toml:1-27`：

```toml
[project]
name = "ccplugin-template"
version = "0.0.195"
requires-python = ">=3.11"
dependencies = ["lib"]                 # 共享库
[tool.uv.sources.lib]
git = "https://github.com/KissFeng/ccplugin"
subdirectory = "lib"
rev = "master"
```

`task` 唯一差异：声明 `[project.optional-dependencies] dev = ["claude-agent-sdk", "pytest-asyncio"]`（`pyproject.toml:11-18`）。

**对新插件的含义**：用户要求"不依赖当前项目 python 生态"。可选两条路：
1. **零 python**（推荐，类似 `codex`、`deepresearch`）：不放 `scripts/`、不放 `pyproject.toml`，仅 `.claude-plugin/plugin.json` + `commands/` + `skills/` + `agents/`。`codex/` 与 `deepresearch/` 即此形态（codex 仅 1 command + 1 agent；deepresearch 仅 4 agents + skills 目录）。
2. **独立 pyproject**：保留 `scripts/`，但 `dependencies` 列表里删掉 `lib`，不写 `[tool.uv.sources.lib]`。代价是无法复用 `lib.hooks.load_hooks` / `lib.utils.gitignore` 等 helper。

### A.4 五插件骨架对照

| 插件 | commands | agents | skills | scripts | pyproject | hooks | 特征 |
|------|----------|--------|--------|---------|-----------|-------|------|
| `template` | 1 | 2 | 1 (skill-template) | example.py | yes（`lib`） | SessionStart | 起点 |
| `task` | 0 | 5 | 9 (align/plan/exec/...) | main.py + hooks.py + task.py + test.py | yes（`lib` + click） | SessionStart | 最复杂 |
| `git` | 1 (commit) | 0 | 多个 | main.py + hooks.py | yes（`lib` + click） | SessionStart async | 命令型 |
| `codex` | 1 (exec) | 1 (codex) | 0 | 无 | 无 | 无 | **极简型** |
| `deepresearch` | 0 | 4 | yes | 无 | 无 | 无 | **agent + skill 纯声明型** |
| `notify` | 0 | 0 | 0 | main.py + hooks.py + notify.py + config.py | yes | SessionStart/UserPromptSubmit/PreToolUse/PermissionRequest | hook-driven 通知 |

新插件最贴近的参考：**`deepresearch`（纯声明）+ `codex`（commands+agent）的组合**，不要照搬 `task`。

---

## B. Hook 注入模式

### B.1 plugin.json 的 hooks 块（标准 shape）

`plugins/tools/git/.claude-plugin/plugin.json:26-39` 是最简 SessionStart：

```json
"hooks": {
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "PLUGIN_NAME=git uv run --directory ${CLAUDE_PLUGIN_ROOT} ./scripts/main.py hooks",
          "async": true,
          "timeout": 500
        }
      ]
    }
  ]
}
```

`notify` 在同一 manifest 注册 4 个事件（`SessionStart` / `UserPromptSubmit` / `PreToolUse` / `PermissionRequest`，`plugins/tools/notify/.claude-plugin/plugin.json:20-60`），全部走 `notify/scripts/main.py hooks` 同一入口。

### B.2 脚本 shape（hook handler 范式）

入口 `plugins/tools/task/scripts/main.py:1-30` — 用 click 把 `hooks` 注册成子命令。`hooks.py` 调用 `lib.hooks.load_hooks()`：

`lib/hooks/hook.py:28-79` 是仓库标准 hook 协议：

1. `json.load(sys.stdin)` 读输入
2. 按 `hook_event_name` 分支
3. SessionStart 事件下，自动把同插件的 `AGENT.md` 替换 `${CLAUDE_PLUGIN_ROOT}` 后 `print` 到 stdout（即 `additionalContext` 注入）
4. 敏感字段 redact（`_SENSITIVE_KEYS`）

`task` 在此基础上扩展：`plugins/tools/task/scripts/hooks.py:14-66` 在 SessionStart 时：
- 调 `lib.utils.gitignore.add_gitignore_rule` 维护 `.KissFeng/.gitignore`
- 递归扫描 `skills/` `agents/` `commands/` 把 `${CLAUDE_PLUGIN_ROOT}` 字面量真实替换写回文件

### B.3 参考模板优先级

- 新插件如要 **轻 hook**（只注入 hot cache 文本）：抄 `git` 的 manifest + `lib.hooks.load_hooks` 原始路径即可。**前提是接受依赖 `lib`**；不接受则自己写 stdin→json→stdout 三十行。
- 新插件如要 **复杂 hook**（多事件）：`notify` 是参考。
- **不要** 抄 languages 系列：commit `07e713d4` 已删除全部 12 个 language 插件 hooks，理由（commit message 摘录）：
  > 11/12 main.py 字节相同；9/12 hooks.py 为空 noop；同时修掉 python hooks.py 漏逗号导致 safe_edit/safe_remove 列表失效的潜在 bug

教训 → **不要写 noop hook 占位**；**不要在多个插件之间复制 boilerplate hook**；hook 必须有真实业务价值。

### B.4 .claude/settings.json 加载顺序

仓库根 `.claude/settings.json` 已注册：
- `SessionStart`（matcher: startup/clear/compact）→ `python3 .claude/hooks/session-start.py`
- `PreToolUse`（matcher: Task）→ `inject-subagent-context.py`

插件级 hook 与项目级 hook 并存，**不冲突**：CC harness 会聚合所有来源。新插件的 hook 写到 `plugin.json` 即可，无需改项目 settings。

---

## C. claude-obsidian skill 套件分析

源：`/Users/luoxin/.claude/plugins/marketplaces/claude-obsidian-marketplace/`，作者 AgriciDaniel，version 1.6.0，MIT。

### C.1 plugin.json（极简）

`.claude-plugin/plugin.json:1-28` — **没有 hooks 字段**、**没有 commands**、**没有 agents**、**没有 mcpServers**。仅 meta + keywords。Hook 单独放 `hooks/hooks.json`（非标准 manifest 字段，由 README 引导用户手动 link 到 `~/.claude/settings.json`）。

### C.2 11 个 skill 一览

| skill | 触发短语（提取自 frontmatter） | 干什么 |
|-------|------------------------------|--------|
| `wiki` | "set up wiki", "scaffold vault", `/wiki` | 入口；scaffold vault、路由到子 skill；管理 hot cache |
| `save` | "save this", `/save`, "file this conversation" | 当前对话/答案 → 结构化笔记进 vault |
| `wiki-query` | "what is", "explain", "search the wiki" | 三档（quick/standard/deep）查询，hot cache→index→pages |
| `wiki-ingest` | "ingest", "process this source", "add this url" | 单文件/URL/批量摄取，平均 1 source 触 8-15 wiki page |
| `wiki-lint` | "health check", "find orphans", "wiki audit" | orphan / dead wikilink / stale claim / Dataview dashboard |
| `wiki-fold` | "fold the log", "log rollup" | 把 `wiki/log.md` 最近 2^k 条折叠成 fold 页（DragonScale Memory） |
| `autoresearch` | "research [topic]", "deep dive into" | Karpathy 自主研究循环，program.md 配置 |
| `canvas` | `/canvas`, "add to canvas", "canvas zone" | 操作 `.canvas` 文件，加图/PDF/笔记 |
| `defuddle` | "defuddle", "clean this page" | URL → clean markdown（去广告） |
| `obsidian-markdown` | "wikilink", "callout", "obsidian syntax" | OFM 语法参考（写入前必读） |
| `obsidian-bases` | "create a base", "table view" | `.base` 文件（Obsidian 2025 数据库视图） |

### C.3 frontmatter 风格（核心借鉴点）

`skills/save/SKILL.md:1-10`、`skills/canvas/SKILL.md:1-5`、`skills/wiki-query/SKILL.md:1-5`：

```yaml
---
name: <skill-id>
description: >
  <一段话>。Triggers on: "<phrase 1>", "<phrase 2>", ..., "/<slash>".
allowed-tools: Read Write Edit Glob Grep Bash      # 可选，限工具白名单
---
```

**关键点**：description 末尾**显式列出触发短语**（含 slash 形式）。这是 CC skill autoload 的语义路由依据。新插件每个 skill 必须照此写。

### C.4 hooks.json 模式（vault auto-commit 范式）

`hooks/hooks.json:1-50`（不是标准 plugin.json 格式，而是补丁到用户 settings 的 snippet）：

- **SessionStart**: `cat wiki/hot.md`（注入近期上下文）+ prompt 引导 silent 读
- **PostCompact**: 同上 prompt 重新读取（hook 注入不抗 compaction）
- **PostToolUse** (Write|Edit): vault 目录 `git add . && git commit -m "auto-commit"`（自动持久化）
- **Stop**: 检测 wiki/ 改动，提示 LLM 更新 hot.md

### C.5 commands wrapper（极简模式）

`commands/wiki.md:1-6` 只有 4 行：
```
---
description: Bootstrap or check the claude-obsidian wiki vault. Reads the wiki skill and runs setup workflow.
---

Read the `wiki` skill. Then run the setup workflow:
```

**不写实际逻辑**，只是把 slash command 路由到同名 skill。这是命令-技能解耦范式。

### C.6 借鉴分类（保留 / 重设 / 弃用）

| 维度 | 决策 | 原因 |
|------|------|------|
| 三层架构（command 薄壳 → skill 主体 → mcp 原语） | **保留** | 与 ccplugin commands+skills 双层一致 |
| Frontmatter `description` 末尾枚举 trigger phrase | **保留** | autoload 必备 |
| `allowed-tools` 字段限工具集 | **保留**（按需） | 防 skill 滥用工具 |
| hot cache（`wiki/hot.md`）+ SessionStart 注入 | **保留思路** | 但实现走 ccplugin `lib.hooks` 注入 AGENT.md 的范式 |
| PostToolUse auto git-commit vault | **重新设计** | ccplugin 已有"所有变更自动暂存"约定（CLAUDE.md L1），不应复制；用户 vault 是否独立 git 仓须配置化 |
| skill 数量（11 个） | **重新设计** | MVP 砍到 5 个：`wiki`(setup) + `save` + `wiki-query` + `wiki-ingest` + `wiki-lint` |
| `wiki-fold` / `autoresearch` / `canvas` / `obsidian-bases` | **弃用 v1** | 复杂度高、依赖 DragonScale，留 v2 |
| `defuddle` | **弃用** | 仓库 `obsidian:defuddle` skill 已全局可用；不重复 |
| `obsidian-markdown` 语法参考 skill | **弃用** | `obsidian:obsidian-markdown` 已全局可用 |
| 插件全名复用 `claude-obsidian` | **弃用** | 用户明确"全新独立"，命名独立 |

---

## D. obsidian MCP / CLI 能力盘点

### D.1 已配置的 MCP server

`~/.claude.json` 含两条配置：
- `luoxin/obsidian` → vault path `/Users/luoxin/persons/knowledge/obsidian`
- `obsidian` → 命令 `mcp-obsidian`，env `OBSIDIAN_API_KEY=…`（即 [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) 插件桥）

### D.2 mcp__obsidian__* 工具（system prompt 可见）

| 工具 | 能力 |
|------|------|
| `list_files_in_dir` / `list_files_in_vault` | 列文件 |
| `get_file_contents` / `batch_get_file_contents` | 读 |
| `simple_search` / `complex_search` | 搜索（关键字 / Dataview-like） |
| `append_content` | 追加 |
| `patch_content` | 按 heading/block/frontmatter patch |
| `delete_file` | 删 |
| `periodic_note` | daily/weekly note CRUD |
| `recent_changes` | 近期变更 |

### D.3 原语足够性评估

| 操作 | MCP 支持 | Fallback |
|------|---------|----------|
| 笔记 CRUD（增删改读） | ✅ 原生 | — |
| 关键字 / 高级搜索 | ✅ simple/complex | 复杂可加 `qmd` skill |
| Wikilink / callout / properties 写入 | ✅（content 即 markdown） | `obsidian:obsidian-markdown` 语法保证 |
| Periodic note | ✅ | — |
| Frontmatter patch | ✅ patch_content | — |
| **Canvas (.canvas) 编辑** | ❌ 无专门工具 | 退化为 `get/append`，按 JSON Canvas 1.0 schema 手写；或 `obsidian:json-canvas` skill |
| **Bases (.base) 视图** | ❌ | 同上，纯 yaml/markdown 写 |
| **Dataview 渲染** | ❌（只能写 query 不能拿结果） | 不可解，避免依赖渲染输出 |
| **图谱 / Graph view** | ❌ | 不可解 |
| **embed render / preview screenshot** | ❌ | Bash + `obsidian-cli` skill 启动 Obsidian 进程截图 |

**结论**：MCP 已覆盖 v1 必需的 CRUD + search。canvas/bases 写文件可行但读取后渲染不可行；v1 不做渲染依赖即可。

---

## E. 仓库 hook 约束（07e713d4 教训）

`07e713d4` commit message 原文：

> 删除 12 个插件的 scripts/ 目录（main.py/hooks.py/__init__.py 及残留 llms.txt 副本）；移除各 plugin.json 的 hooks 字段（含 golang 的 SessionStart + PreToolUse）；补全 plugins/languages/llms.txt 索引至 12 条
>
> Why: 用户决议不再使用插件级 hooks，避免冗余 boilerplate（11/12 main.py 字节相同；9/12 hooks.py 为空 noop）；同时修掉 python hooks.py 漏逗号导致 safe_edit/safe_remove 列表失效的潜在 bug

**硬约束**：
1. 新插件 hook 必须 **有实际业务**，不写 noop
2. 不在多插件复制 boilerplate；如需共用，落 `lib/hooks/` 而非 plugin 内
3. plugin.json 的 hooks 字段精简：能不写就不写
4. python list 字面量逗号 bug 教训 → 若新插件**避免 python**就规避此风险

---

## F. 定时任务 (cron) 实现路径

### F.1 主线工具

ToolSearch 中**未发现** `CronCreate/CronList` 之类原生工具（system prompt 列出的 skills 中无 `cron-*`）。意味着 CC harness 不直接执行定时任务。

### F.2 现有插件如何做（kioku 参考）

`/Users/luoxin/.claude/plugins/marketplaces/megaphone-tokyo/scripts/install-schedule.sh:5-27`：

```
macOS では install-launchagents.sh を、Linux/WSL/BSD では install-cron.sh を呼ぶ。
```

`install-cron.sh:3-11`：**仅打印 crontab 行**，不写入用户 crontab（非破坏）。要求用户手动 `crontab -e` 粘贴。

### F.3 三种可选路径

| 方案 | 优点 | 缺点 |
|------|------|------|
| **macOS launchd / linux cron**（kioku 同款） | 真正持久；不依赖 CC 在线 | 跨平台脚本复杂；需用户手动安装 |
| **GitHub Actions** | 零本地依赖 | 必须 vault 在 GitHub repo；隐私顾虑 |
| **CC SessionStart 触发 + 时间戳判定** | 无需外部 cron | 必须有人开 CC 才执行；不真定时 |

**MVP 推荐**：方案 3（SessionStart 检查 `last_lint.timestamp`，超 24h 触发 lint 提示），低复杂度无外部依赖。v2 提供方案 1 的脚本。

---

## G. 新插件骨架建议

### G.1 命名

候选：`obsidian-kb` / `obsidian-vault` / `vault` / `kb`。基于现有 `notify` `git` `task` 都是 1 词、`deepresearch` 1 词长式，建议 **`obsidian-kb`**（与 marketplace `claude-obsidian` / `kioku` 区分清晰）。

### G.2 目录树（v1 MVP）

```
plugins/tools/obsidian-kb/
├── .claude-plugin/
│   └── plugin.json                  # manifest，无 hooks（v1 不写 hook 避免 noop 教训）
├── commands/
│   ├── kb-setup.md                  # /obsidian-kb:setup → 路由到 setup skill
│   ├── kb-save.md                   # /obsidian-kb:save → save skill
│   ├── kb-query.md                  # /obsidian-kb:query
│   ├── kb-ingest.md                 # /obsidian-kb:ingest
│   └── kb-lint.md                   # /obsidian-kb:lint
├── skills/
│   ├── setup/SKILL.md               # vault 引导 + .obsidian-kb 配置写入
│   ├── save/SKILL.md                # 对话→笔记
│   ├── query/SKILL.md               # 三档 query（hot→index→deep）
│   ├── ingest/SKILL.md              # 文件/URL→wiki page
│   └── lint/SKILL.md                # orphan / dead link / stale check
├── agents/
│   └── librarian.md                 # 可选：长任务用的 vault 整理 agent
├── docs/
│   ├── architecture.md              # 设计说明
│   └── vault-conventions.md         # 目录约定（concepts/sources/journals 等）
├── README.md                        # 用户文档
└── llms.txt                         # AI 索引（仿 plugins/tools/git/llms.txt）
```

**不放**：`scripts/`、`pyproject.toml`、`.python-version`、`uv.lock` — 满足"不依赖 python 生态"。

### G.3 文件职责（每文件一行）

| 文件 | 职责 |
|------|------|
| `.claude-plugin/plugin.json` | manifest：name=obsidian-kb、commands/agents/skills 显式列出、无 hooks |
| `commands/kb-*.md` | 4 行薄壳：frontmatter description + "Read the `<skill>` skill, then run." |
| `skills/setup/SKILL.md` | 检测 vault path（env / config / prompt）、scaffold `wiki/`、写 `wiki/hot.md` 模板 |
| `skills/save/SKILL.md` | 抽取对话要点→选 note type→写 frontmatter→`mcp__obsidian__append_content` 落盘→更新 index/log/hot |
| `skills/query/SKILL.md` | quick: 仅 hot.md；standard: + index + simple_search；deep: + complex_search + 多页合成 |
| `skills/ingest/SKILL.md` | 文件→entities→1 source 触 N page→交叉引用；URL 走 `obsidian:defuddle`（外部 skill）→ ingest |
| `skills/lint/SKILL.md` | 扫 orphan / dead `[[]]` / 缺 frontmatter；输出 markdown 报告，不自动改 |
| `agents/librarian.md` | 长任务子 agent，处理批量 ingest/lint/重组；`permissionMode: bypassPermissions` |
| `docs/architecture.md` | 三层（command→skill→MCP）+ vault 目录约定 |
| `docs/vault-conventions.md` | wiki/concepts/, wiki/sources/, wiki/journals/, wiki/log.md, wiki/hot.md |
| `README.md` | 安装、配置（VAULT_PATH env）、各 command 用法、与 claude-obsidian/kioku 差异说明 |
| `llms.txt` | 命令+skill 列表（AI 快查） |

### G.4 plugin.json 模板

```json
{
  "name": "obsidian-kb",
  "version": "0.0.195",
  "description": "Obsidian 知识库 CC 插件 - vault 设置、对话保存、查询、摄取、健康检查（基于 mcp-obsidian）",
  "author": { "name": "KissFeng", "email": "kissfeng66@gmail.com" },
  "license": "AGPL-3.0-or-later",
  "keywords": ["obsidian", "knowledge-base", "wiki", "vault", "mcp"],
  "commands": [
    "./commands/kb-setup.md",
    "./commands/kb-save.md",
    "./commands/kb-query.md",
    "./commands/kb-ingest.md",
    "./commands/kb-lint.md"
  ],
  "agents": ["./agents/librarian.md"],
  "skills": "./skills/"
}
```

### G.5 与已有约定的对齐

- 版本号 `0.0.195` 与仓库根同步，由 `scripts/update_version.py` 维护
- 加入 `.claude-plugin/marketplace.json` 的 `plugins[]` 数组（仿 git/notify 块）
- `lib/` 不引用；如未来需 hook，再独立写 stdin→stdout 三十行，不抄 lib.hooks
- 每个 SKILL.md 末尾 `description` 写 `Triggers on: ...` 列举短语（autoload 触发）

---

## Caveats / Not Found

- 未读 task 全部 9 个 skill 的 SKILL.md 全文（只采样 exec/plan）；如需 plan 流程参考可后续补
- 未实际测试 `mcp-obsidian` 当前会话工具是否可调（未列入本次研究 query）
- kioku 的 `manifest.json` 在 `mcp/` 而非 `.claude-plugin/`，未深读其完整 hook 形态；若新插件想做"会话日志自动入库"，需要再调研 kioku `session-logger.mjs`（`/Users/luoxin/.claude/plugins/marketplaces/megaphone-tokyo/hooks/session-logger.mjs`）
- 定时任务方向 F 节给出三方案对比，但未深入实现细节
