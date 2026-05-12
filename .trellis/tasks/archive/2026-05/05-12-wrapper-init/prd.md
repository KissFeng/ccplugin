# PRD — ~/.cortex/scripts 加 init 知识库初始化 wrapper

## 背景

`install.sh` 仅装 ~/.cortex/{config, scripts/wrapper}。vault 骨架 (双 namespace 目录 + seed 文件) 由 cortex-install SKILL (LLM) 安装时建。但 ~/.cortex/scripts/ 缺一个**便捷入口** wrapper 让用户随时重建/初始化 vault 骨架, 不必启动 LLM SKILL。

## 目标

加 `~/.cortex/scripts/init.sh` (由 plugin 侧 `install_wrappers.sh` 生成), 调 `cortex-install` SKILL 跑 AUTO_MODE 安装 vault 骨架。

### 不在范围
- 不动 install.sh (它已装 wrapper, 现在让 wrapper 多一个)
- 不动 cortex-install SKILL 内容
- 不重写 vault 骨架机制 (复用 SKILL)

## 设计

### 1. `~/.cortex/scripts/init.sh` (生成自 install_wrappers.sh)

```bash
#!/usr/bin/env bash
# init.sh — 初始化/重建 cortex vault 骨架 (双 namespace + seed 文件)
#
# 调 cortex-install SKILL (AUTO_MODE), 按 ~/.cortex/config.json 解析 vault。
#
# Usage: ~/.cortex/scripts/init.sh [--force]
set -uo pipefail

FORCE="${1:-}"

# 解析 vault
CONFIG="$HOME/.cortex/config.json"
if [[ ! -f "$CONFIG" ]]; then
  echo "[cortex] config 不存在 ($CONFIG), 跑 install.sh 先安装" >&2
  exit 4
fi

VAULT="$(jq -r '.vault // empty' "$CONFIG" 2>/dev/null)"
if [[ -z "$VAULT" ]]; then
  echo "[cortex] vault 路径未配置" >&2
  exit 4
fi

# 已初始化判断 (_meta/version.json 存在)
if [[ -f "$VAULT/_meta/version.json" && "$FORCE" != "--force" ]]; then
  echo "[cortex] vault 已初始化: $VAULT"
  echo "  → 重建用: $0 --force"
  echo "  → 看结构: ls $VAULT"
  exit 0
fi

PLUGIN_ROOT="${CORTEX_INSTALL_PATH:-$HOME/.claude/plugins/marketplaces/ccplugin-market/plugins/tools/cortex}"
SETTINGS="$(jq -r '.settings // empty' "$CONFIG" 2>/dev/null)"
SETTINGS="${SETTINGS:-$HOME/.claude/settings.glm-4.7-flash.json}"

# 跑 cortex-install SKILL via claude --bare
PROMPT="[AUTO_MODE: non-interactive shell wrapper. 不用 AskUserQuestion, 自动决策.]

初始化 cortex vault: $VAULT

跑 cortex-install skill 完整流程:
1. 不询问 lang, 用 \${CORTEX_LANG:-zh-CN}
2. preset=lyt (固定)
3. 写共享根 (_meta/version.json, memory-policy.yaml, template-manifest.json, _templates/, index.md, hot.md, 主页.md, 焦点.md)
4. 按 plugin presets/_structure.json 创建知识库 + 记忆体系 + 仪表盘 + 归档目录树
5. 复制 seed_files (含占位符渲染: {{TITLE}} {{CURRENT_PATH}} {{LAST_UPDATED}})
6. **跳过** git auto-sync 询问 (默认 off, AUTO_MODE)
7. **跳过** cron 注册询问 (默认 off, 用户单独跑 install_cron.sh)
8. 回报创建/跳过文件总数

强制模式: $FORCE
不动用户已写入的笔记 (frontmatter 检测 last_modified > created 则跳过)"

claude --bare \
  --no-session-persistence \
  --settings "$SETTINGS" \
  --max-budget-usd 0.30 \
  -p "$PROMPT" \
  --allowed-tools "Bash Read Write Edit Glob mcp__obsidian__obsidian_list_files_in_vault mcp__obsidian__obsidian_list_files_in_dir mcp__obsidian__obsidian_get_file_contents mcp__obsidian__obsidian_append_content"
```

### 2. `install_wrappers.sh` 加生成 init.sh

`plugins/tools/cortex/scripts/install_wrappers.sh`:
- 在生成 wrapper 列表加 `init`
- 写 init.sh 内容 (heredoc) — 与现有 wrapper 风格一致

### 3. init.sh 输出友好

完成后打印:
```
[cortex] ✓ vault 初始化完成: <VAULT>
[cortex]   主页:     <VAULT>/主页.md
[cortex]   知识库:   <VAULT>/知识库/
[cortex]   记忆体系: <VAULT>/记忆体系/
[cortex]   仪表盘:   <VAULT>/仪表盘/
[cortex] Next:
[cortex]   ~/.cortex/scripts/install_cron.sh   # 注册周期任务
[cortex]   ~/.cortex/scripts/lint.sh           # 健康检查
```

(实际 claude --bare 输出已含, 不重复)

## 实施

单文件改 `plugins/tools/cortex/scripts/install_wrappers.sh`:
1. wrapper 列表加 `init`
2. 加 init.sh 生成函数 (heredoc)

跑 `bash install_wrappers.sh /tmp/test-scripts` 验证生成。

## 验收

- [ ] `plugins/tools/cortex/scripts/install_wrappers.sh` 含 init wrapper 生成逻辑
- [ ] 跑 `bash install_wrappers.sh /tmp/test-cortex-scripts` 生成 init.sh
- [ ] init.sh 含 `[AUTO_MODE]` prefix + claude --bare 调用 + 调 cortex-install SKILL
- [ ] init.sh 有 `--force` 检测 (_meta/version.json 存在跳过, --force 强制)
- [ ] init.sh `bash -n` 语法 PASS
- [ ] init.sh chmod +x
- [ ] install.sh 跑完后 ~/.cortex/scripts/ 含 12 个 wrapper (原 11 + init)
- [ ] 217 python tests 无回归

## 风险

| 风险 | 缓解 |
|------|------|
| claude --bare 超 budget | --max-budget-usd 0.30 限额 |
| seed_files 复制覆盖用户数据 | SKILL 流程已有 frontmatter 检测 + 已存在跳过 |
| --force 误用清空 | 提示 + 备份到 vault/.cortex-backup/<timestamp>/ |

## 子任务

单任务, 单文件改, 单 trellis-implement。
