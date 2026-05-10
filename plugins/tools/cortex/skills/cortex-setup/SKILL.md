---
name: cortex-setup
description: 初始化或升级 Obsidian vault 至 cortex 标准布局 — 写共享根 (_meta / _templates / index.md / hot.md / log/ / folds/) + 选定 preset (lyt/zettel/para/blank) 的业务目录与种子文件。Triggers on "set up cortex", "init vault", "/cortex:install", "create knowledge base in obsidian", "scaffold vault", "重建知识库目录", "初始化 obsidian vault".
allowed-tools: Bash Read Write Edit Glob mcp__obsidian__obsidian_list_files_in_vault mcp__obsidian__obsidian_list_files_in_dir mcp__obsidian__obsidian_get_file_contents mcp__obsidian__obsidian_append_content
---

# cortex-setup

把一个 (新或既有) Obsidian vault 升级到 cortex 标准布局。

## 触发场景

- 用户初次安装 cortex,需要把空 vault 起骨架
- 已有 vault 接入 cortex,需补 `_meta/` 与 `_templates/`
- 切换 preset (lyt ↔ para ↔ blank)

## 流程

1. **解析 vault** — 跑 `${CLAUDE_PLUGIN_ROOT}/hooks/_lib/resolve_vault.sh` 拿绝对路径;失败则提示用户配置 `OBSIDIAN_VAULT` env 或 `~/.config/cortex/config.json`
2. **选 preset** — 默认 lyt;用户可指定 `lyt|zettel|para|blank`
3. **写共享根** (所有 preset 必备):
   - `_meta/version.json` — `{"schema": "1.0", "preset": "<preset>", "created": "<UTC ISO>"}`
   - `_meta/lint-baseline.json` — `{"exempt": []}`
   - `_meta/migrations/` — 空目录
   - `_templates/{concept,entity,domain,dashboard,question,source,_index}.md` — 复制自 `${CLAUDE_PLUGIN_ROOT}/templates/`
   - `index.md` — 用 `_templates/_index.md` 渲染
   - `hot.md` — 空骨架 (frontmatter `type: meta`)
   - `log/_index.md` — 空骨架
   - `folds/_index.md` — 空骨架
4. **写 preset 业务目录** — 复制 `${CLAUDE_PLUGIN_ROOT}/presets/<preset>/seed/` 全部内容到 vault
5. **回报** — 列已创建/已存在的文件,提示运行 `/cortex:doctor` 验证

## 写入策略

- **不覆盖已有文件** — 用 `Glob` 检查目标路径,存在则跳过并在报告中标 `(skipped)`
- 优先用 `mcp__obsidian__obsidian_append_content` (vault 索引一致);MCP 不可用回退 `Write`
- 任何失败不中断后续步骤,统一收尾报错

## 输出格式

```
✅ 写入 _meta/version.json
✅ 写入 _meta/lint-baseline.json
⏭️  _templates/concept.md (已存在)
✅ 写入 hot.md
...

总结: 22 项写入, 3 项跳过, 0 项失败
下一步: /cortex:doctor 验证
```
