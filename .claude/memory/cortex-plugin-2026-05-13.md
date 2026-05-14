---
name: cortex-plugin
description: Cortex 插件当前真相 — vault 结构 / agent / skill / wrapper / 写契约 / 记忆层 / 默认行为
type: project
---

# Cortex 插件 — 单一真相清单

**Why**: 跨多轮重构后, cortex 的 vault 模型、agent 集合、preset、fold/historian 等已多次反转。本 memo 是当前真相基线, 历史变迁见 git log。

**How to apply**: 改 cortex 时以本清单为准, 旧 memory / docs 与此冲突时本清单优先。

## Vault 模型

- 单一 schema (无 preset 系统)。`_meta/version.json` 仅含 `lang` / `preserve_transcript` / `auto_commit` / `auto_push`
- 顶层: `_meta/ _templates/ _assets/ 知识库/ 记忆/ 仪表盘/ 归档/ locales/ .obsidian/ .trash/` (lint `vault-structure-violation` 强制)
- 知识库 4 子目录: `项目/<host>/<org>/<repo>/`, `领域/{创作,学习,工作,技术,生活,金融,未分类}/`, `日记/日/<YYYY-MM>/<YYYY-MM-DD>.md`, `收件箱/`
- 记忆 L0-L4: `L0-核心/ L1-长期/ L2-中期/ L3-短期/ L4-流水账/{ledger,sessions}/ working/ views/{consolidated,candidates.md}`
- 项目路径策略: github/gitlab 走 `host/org/repo` 三段; 本地仓库走相对 `$HOME` 路径, 不足 3 段补 `_local`
- AI 自决域: `--domain` 可选, 缺时 AI 读 body 自决 6 域, 不匹配默 `领域/未分类/`

## 资产计数

| 类型 | 计数 | 备注 |
|---|---|---|
| Agents | 7 | curator / researcher / archivist / cartographer / linker / summarizer / translator (historian 已删) |
| Skills | 21 | 自动触发 + 显式调 |
| Slash commands | 20 | `/cortex:<name>` 冒号 (dash 无法解析) |
| Wrappers | 22 | 10 slash + 3 shell + 9 CLI, 装在 `~/.cortex/scripts/*.sh` |
| Python CLI | 9 | save / search / deep_search / ingest_url / ingest_file / memory / ledger / session / html_render |
| Lint 规则 | 18 | run.py autofix 自循环至 clean; rule 18 = `path-lang-mismatch` (按 vault.lang 校验 path segment, 豁免 host/org/repo + ASCII 专名 + frontmatter `path_lang_exempt`) |
| Hooks | 5 | SessionStart / PostCompact / Stop / SubagentStop / UserPromptSubmit |
| Cron jobs | 8 | lint / dashboard / digest / memory-{promote,forget,compact,warden,archive} |

## Vault 写硬契约 (session_start hook 注入)

1. **L1 强制 = `mcp__obsidian__*`** (save / ingest / patch / refactor / lint --fix 等所有 vault 写)
2. **L2 fallback = 官方 `obsidian` CLI** (MCP 工具失败本次回退)
3. **L3 兜底 = 直接文件 IO** (canvas / 非 md / L1+L2 失败时)
4. **MCP 未注册** → AI 必须先 `AskUserQuestion` 单次授权 (options: `安装 MCP` / `本次使用磁盘 IO (有风险)`), 授权仅本会话有效不写盘, 下次启动重新询问
5. **未授权前**: AI 硬拒绝所有 vault 写并提示用户先选择
6. **例外**: Stop hook / cron / python CLI (非 AI 上下文) 走文件 IO, 不受契约约束

## Hook 行为

- **session_start**: header 后立即注入 🔐 Vault 写契约 (探活 mcp-obsidian via `claude mcp list` → `~/.claude.json:.mcpServers`), 然后 stats + L0 core + hot.md + behavior contract + triggers + collab
- **user_prompt_submit**: 检 git remote → 推 project_hint (`host/org/repo`) + KB 相对路径 (`知识库/项目/<hint>/`). 触发词命中时强制 "禁止直接询问用户, 第一个工具调用必须先搜": 三步 a) `--scope domains` 限项目 + path grep repo 名 b) 跨项目 c) `--scope all` 泛搜。仅全无命中才允许向用户提问
- **stop / postcompact**: 纯 jsonl copy 到 `记忆/L4-流水账/sessions/<cli>/<YYYY>/<MM>/<DD>/<id>.jsonl`

## 搜索 / 召回优先级

- 知识库 `search.py`: hot.md grep → index.md grep → Smart Connections REST (1s 探活) → ripgrep (兜底)
- 深度 `deep_search.py`: `hybrid` (默认, SC+rg+BM25) / `iterative` (≤3 轮挖 gap token) / `subgraph` (≤3 hop, wikilink_index O(V) 一次构建)
- 记忆 `memory.py recall`: L0→L1→L2→L3→L4 加权, 策略走 `_meta/memory-policy.yaml`
- scope: `all=知识库/`, `concepts=知识库/领域/`, `domains=知识库/项目/`, `log=知识库/日记/`

## Ingest 项目级硬契约 (SKILL §1.1 / §7 / §8 / §9)

- **4 层目录** (`知识库/项目/<host>/<org>/<repo>/`): `主题/` (架构/决策/陷阱/依赖/配置/错误码/测试/功能 ≥4) + `模块/` (top-dir 拆) + `文件/` (源文件→.md) + `符号/api/` (函数/类级)
- **分级 .md 下限**: ≤50 文件 ≥15 .md / 50-500 ≥40 / >500 ≥100; 大 repo 用 `符号/api/<module>/<name>.md` 二级目录防爆炸
- **6 类抽取**: API surface + 配置 schema + 错误码 + 测试用例 + 功能模块 + 全局常量
- **强制排除**: build 产物 / lock / binary / 系统 IDE / 临时备份 / 压缩包
- **知识图谱 4 制品** (内联生): `_db.base` (Bases 3 视图 Obsidian 1.7+) + `_assets/canvases/<repo>.canvas` (≤20 节点) + Wikilink 网 (每 .md 出链 ≥5, 小 repo prorated ≥3) + websearch 扩展 (5 URL 容忍跳过)
- **拒交**: 4 层任一空 / 6 类任一缺 / ALL_MD < 下限 / M/R < 0.8 (R 应用排除清单) → AI 必须继续补

## Digest 路由识别 (SKILL §2-§3-§5)

- **6 信号识别** repo 归属: frontmatter `host/org/repo` (强) > `source_url` (强) > wikilink (中) > URL (中) > tag `host/org/repo/<v>` (中) > keyword ≥3 次 (弱)
- **路由表**: 反思/连接/矛盾/决策 4 类 — 命中 repo 落 `知识库/项目/<host>/<org>/<repo>/笔记/` 或 `主题/决策.md` append; 未命中 fallback `知识库/收件箱/`
- 多 repo: 强信号优先 + 其他 repo 加 backlink
- repo 目录缺: `mkdir -p` + minimal `_index.md` stub
- §5 清理: 收件箱 ≥30 天复扫识别, 命中迁项目/笔记/, 否则归档 `归档/收件箱-<YYYY-QN>.md`

## 关键约定

- AUTO_MODE persistent (禁询问 ≠ 中止, AI 自决循环修复至 clean)
- Frontmatter `tags` ≥10 强制, lint `fm-missing-tags` autofix 派生 (12 维度, 严禁占位符)
- Banned fm fields: `preset` (已废, lint autofix pop)
- 路径 lang 校验 (lint rule 18): vault.lang=zh-CN segment 全 ASCII 或 lang=en segment 含 CJK → warn; 豁免 host/org/repo + ASCII 专名 + frontmatter `path_lang_exempt: true`
- cortex-refactor 3 子操作: `rename` / `merge` / `split` (fold / restructure 已删)
- 插件路径硬编码 `$HOME/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex` (env var 解析 bug 规避)
- 自研 MCP 已移除, 走官方 `mcp-obsidian` (用户 `claude mcp add` 自行注册)
- Slash wrapper: `-h`/`--help` + `-i`/`--interactive` (无 -p 进 REPL, 注入 `/cortex:<name>` 首消息) + `--no-commit`; 调 claude 时 echo bash + `--dangerously-skip-permissions`
- 测试: `cd plugins/tools/cortex/tests/python && python3 -m pytest -q` (324 pass + 9 subtests)

## 关联 docs

- `plugins/tools/cortex/AGENT.md` §协作约定 — L1/L2/L3 写契约权威
- `plugins/tools/cortex/docs/{知识库结构,Agents,Commands,Skills 详解,Hooks 机制}.md`
- `plugins/tools/cortex/scripts/lint/schemas.py` — vault 单一 schema 定义
