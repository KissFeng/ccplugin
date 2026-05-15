---
name: cortex-save
description: 落档非平凡发现到 vault — 选目录 (项目/领域/日记/收件箱), 套模板, 塞 frontmatter (4 评分字段), 注 block-id, 反向 wikilink 回填, 同步 index/hot。触发: "save this" / "归档" / "落档" / "save 笔记"。
allowed-tools: Bash Read Write Edit Glob mcp__obsidian__obsidian_get_file_contents mcp__obsidian__obsidian_append_content mcp__obsidian__obsidian_patch_content mcp__obsidian__obsidian_simple_search
---

# cortex-save

把"值得留下的东西"写进 Obsidian vault, 让未来会话能搜到。

## 调用优先级 (P1)

1. **优先 CLI**: `bash ~/.cortex/scripts/save.sh --kind <k> --title <t> --body <b> [--tags ...] [--source-url ...]` — 自动跑 masking + frontmatter + block-id + flock + hot/index patch, 结构化返 `{path, block_ids, hits}` (stdout JSON)
2. **回退**: L1 obsidian CLI / L2 mcp__obsidian / L3 Write — CLI 不可达时

## 触发场景

- 用户显式 "save this" / "落档" / "归档" / `/cortex:save`
- Stop / SubagentStop hook 启发式触发后回到主线让 skill 完成精修
- 当前讨论沉淀出 1-2 个明确概念 / 决策 / 实体 / 资源, 主 agent 主动调

## 关键决策树

1. **解析 vault** → `<PLUGIN_ROOT>/scripts/hooks/_lib/resolve_vault.sh`; 失败提示配置后退出
2. **判 type**: 用户给 `--topic` → `concept`; `--from-session` 或无参 → `log`; 项目内事 → `domain`
3. **选目录** — 按 type 路由表 (concept/entity/project/source/reflection/journal/...) + 文件名 lang 对齐 (rule 20 path-lang-mismatch); 详见 [references/path-routing.md](references/path-routing.md)
4. **套模板 + 填 frontmatter** — `<vault>/_templates/<type>.md` 或 plugin presets fallback; 替换 `{{TITLE}}/{{CREATED}}/{{UPDATED}}`; 强制 4 评分字段 (score/confidence/source_credibility/maturity), 详见 [references/scoring-frontmatter.md](references/scoring-frontmatter.md)
5. **block-id 注入** — H2/H3 段末追 `^cortex-<sha8>`; sha8 = sha256(rel-path::UTC-iso::section-index::heading)[:8]
6. **写入** — P0 masking 前置 → L1 mcp__obsidian (优先) → L2 obsidian CLI → L3 Write 兜底; 详见 [references/save-flow.md](references/save-flow.md)
7. **更新索引 + backlink** — index.md type 章节 / hot.md 顶部 / log/_index.md (log 类) + 跑 `backlink_sync.py` 反向回填
8. **输出** — 绝对路径 + 相对路径 + `obsidian://` URI + backlinks 命中数 + 待补 wikilink 数

## AUTO_MODE (wrapper / cron 传 `auto` 后缀)

- **不调** AskUserQuestion (wrapper allowed-tools 已禁)
- body 经 masking 后直接写盘, 不询问
- 默认 `kind=log` (未提供时), 默认 6 域路由走 `领域/未分类/`
- persistent: save 失败 → 重试 / 换 save.sh 参数 / 写 cache 兜底, 禁询问禁中止
- 写盘不需二次确认

## References

| 文件 | 内容 |
|---|---|
| [references/path-routing.md](references/path-routing.md) | type → 目录路由表 + 6 域自决 + 文件名 lang 对齐 + path_lang_exempt |
| [references/save-flow.md](references/save-flow.md) | P0 masking + L1/L2/L3 写入策略 + obsidian-git 协调 + save_session.py 快捷调用 |
| [references/scoring-frontmatter.md](references/scoring-frontmatter.md) | 4 评分字段 (知识库) + 2 评分字段 (记忆) + frontmatter schema + CLI override |

## 不做

- 不 `git commit` / `git push` (与 OGit 冲突)
- 不删 / 改用户已有内容 (仅追加章节)
- 不解析 canvas (.canvas) / bases (.base)

## 错误处理

| 失败 | 行为 |
|---|---|
| vault 未解析 | 立即退出, 给配置示例 |
| 模板缺失 | 退出, 提示重装 cortex |
| MCP 不可用 | 回退 Write |
| save_session.py 退出码 1 | stderr 输出后退出 (AUTO_MODE) / AskUserQuestion (Interactive) |
| 反向 wikilink 失败 | 仅警告, 主文件保留 |
