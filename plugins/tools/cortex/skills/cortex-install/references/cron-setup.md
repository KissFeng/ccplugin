# cortex-install — 9 cron 注册流程

装机一次性, 内联 launchd/cron/GHA 注册。

## AskUserQuestion 流程 (≤4 合并单次调用)

**Q1 (multiSelect)**: "勾选要注册的 cron job (8 项)":

- `daily 01:00 知识库 lint`
- `daily 02:30 dashboard`
- `daily 02:00 memory-promote` (L4→L3 提炼 + 候选写 candidates.md)
- `daily 03:00 memory-forget` (扫过期标 archive_pending)
- `weekly Sun 04:00 memory-compact` (L4 流水账 gzip)
- `weekly Sun 04:30 digest` (ledger → views 周报)
- `biweekly 1,15 05:00 memory-warden` (腐化检测)
- `monthly 1 06:00 memory-archive` (执行归档)

**Q2 (single)**: "注册平台":

- `不启用` (默认)
- `launchd (macOS)`
- `cron (Linux/macOS)`
- `GitHub Actions (远程仓库)`

Q2 = `不启用` → 跳过, 安装完成。Q2 ∈ {launchd, cron, gha} → 走下述内联注册。

## 解析 PLUGIN_ROOT

cron daemon 不继承 shell env, snippet 必须绝对路径。优先级:

`$CORTEX_INSTALL_PATH` env > `~/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex` > `$CLAUDE_PLUGIN_ROOT`

**避免**本地开发源码路径 (cron 上下文不可达)。

## 每 job 的 wrapper

`<PLUGIN_ROOT>/scripts/cron/{lint,dashboard,memory-promote,memory-forget,memory-compact,digest,memory-warden,memory-archive}.sh`

内部走 `claude --bare --no-session-persistence --settings ~/.claude/settings.glm-4.7-flash.json -p "..." --allowed-tools "Bash Read Glob Write Edit"` (memory-* 需写, 不允许删除)。

## Cron 调度表

| job | cron 表达式 |
|-----|-------------|
| lint | `0 1 * * *` |
| dashboard | `30 2 * * *` |
| memory-promote | `0 2 * * *` |
| memory-forget | `0 3 * * *` |
| memory-compact | `0 4 * * 0` |
| digest | `30 4 * * 0` |
| memory-warden | `0 5 1,15 * *` |
| memory-archive | `0 6 1 * *` |

## 后端 1: launchd (macOS)

为每选中 job 写 plist:

- 路径: `~/Library/LaunchAgents/dev.KissFeng.cortex.<job>.plist`
- 内容: `<ProgramArguments>` = `["bash", "<PLUGIN_ROOT>/scripts/cron/<job>.sh"]`, `<StartCalendarInterval>` 按上表
- 落盘前**必须**再调 `AskUserQuestion` 打印完整 plist, 选项 `写入` / `取消` / `改时间`
- 用户选 `写入` → `Write` plist + `Bash launchctl load <plist>`

## 后端 2: cron (Linux/macOS)

append `~/.cortexrc.cron`:

- 行格式: `0 2 * * *  bash <PLUGIN_ROOT>/scripts/cron/memory-promote.sh   # cortex.memory-promote`
- 落盘前 `AskUserQuestion` 打印待 append 行, 选项 `写入` / `取消` / `改时间`
- `Bash echo '...' >> ~/.cortexrc.cron && (crontab -l 2>/dev/null; cat ~/.cortexrc.cron) | crontab -`

## 后端 3: GitHub Actions (远程仓库) — 不自动写

- 仅打印模板, 提示用户复制到 `<vault repo>/.github/workflows/cortex-cron.yml`
- 模板包含 9 个 `jobs.<name>`, 各 `on.schedule.cron`, `runs-on: ubuntu-latest`, `steps` 安装 cortex 插件 + 跑 `bash scripts/cron/<job>.sh`
- 提示 vault 须为 GitHub repo, secrets 配 `OBSIDIAN_API_KEY` (若 lint 走 REST)

## 关键约束

- 写 plist / crontab 前**必须** dry-run + `AskUserQuestion` 二次确认
- cron job 默认 `--allowed-tools "Bash Read Glob Write Edit"` (memory-* 需写; lint 只读保持 `Bash Read Glob`)
- wrapper 提供 `flock -n` + `timeout 600` (复用 `scripts/cron/run.sh`)

## 卸载提示

- launchd: `launchctl unload <plist> && rm <plist>`
- cron: 编辑 `~/.cortexrc.cron` 删行 + `crontab ~/.cortexrc.cron`
- gha: 删 `.github/workflows/cortex-cron.yml`

重跑 `cortex-install` 可再次配置。
