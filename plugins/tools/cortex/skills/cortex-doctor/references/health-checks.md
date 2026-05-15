# cortex-doctor — 18 项体检详细规则

> SKILL.md 入口的 18 项体检逐项说明。

## 检查清单

1. **vault 路径解析** — 跑 `~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/hooks/_lib/resolve_vault.sh`, 显示命中的来源 (env / config / default / auto-detect / 未命中)
2. **vault 结构** — 共享根 (`_meta/`, `_templates/`, `index.md`, `hot.md`) + 顶层 (`知识库/`, `记忆/`, `仪表盘/`, `归档/`) 是否齐全
3. **官方 obsidian CLI** — `command -v obsidian` 是否存在, `obsidian --version` 输出 (期望 v1.12.x+); 同时 `obsidian vault list` 检查 vault 是否已注册到 `obsidian.json`
   - **cortex 主路径**: read=`obsidian read` / write=`obsidian create overwrite=true` / append=`obsidian create append=true` / list=`obsidian files` / search=`obsidian search:context` / move=`obsidian move` / frontmatter=`obsidian property` / daily=`obsidian daily`
   - 未安装 → 参考官方 docs <https://docs.obsidian.md/Plugins/Obsidian+CLI> (Obsidian Settings → General → Command line interface 启用并安装)
4. **Obsidian app 在跑** — 官方 CLI 经 app runtime, app 不在跑全部失败
   - mac: `pgrep -x Obsidian`
   - linux: `pgrep obsidian`
   - win: `tasklist /FI "IMAGENAME eq Obsidian.exe"`
   - 未跑 → 提示用户启动 Obsidian app
5. **vault 自动更新 wikilink** — 读 `<vault>/.obsidian/app.json` 的 `alwaysUpdateLinks` 字段
   - `true` → ✅ `obsidian move` 会自动更新 wikilink
   - `false` / 缺失 → ⚠ 提示开启 (Settings → Files & Links → Automatically update internal links), 否则 cortex-refactor 的 move 不会自动改链
6. **Obsidian MCP server (L2 兜底)** — 检测 `mcp__obsidian__obsidian_list_files_in_vault` 工具是否可用。用于 heading-anchor patch / block-id patch / canvas / 非 md 文件 / 完整 metadata graph 等官方 CLI 不支持的场景
7. **Local REST API** — `curl -sf http://127.0.0.1:27123/` 检测端口
8. **Smart Connections** — 查 `~/Library/Application Support/obsidian/<vault>/.obsidian/plugins/smart-connections/data.json`
9. **Obsidian Git** — 同上, 提示是否需关闭 cortex auto-commit
10. **lint 基线** — `_meta/lint-baseline.json` 存在性
11. **模板完整性** — `_templates/{concept,entity,domain,dashboard,question,source}.md` 是否齐全
12. **Smart Connections REST API** — `curl -sf -m 2 http://127.0.0.1:27124/embeddings/info` 是否可达 (cortex-search L3 语义检索依赖)
13. **ripgrep** — `command -v rg` (cortex-search L5 兜底依赖)
14. **backlink 完整性** — 抽样 5 个 `log/` 与 `知识库/领域/` 页面, 检查其 `[[X]]` wikilink 是否在 X 的 `## Backlinks` 段中出现; 不一致计入报告
15. **共享 config 存在性** — `~/.cortex/config.json` 是否存在; 缺失 → ℹ️ info (非 fail), 提示运行 `~/.cortex/scripts/config.sh init`
16. **共享 config 合法性** — 跑 `python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/cortex_config.py validate`; exit 0 + "config ok" → ✅; "config absent" → ℹ️; exit 1 → ❌ 列出字段错误
17. **wrapper 完整性** — 检 `~/.cortex/scripts/` 下 wrapper (`lint.sh`, `dashboard.sh`, `doctor.sh`, `install_cron.sh`, `config.sh`, `update.sh`, ...) 是否存在且可执行; 缺失 → ⚠️ warn

## 行为

按顺序跑上面 18 项, 每项输出一行带 emoji 状态:

```
✅ vault 路径: /Users/.../knowledge/obsidian (源: env)
✅ 共享根: 完整
✅ obsidian CLI: v1.12.4 (vault `brain` 已注册)
✅ Obsidian app: 在跑 (pid 12345)
✅ alwaysUpdateLinks: true (move 自动改链)
✅ Obsidian MCP (L2 兜底): 可用
...
```

末尾给一句总结 + 建议下一步。
