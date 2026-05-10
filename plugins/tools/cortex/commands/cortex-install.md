---
description: 在 Obsidian vault 中安装 cortex 标准布局 — 写入共享根 (_meta / _templates / index.md / hot.md / log/ / folds/) 与所选 preset (lyt / zettel / para / blank) 的业务目录与种子文件。默认 preset 为 lyt。不覆盖已有文件。
argument-hint: "[lyt|zettel|para|blank]"
allowed-tools: Bash, Read, Write, Glob, mcp__obsidian__obsidian_list_files_in_vault, mcp__obsidian__obsidian_list_files_in_dir, mcp__obsidian__obsidian_get_file_contents, mcp__obsidian__obsidian_append_content
---

# /cortex:install

在 Obsidian vault 中安装 cortex 标准布局。这是把空 vault 起骨架, 或把既有 vault 升级到 cortex 约定的入口命令。

## 用法

```
/cortex:install            # 默认 preset = lyt
/cortex:install lyt        # Linking Your Thinking (8-bucket + MOC)
/cortex:install zettel     # Zettelkasten (扁平 + UID)
/cortex:install para       # PARA (Projects/Areas/Resources/Archive)
/cortex:install blank      # 最小骨架 (仅共享根, 无业务目录)
```

## 行为

1. 解析 vault 路径: 读 `${CLAUDE_PLUGIN_ROOT}/hooks/_lib/resolve_vault.sh` 输出 (env > config > 默认 > auto-detect)
2. 校验参数 `$1` 必须 ∈ `{lyt, zettel, para, blank}`, 缺省时默认 `lyt`
3. 调用 `cortex-setup` skill 完成安装:
   - 写共享根 (所有 preset 必备): `_meta/version.json`, `_meta/lint-baseline.json`, `_meta/migrations/`, `index.md`, `hot.md`, `log/_index.md`, `folds/_index.md`
   - 复制 `${CLAUDE_PLUGIN_ROOT}/templates/*.md` 到 `<vault>/_templates/`
   - 读 `${CLAUDE_PLUGIN_ROOT}/presets/<preset>/_structure.json`, 按 `directories` 创建空目录, 按 `seed_files` 复制种子文件
4. 报告每个写入文件 (`✅` 新建 / `⏭️` 已存在跳过 / `❌` 失败), 末尾给总结与下一步建议

## 实现步骤 (给 Claude)

请执行 `cortex-setup` skill, 把 preset 参数传入。流程见该 skill 的 SKILL.md。

## 错误恢复

| 情况 | 处理 |
|------|------|
| vault 路径解析失败 | 提示用户设置环境变量 `OBSIDIAN_VAULT` 或写入 `~/.config/cortex/config.json`, 然后重试 |
| 参数不在 `{lyt, zettel, para, blank}` | 报错并列出 4 个有效值, 不动 vault |
| 个别文件写入失败 (权限 / IO) | 标 ❌ 但不中断后续, 末尾汇总错误清单 |
| 已存在的文件 | 默认 **跳过, 不覆盖**。要重置某文件用户需手动删除后重跑 |
| Obsidian MCP server 不可用 | 回退用 `Write` 工具直接写文件; 末尾提示用户配置 `mcp__obsidian__*` 以获得索引一致性 |

## 不做

- 不删除任何已有文件
- 不修改用户已存在的 `_templates/*.md` (用户可自由编辑)
- 不写入 `~/.claude/settings.json` 或其他全局配置
- 不自动 git commit (即便 vault 是 git 仓库)

完成后建议运行 `/cortex:doctor` 验证安装结果。
