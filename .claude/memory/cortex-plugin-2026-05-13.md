---
name: cortex-plugin-2026-05-13
description: Cortex 插件 2026-05-13 整体重构 — 路径迁移 / AUTO_MODE persistent / slash 冒号 / 全 scripts 集中 / 文档对齐
type: project
---

# Cortex 插件 2026-05-13 整体重构

**Why**: 用户多轮指出冲突 (路径混用、版本号残留、shell 触发仍出确认问句、文档计数失真、MOC 已废仍引用、env var 配置二义)。一次性收尾,把所有不一致拉齐到单一真相。

**How to apply**: 之后任何 cortex 相关改动以本次状态为基线,不要回退到旧约定。

## 单一真相清单

| 项 | 真相 |
|----|------|
| Vault 顶层目录 | `知识库/{项目,来源/{代码仓库,网页,论文,书籍},领域/{...},日记/{日,周,月,年},反思,收件箱,实体,概念}` + `记忆/{L0-核心,L1-长期,L2-中期,L3-短期,L4-流水账,working,views}` + `_meta` `_templates` `_assets` `仪表盘` `归档`; **root 上 知识库 子层名 (项目/来源/领域/日记/反思/收件箱/概念/实体/...) lint 强制 mv 入 知识库/<name>/** |
| 配置 | `~/.cortex/config.json` (keys: vault / lang / settings / install_path / timeout_default) |
| Env var 政策 | 禁配置类 (`OBSIDIAN_VAULT`/`CORTEX_VAULT`/`CORTEX_LANG`/`CORTEX_INSTALL_PATH`/`CORTEX_SETTINGS`); 仅 install.sh bootstrap 期允许; 平台契约保留 (`CLAUDE_PLUGIN_ROOT`, `CORTEX_JOB_LABEL`, `CORTEX_STREAM_TEE_FILE`); 官方 mcp-obsidian 用户自行 `claude mcp add` 传 `OBSIDIAN_API_KEY`/`OBSIDIAN_HOST`/`OBSIDIAN_PORT` |
| Slash 形式 | `/cortex:<name>` (冒号),dash `/cortex-<name>` claude 无法解析 |
| AUTO_MODE 行为 | persistent — 禁询问 ≠ 中止; AI 自决循环执行直至 lint clean 或工具客观失败 |
| 插件路径硬编码 | `$HOME/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex` (env var 会有解析 bug) |
| MOC | **已删** — canvas + dashboard 二件套替代 |
| 版本号概念 | **禁** — 删 v2 / v1 / legacy / migration 标记 |

## 实际计数 (与文档对齐)

| 项 | 数 |
|----|----|
| Agent | 8 (`agents/*.md`) |
| Skill | 21 (`skills/<name>/SKILL.md`) |
| Slash command | 20 (`commands/<name>.md`) |
| Bash wrapper | 22 (`~/.cortex/scripts/<name>.sh` = 10 slash + 3 shell + 9 CLI) |
| Lint 规则 | 26 (20 旧 + 1 repo-path-deprecated + 5 kb-*-deprecated) |
| Hook | 5 (SessionStart / PostCompact / Stop / SubagentStop / UserPromptSubmit) |
| 自研 MCP | **已移除** (2026-05-13 晚批): scripts/mcp/ → scripts/cli/, plugin.json 删 mcpServers |
| 官方 MCP (可选) | `mcp-obsidian` (用户走 install.sh 引导自行注册, 不 bundle) |
| CLI 模块 (`scripts/cli/*.py`) | 10 (save/search/deep_search/ingest_url/ingest_file/memory/ledger/session/html_render/cortex_stream) |

## 目录布局 (python/bash 集中到 scripts/)

```
plugins/tools/cortex/
├── install.sh                ← 唯一根级 bash (例外)
├── scripts/                  ← 所有 python/bash 集中
│   ├── cortex_config.py
│   ├── install_cron.sh
│   ├── install_wrappers.sh
│   ├── regen_template_manifest.py
│   ├── cli/                  ← python CLI + lib (替 scripts/mcp/, 2026-05-13 晚批)
│   │   ├── {save,search,deep_search,ingest_url,ingest_file}.py
│   │   ├── {memory,ledger,session,html_render,cortex_stream}.py
│   │   └── lib/  (frontmatter/lock/vault_path/wikilinks/extractors/cortex_common)
│   ├── cron/  hooks/  lint/  refactor/  lib/
├── tests/
├── agents/ commands/ skills/ docs/ presets/ templates/ locales/ styles/
└── .claude-plugin/plugin.json
```

## ingest 全局规则 (folder-first + 深度 + 评分)

- 仓库/项目用**目录**承载: `index.md` 主条目 + ≥4 子文档 (architecture/decisions/pitfalls/dependencies)
- 嵌套 git repo: `find . -name .git ≥2` 时父+子各自独立 ingest
- 深度 L1-L6: 结构/文档/配置/入口码/历史/派生
- 强制 frontmatter: type / title / desc / created / updated / tags(**≥10**) / source_url / version / when_to_read / score(1-5) / maturity
- tags 强制: **≥10 个**, 严禁占位符 (`<...>` / placeholder / TODO / 待填 / TBD); 派生维度: `type/` `topic/` `stack/` `lang/` `source/` `host/` `org/` `repo/` `score/` `maturity/` `created/` `keyword/`

## 测试基线

- python 243 PASS
- bash 8 files / 11 assertions PASS
- mcp 113 PASS
- **总 364 + 8 全绿**

## 文档分层

- `docs/` — 用户使用 (起步 / 调用方式 / 进阶 / 出问题)
- `docs/_internal/` — 开发者参考 (architecture / design-decisions / hook-protocol / contributing)

## 关键 commit

| Hash | 主题 |
|------|------|
| `e5b6e85e` | Stop/PostCompact 简化为纯 jsonl copy → 记忆/L4-流水账/sessions/<cli>/<YYYY>/<MM>/<DD>/<id>.jsonl |
| `ab675e58` | install_cron 删尾部 disclaimer |
| `dce1c41f` | install_cron read+compare+conditional-write, 表格始终输出 |
| `c3fdd4ca` | cortex_stream 工具调用渲染优化 |
| `2f7ee914` | digest 收件箱 ≥30天强制 classify/archive/delete |
| `7d90da23` | save_session 路径迁移 + digest 加 inbox |
| `a1fce7ef` | install_cron 自动 idempotent (读+去重+写入) |
| `bc13dee2` | consolidate → digest, fold 完全移除 |
| `b88a2510` | consolidate 升级日处理五阶段 |
| `a7f87600` | install --non-interactive 默认装 cron + 表格输出 |
| `4ba4f2b5` | cron dashboard 改 daily (was weekly) |
| `f1fe02a8` | 范围标记改文字 (去 emoji) |
| `66dc8d2c` | 文档清单加范围列 (全局/当前目录/知识库/记忆) |
| `192d050b` | templates/ 移到 presets/seed/_templates/ |
| `32ac08ea` | neat-freak 记忆 + README 计数对齐 |
| `4e5a48ea` | python/bash 全移 scripts/ (install.sh 例外) |
| `59e9d127` | 删 MOC 引用 + install_cron 路径硬编码 |
| `454af37f` | 文档计数对齐 + 内部下沉 |
| `c2a66f53` | 7 类全局不一致 (路径/slash/env/AUTO_MODE/lint/版本号) |
| `3bac2d4b` | AUTO_MODE 改 persistent 自决循环 |
| `e1ab3f6b` | slash dash → colon |
| `73b58bd8` | ingest 全局知识库构建规则 |
| `1e74eb60` | ingest 默认深度分析 PWD |
| `169ba3a1` | cortex_stream stdout 严禁 raw NDJSON |
| `41ced4c3` | cortex_stream 顺序渲染 (去 Live 区) |
| `19952bae` | lint: log/folds/sessions 移出 root_dirs + fm-duplicate-tags 规则 + 自动清 lint_whitelist 旧条目 |
| `f515cb8c` | digest: L4 全量处理, 不限文件类型, 不限时间窗 |
| `135f497f` | digest: L4 全清空 — 删 7d 时间窗例外, 单向漏斗 0 残留 |
| `4cc5d8aa` | digest: 既有 L0-L3 + 知识库 参与交叉学习, 数据更新不删条目 (update_target/enrich_target/conflict) |
| `7a4573da` | digest: 五阶段 spec 单一真相搬到 SKILL.md, command/cron 仅委托 |
| `332f7a10` | lint: fm-banned-tags 规则 + parse_frontmatter 多行 YAML list bug 修 (核心 bug — `- item` 无缩进时被丢弃) |
| `2492ce47` | lint: fm-banned-fields (禁 preset 字段) + fm-missing-tags (强制 tags 存在) |
| `49e3c217` | lint: vault root 上 知识库 子层 namespace 强制收纳 (实体/概念/领域/来源 等 mv 到 知识库/) + locale_dirs 顶层化 |
| `d7210ffa` | dashboard: seed 12 页清 `{{X}}` runtime 占位符 (KB_TOTAL/CHART_*/L*_TOTAL 等 ~100 个), DASH:BEGIN/END 单一数据源; cortex_stream Edit 分支 `=` → `==` 语法 |

## 定时任务最终调度

| Job | 频率 | 时间 |
|-----|------|------|
| `lint.sh` | daily | 01:00 |
| `dashboard.sh` | daily | 02:30 |
| `digest.sh` | daily | 03:00 |

系统注册方式: install_cron.sh 仅**打印 snippet**, 用户手工 `crontab -e` / `launchctl load` / GHA workflow 三选一启用。当前系统未注册任何 cortex 定时任务。

## 目录布局变化

- `templates/` → `presets/seed/_templates/` (preset 统一提供, vault init 走单一复制流)
- 根目录最终: install.sh / scripts/ / tests/ / agents/ commands/ skills/ docs/ presets/ locales/ styles/ / _manifest.json AGENT.md README.md / .claude-plugin/

## 文档范围标记 (4 类, 文字描述, 禁 emoji)

- **全局** — 系统/用户级 (~/.cortex/, ~/Library/LaunchAgents, marketplace cache, Claude 会话 hook)
- **当前目录** — PWD (wrapper 调用时 cwd, 如 ingest 深度分析)
- **知识库** — vault (~/.cortex/config.json:.vault)
- **记忆层** — 记忆/L0-L4 子树

## Digest skill 单一真相 (2026-05-13 后期)

- 操作规范从 `commands/digest.md` + `scripts/cron/digest.sh` 内联 PROMPT 搬到 `skills/cortex-digest/SKILL.md`
- command/cron 改为单行委托 ("Invoke Skill cortex-digest")
- **L4 = 单向漏斗**: 每次 digest 必清 0 残留 (promote-L3 / archive-到-归档/L4-<YYYY>/<rel> / delete 三选一), 无时间窗例外
- **既有 L0-L3 + 知识库 参与交叉学习** (数据更新不删条目):
  - update_target (L1/L2/L3 命中) → `cortex_memory_write` append + weight += 0.05 (cap 1.0)
  - enrich_target (知识库命中) → patch 加 `## 新增例证 <date>` + wikilink
  - conflict → 新写 `知识库/反思/矛盾/<date>-<topic>.md`, 不动既有
  - concretize (疑问页 backlinks≥3) → 阶段 5 删
- 日记归档目标: `归档/日记/<YYYY-QN>.md` 季度桶

## Lint 规则总览 (20 条)

新增 (2026-05-13 后期):
- `fm-duplicate-tags`: tags 列表内重复, autofix 保序去重
- `fm-banned-tags`: tags 含结构标记 (index/meta/template/_index/stub), autofix 移除
- `fm-banned-fields`: fm 含禁止字段 (preset 等), autofix pop
- `fm-missing-tags`: **2026-05-13 v3 升级** — 三分支 (字段缺 / 非 list / `<10`); autofix 读 fm + 正文 h1/h2 + 首 500 字派生 ≥10 tag, 严禁占位符 (`<...>` / placeholder / TODO / 待填 / TBD); 派生不足 10 保 warn 不写盘, 由 AI 二次循环
- `lint-skip: true` (frontmatter 短路标志): 任何 md 含此字段, check_file 入口直接返空 findings; 31 个 `_templates/*.md` 全加 (模板演示占位符不应被 lint 拦)

行为升级:
- `vault-structure-violation`: root 上的 知识库 子层名 → autofix **merge 到 知识库/<name>/** (非备份). 子层集: 项目/来源/领域/日记/反思/收件箱/概念/实体/问题/临时 + en alt
- 自动清 `_meta/version.json:lint_whitelist` 中废弃条目 (log/, folds/, sessions/)
- `parse_frontmatter` 修多行 YAML list bug — `- item` 无缩进时被丢弃 (yaml 标准合法但 lightweight parser 忽略); 现 `stripped.startswith("- ")` 即追加

## Dashboard seed 重构

- 12 个仪表盘 seed (`presets/seed/仪表盘/*.md`) 体清空所有 runtime 占位符 (~100 个 `{{KB_TOTAL}}` / `{{CHART_*}}` / `{{L*_TOTAL}}` 等)
- 新结构: frontmatter (`view_query`/`role` 保留) + h1 (fm.title) + `> [!info]` intro (fm.role) + `<!-- DASH:BEGIN -->...<!-- DASH:END -->` 待填区 + `<!-- TEMPLATE_END -->`
- 单一数据源: `cortex-dashboard` skill 注入 DASH:BEGIN/END 块; 体里不再有 inline 占位符

## 自研 MCP 移除 (2026-05-13 晚批 v2)

**动机**: 用户决策 — plugin bundle MCP server 与官方 `mcp-obsidian` 重复;插件应只暴露 bash/CLI 接口,REST 操作走可选官方 MCP。

### Phase 1 (`015a4a30`)

- `.claude-plugin/plugin.json:mcpServers.cortex` 整块删除
- `install.sh` 末尾加 "MCP (可选)" 章节, 引导 `claude mcp add obsidian uvx mcp-obsidian -e OBSIDIAN_API_KEY=... -e OBSIDIAN_HOST=127.0.0.1 -e OBSIDIAN_PORT=27123`

### Phase 2a (`7945f42d`) — 协议层剥离

- `scripts/mcp/` → `scripts/cli/` (git mv)
- `scripts/mcp/tools/*.py` → `scripts/cli/{save,search,deep_search,ingest_url,ingest_file}.py`, 每个加 argparse main()
- 拆 `cortex_mcp.py` 函数到 `scripts/cli/{memory,ledger,session,html_render}.py`, 共享 helper 进 `cli/lib/cortex_common.py`
- 删 `scripts/mcp/server.py` + `scripts/mcp/cortex_mcp.py` + `scripts/mcp/tests/` (113 MCP 协议测试)
- 算法 100% 保留 (masking / frontmatter / BM25 / 子图扩展 不变)

### Phase 2b-f (`214ebefc`) — 接入 + 文本替换

- `scripts/install_wrappers.sh` 加 `emit_cli` helper + 9 CLI wrappers (`save/search/deep_search/ingest_url/ingest_file/memory/ledger/session/html_render`)
- bash wrapper 模板: `exec python3 $PLUGIN_ROOT/scripts/cli/<mod>.py "$@"`
- wrapper 总数 17 → 21 (9 slash + 3 shell + 9 CLI)
- 16 个 agent/skill/command/hook 文件中 `mcp__cortex__*` 调用改为 `bash ~/.cortex/scripts/<name>.sh ...`
- `allowed-tools:` frontmatter 删 `mcp__cortex__*`, 加 `Bash`
- `cortex_stream.py` 从 `scripts/mcp/` 搬到 `scripts/cli/` (非 MCP 协议代码, 只是 stream-json 渲染器)
- 新 `tests/python/test_cli_smoke.py`: 9 CLI 模块 `--help` 烟雾测试
- 删 `tests/python/test_mcp_3_tools.py`
- `scripts/mcp/` 目录彻底删除

### 验收

- `grep "mcp__cortex__"` in `agents/ commands/ skills/ scripts/hooks/` = 0
- python tests 286 pass + 9 subtests, 0 fail
- 用户角度: 装 plugin 不再自动启 cortex MCP server;`mcp-obsidian` 为可选,走 install.sh 文末引导手动注册

## tags ≥10 强制 (`2e5d53d9`, 2026-05-13 v3)

**动机**: 用户要求知识库每一个 md 必须有 ≥10 个语义标签, 严禁占位符。

### Lint 规则升级

- `fm-missing-tags`: 单规则三分支 (字段缺 / 非 list / `<10`)
- autofix 改为派生器: 读 fm (type/lang/host/org/repo/source_url/score/maturity/created 等) + 正文 h1/h2 (→ `topic/<slug>`) + 首 500 字中文 2-4 字 + 英文 PascalCase (→ `keyword/<x>`)
- 去重保序, 截断 ≤20, 严禁 5 类占位符
- 派生不足 10 不写盘, 保 warn

### Lint 短路标志

`lint-skip: true` 入口短路, 跳过所有规则。用于 31 个 `_templates/*.md` (含 memory/html/knowledge 子目录), 让模板演示占位符不被 lint 拦。

### Ingest 落档强制

`scripts/cli/save.py:_save_internal` 写盘前调 `_derive_tags(fm, body)`, 自动扩展到 ≥10。host/org/repo 同步写入 fm 顶层。

### 文档同步

- `skills/cortex-ingest/SKILL.md`: "tags ≥ 3" → "≥10 严禁占位"
- `skills/cortex-lint/SKILL.md`: rules 表加 `lint-skip` 短路说明
- `commands/ingest.md`: "(≥3)" → "(≥10, 严禁占位)"

### 验收

- pytest 286 → 292 pass (6 新 case), 0 fail
- 模板 31 个 `lint-skip: true` 全加
- grep `≥3 tag` 残留 = 0

## 仪表盘输出优化 (`12bebfb2`, 2026-05-13 v4)

12 dashboard seed + skill + cron prompt 全套升级:

- seed `view_query` 改 dict (kind + level + limit + window), 加 `view_chart` (7 类) + `view_kpi` (真实 Bash 计数表达式) + `view_legend` + `view_stale_after`
- 仪表盘从 lint exemption 移除, 全 12 seed tags ≥10
- SKILL 重写: 8 kind 查询 (memory/knowledge/ledger/cron/bridge/distribution/promotion/warden) + 7 chart 模板 (pie/sankey/heatmap/timeline/mindmap/table/grid), mermaid fallback (heatmap→emoji table 🟩🟨🟧🟥, sankey→flowchart LR)
- DASH:BEGIN/END 区结构: KPI callout + chart + Top-N + LEGEND
- 错误处理: 路径缺→报 error 不写盘保留上次; 路径空→渲染 0 (真实数据); 严禁 N/A 占位
- cron/dashboard.sh PROMPT 单行委托

## GitHub/GitLab 项目目录 (`f76d735c`, 2026-05-13 v5)

- github/gitlab/local git repo → `知识库/项目/<host>/<org>/<repo>/`
- 来源仅承载非 repo (网页/论文/书/视频/PDF)
- `scripts/cli/save.py` 新 `kind=project`, `kind=domain` 保留 alias, `kind=source` 严禁 repo host
- `ingest_url/ingest_file` 自动 host 路由
- Lint 新规则 `repo-path-deprecated` autofix mv + frontmatter rewrite
- 新模板 `_templates/project.md`, schema 重写

## 知识库 4 子目录对齐 vault (`68d2ab7a`, 2026-05-13 v6)

**核心**: 用户实际 vault 仅用 4 子目录, 插件 spec 收紧。

### 4 子目录最终模型

```
知识库/
├── 收件箱/           # 落档兜底, 待 digest 分发
├── 日记/日/<YYYY-MM>/<YYYY-MM-DD>.md
├── 项目/<host>/<org>/<repo>/
└── 领域/<域>/
```

**删**: 来源/反思/实体/概念/问题/临时/日记-周/日记-月/日记-年

### kind 路由 11 种 (save.py)

| kind | 路径 |
|------|------|
| project | `知识库/项目/<host>/<org>/<repo>/<slug>.md` |
| domain | alias project |
| source | host ∈ github/gitlab 报错; 否则 `知识库/收件箱/<host>-<slug>.md` |
| entity / concept | `知识库/领域/<domain>/<kebab>.md` (--domain 可选, 缺默 `未分类`, AI 自决) |
| reflection | `知识库/日记/日/<YYYY-MM>/<YYYY-MM-DD>-反思-<slug>.md` |
| question / fleeting / inbox | `知识库/收件箱/<slug>.md` |
| log / journal | `知识库/日记/日/<YYYY-MM>/<YYYY-MM-DD>.md` (仅日, 周/月/年 kind 删) |

### local 项目相对 `$HOME` 路径

- `~/persons/lyxamour/ccplugin/` → host=persons, org=lyxamour, repo=ccplugin
- 不足 3 段用 `_local` 补齐
- source_url: `file://$HOME/<rel>`

### 嵌套 repo

`ingest_file._find_nested_repos`: 递归发现 `.git/`, 每个独立 ingest 到自己的 `项目/<host>/<org>/<repo>/`, 父项目内容排除子 repo。

### 模板重做 (6 个)

**删**: `_templates/{entity,concept,question,source,domain}.md`
**保留**: `_templates/{project,_index,dashboard}.md`
**新**: `_templates/{inbox,journal-day,domain-topic}.md` (lint-skip + tags ≥10)

### Lint 5 新规则

| Rule | Autofix |
|------|---------|
| `kb-reflection-path-deprecated` | mv 收件箱 |
| `kb-question-fleeting-path-deprecated` | mv 收件箱 |
| `kb-entity-concept-path-deprecated` | warn-only (需 AI 选域) |
| `kb-journal-multi-freq-deprecated` | mv `归档/日记/<YYYY-QN>.md` |
| `kb-source-non-repo-path-deprecated` | mv `收件箱/<host>-<slug>.md` |

### AI 自决域选择

`--domain` 可选, 缺时 SKILL/agent 读 body 自决 6 域 (创作/学习/工作/技术/生活/金融), 不匹配默 `领域/未分类/`, 允许创建新子目录。

### 验收

pytest 300 → 320 pass (+15 新 case: save 路由 9 + rel_home 4 + lint deprecation 6)

## install_wrappers.sh 修复 (`e2bc30cc` + `d0b22973`, 2026-05-13/14)

### `e2bc30cc` — 补 ingest + 清旧残留
- `emit_slash ingest` (commands/ingest.md 是合法 `/cortex:ingest`)
- `TARGET_DIR` 内非白名单 .sh 自动 `rm` (避免重命名后旧 wrapper 残留)
- wrapper 总数 21 → 22 (10 slash + 3 shell + 9 CLI)

### `d0b22973` — bash 3.2 兼容
- `declare -A` 需 bash 4+, macOS 默认 bash 3.2 报 `invalid option`
- 改空格分隔字符串 + `case` 边界匹配 (POSIX-ish)
- 头尾空格防误匹配 (save.sh vs save_session.sh)

## install.sh MCP 段精简 (`9a1a4471`, 2026-05-14)

- 删介绍行 "如需通过 Obsidian REST API 操作 vault, 装官方 mcp-obsidian"
- 删尾注 "注: cortex 内部业务 (memory/digest/lint/ingest) 走 bash wrappers"
- step2 label + claude mcp add 命令合并单行
- 最终 3 printf (标题 + step1 + step2 含命令)
