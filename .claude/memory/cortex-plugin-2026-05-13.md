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
| Lint 规则 | 17 | run.py autofix 自循环至 clean |
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

## 关键约定

- AUTO_MODE persistent (禁询问 ≠ 中止, AI 自决循环修复至 clean)
- Frontmatter `tags` ≥10 强制, lint `fm-missing-tags` autofix 派生 (12 维度, 严禁占位符)
- Banned fm fields: `preset` (已废, lint autofix pop)
- cortex-refactor 3 子操作: `rename` / `merge` / `split` (fold / restructure 已删)
- 插件路径硬编码 `$HOME/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex` (env var 解析 bug 规避)
- 自研 MCP 已移除, 走官方 `mcp-obsidian` (用户 `claude mcp add` 自行注册)
- 测试: `cd plugins/tools/cortex/tests/python && python3 -m pytest -q` (314 pass + 9 subtests)

## 关联 docs

- `plugins/tools/cortex/AGENT.md` §协作约定 — L1/L2/L3 写契约权威
- `plugins/tools/cortex/docs/{知识库结构,Agents,Commands,Skills 详解,Hooks 机制}.md`
- `plugins/tools/cortex/scripts/lint/schemas.py` — vault 单一 schema 定义
