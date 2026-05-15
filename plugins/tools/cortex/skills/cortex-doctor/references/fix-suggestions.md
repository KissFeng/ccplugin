# cortex-doctor — 问题修复建议

> SKILL.md 入口的实现提示 + 容错策略 + 修复建议。

## 实现提示 (给 Claude)

1. 用 `Bash` 跑 `~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/hooks/_lib/resolve_vault.sh` 拿 vault 路径
2. 用 `Read` / `Glob` 检查共享根目录与模板
3. obsidian CLI / app-running / MCP / REST 检查用一组 `Bash` 命令:
   - CLI 在但 app 未跑 → ❌ CLI 全部失败, 提示启动 app
   - CLI 缺失但 MCP 在 → 给降级建议: "官方 obsidian CLI 不可用, cortex 将走 MCP REST 路径; 需要 Local REST API 插件 + Obsidian 进程常驻; 单调用延迟 ~10ms→~50ms 量级"
   - 两者都缺 → ❌ 致命
4. 全部容错: 任一项失败仅标 ❌, 不中断后续检查

## 修复建议矩阵

| 体检项 | 失败现象 | 修复命令 / 操作 |
|---|---|---|
| vault 路径 | 未命中 | 设 `OBSIDIAN_VAULT` env / 或跑 `bash ~/.cortex/scripts/config.sh init` 写 `~/.cortex/config.json:.vault` |
| vault 结构 | 缺顶层目录 | 跑 `bash ~/.cortex/scripts/init.sh` 重建骨架 |
| obsidian CLI | 不存在 | Obsidian Settings → General → Command line interface 启用 |
| Obsidian app | 未跑 | 启动 Obsidian app (macOS `open -a Obsidian`) |
| alwaysUpdateLinks | false | Obsidian Settings → Files & Links → Automatically update internal links → 开 |
| MCP server | 不可用 | 用户安装 obsidian MCP server (mcp-obsidian) |
| Local REST API | 27123 不通 | 装 Local REST API community plugin + 启用 |
| Smart Connections | 缺 | 装 Smart Connections community plugin + Settings 开启 |
| Smart Connections REST API | 27124 不通 | SC 插件 Settings → REST API → 启用 + 重启 Obsidian |
| ripgrep | 缺 | `brew install ripgrep` / `apt install ripgrep` |
| lint 基线 | 缺 | 跑 `bash ~/.cortex/scripts/lint.sh` 自动创建 |
| 模板缺失 | 缺 .md | 跑 `bash ~/.cortex/scripts/init.sh` 复制默认模板 |
| backlink 不一致 | mismatch | 跑 `bash ~/.cortex/scripts/lint.sh` autofix |
| config 缺 | absent | `python3 ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/scripts/cortex_config.py init` |
| config 非法 | exit 1 | 按字段错误清单逐项改 `~/.cortex/config.json` |
| wrapper 缺 | 不存在 | 跑 `bash ~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex/install.sh` 重装 wrapper |

## 不做

- 不写 vault (诊断专用)
- 不自动修复, 仅给出建议命令 (用户决定是否执行)
- 不被 LLM 自动触发 (`disable-model-invocation: true`), 必须用户显式说"诊断 cortex / cortex doctor"
