# cortex 迁移到官方 obsidian CLI + 强制 AskUserQuestion 确认

## Goal

将 cortex 插件的写操作主路径从 `notesmd-cli` (Yakitrak/obsidian-cli 改名) 迁移到 **官方 Obsidian CLI** (v1.12.4 GA 2026-02-27),
并把所有需要用户确认的交互点统一改用 Claude Code 内建 `AskUserQuestion` 工具,
避免 free-text 提示带来的歧义和不可审计性。

## What I already know

- 官方 Obsidian CLI 已 GA 免费 (2026-02-27 v1.12.4), 经 Obsidian 运行时, app 需在跑, 会自动 launch。
- notesmd-cli (原 Yakitrak/obsidian-cli) Go binary headless, 不需 app, 但是第三方。
- 当前 cortex L1=notesmd-cli, L2=mcp__obsidian__*, L3=cortex skill 直接写。
- 新优先级: **L1=官方 CLI, L2=mcp__obsidian__*, L3=直接写文件 (需 AskUserQuestion 显式授权)**。
- AskUserQuestion 限制: 1-4 questions/call, 2-4 options/question, 系统自动附 "Other"; 不能用于 plan approval。
- 受影响文件清单:
  - `plugins/tools/cortex/.claude-plugin/plugin.json` (无 CLI 引用, 跳过)
  - `plugins/tools/cortex/AGENT.md:9,14`
  - `plugins/tools/cortex/locales/{en,ja,zh-CN}.yml` (`collab_no_direct` + `cli_missing_warn`)
  - `plugins/tools/cortex/agents/*.md` × 8 (`notesmd-cli <cmd> ... (回退 mcp__obsidian__*)` 模式)
  - `plugins/tools/cortex/docs/设计决策.md:27,31,33,39` (D2 决策需重写)
  - `plugins/tools/cortex/docs/架构设计.md:43,123,125` (L1/L2/L3 表)
  - `plugins/tools/cortex/hooks/session_start.sh` (`shutil.which("notesmd-cli")` 改成官方 CLI 检测)
  - cortex skills 中所有 prompt 用户确认点 (待审计)

## Assumptions (temporary)

- 官方 CLI 命令面覆盖 notesmd-cli 全部 7 个动作 (print/create/list/search-content/move/frontmatter/daily) — **待研究验证**。
- 官方 CLI 在系统 PATH 中安装名为 `obsidian` 或 `obsidian-cli` — **待研究验证**。
- 官方 CLI move 同样自动更新 wikilink (WebSearch 初步确认) — **待研究**。
- L3 直接写场景: vault 内非 markdown (canvas/excalidraw json), 或 app 未跑且 CLI 不可用时的兜底。

## Decisions (locked)

- **L1 = 官方 CLI only**, 不保留 notesmd-cli 任何路径; app 未跑时**接受丢失 headless**, 直接走 L2=mcp__obsidian__*, 最后 L3=直接写盘。
- **L3 授权粒度**: per-file 默认 (单文件改写时单次 AskUserQuestion), 批量 ≥3 文件时升级为 per-batch 单次授权 (列出所有目标路径)。
- **不引入 cross-session 持久授权** (vault 安全优先)。
- 官方 CLI 二进制名 `obsidian` (全平台一致), 多 vault: `obsidian vault=<name> <cmd>`, 参数语法 `key=value` 无 `--flag`。
- 仍需 MCP fallback: heading-anchor patch / block-id patch / canvas / 完整 metadata graph。
- `move` 自动更新 wikilink: 官方 CLI 条件支持 (依赖 vault 设置 "Automatically update internal links"); `cortex-doctor` 加入此设置校验。

## Implementation Plan (small PRs)

**PR1 — 基础设施 (CLI 检测 + locale + AskUserQuestion helper)**
- `hooks/session_start.sh`: 检测 `obsidian` PATH 存在性, 检测 Obsidian app 是否在跑 (mac: `pgrep -x Obsidian`, linux: `pgrep obsidian`, win: `tasklist`)
- `locales/{en,ja,zh-CN}.yml`: 改写 `collab_no_direct` (新 L1/L2/L3 顺序) + `cli_missing_warn` (官方 CLI 安装入口 = Obsidian Settings → General → Command line interface)
- 新增 locale key: `l3_authorize_single` / `l3_authorize_batch` (用于 AskUserQuestion 文案)

**PR2 — 命令面替换 (8 agents + AGENT.md)**
- `AGENT.md:9,14` 改写
- `agents/*.md` × 8: notesmd-cli → obsidian 命令面映射
  - print → read, create → create overwrite, list → files, search-content → search:context, move → move (+ wikilink update note), frontmatter → property/properties, daily → daily, `--vault X` → `vault=X`

**PR3 — 文档同步**
- `docs/设计决策.md` D2 重写: 决策方更新为 "官方 CLI GA, 第三方理由消失"
- `docs/架构设计.md`: L1/L2/L3 表 + 架构图更新

**PR4 — AskUserQuestion 改造 (17 个点)**
- 高价值优先: `cortex-refactor --apply` / `cortex-cron install` / `cortex-install` lang+preset+cron 合并 (≤4 questions)
- L3 直接写 gate: `cortex-ingest:72` / `cortex-install:53` / `cortex-new:46` / `cortex-linker auto_apply` — 加 AskUserQuestion per-file/per-batch 授权
- 审 `hooks/*` 与 `scripts/install_cron.sh` 中的 `read -p` 提问 (audit 未覆盖)

**PR5 — cortex-doctor 增强**
- 检测 Obsidian "Automatically update internal links" 设置 (保 move 行为正确)
- 检测官方 CLI 启用状态

## Requirements (evolving)

- [ ] 8 个 cortex agent 文件的 `notesmd-cli <cmd>` 替换为官方 CLI 等价命令。
- [ ] 3 个 locale 文件 `collab_no_direct` + `cli_missing_warn` 改写。
- [ ] `hooks/session_start.sh` CLI 检测逻辑迁移。
- [ ] `docs/设计决策.md` D2 决策重写, 反映新 L1/L2/L3。
- [ ] `docs/架构设计.md` 架构图 + L1/L2/L3 表更新。
- [ ] cortex skills/agents 中所有用户确认点改用 AskUserQuestion (待审计清单)。
- [ ] L3 直接写需 AskUserQuestion 授权机制。

## Acceptance Criteria (evolving)

- [ ] `rg -n "notesmd-cli" plugins/tools/cortex/` 零命中 (或仅作历史 fallback 提示)。
- [ ] cortex skills/agents 内无 free-text 用户确认 prompt, 全部走 AskUserQuestion。
- [ ] SessionStart hook 检测官方 CLI 缺失时给安装提示 (官方下载路径)。
- [ ] L3 直接写有用户授权 gate, 未授权时拒绝写盘。

## Definition of Done

- [ ] 所有受影响文件改完, 通过 `gitnexus_detect_changes` 校验范围。
- [ ] 至少手动跑通: cortex-save / cortex-search / cortex-new 三个核心 skill 在官方 CLI 路径下工作。
- [ ] CLAUDE.md §代码质量检查规范跑过 (claude --settings glm-4.5-flash 验证 skill 描述)。
- [ ] 暂存区自动提交 (项目约定)。

## Out of Scope

- 不改 cortex 插件的功能边界 (search/save/lint/fold 等行为不变)。
- 不改 marketplace.json 注册信息。
- 不动 plugin.json schema (上轮已重构完成, commit `956cebf1`)。
- 不为兼容旧 notesmd-cli 用户保留双路径 — 直接切换。

## Technical Notes

- 官方 CLI 时间线: 2026-02-10 早期访问 (Catalyst 用户), 2026-02-27 GA 免费。
- notesmd-cli 改名背景: 因官方 CLI 发布, Yakitrak/obsidian-cli 改名避免冲突。
- AskUserQuestion 限制 4 questions, 单 question 4 options + 自动 Other。
- Trellis brainstorm 规则: 研究类调用必走 `trellis-research` sub-agent, 不在主线 inline WebFetch/WebSearch。

## Research References

- [`research/obsidian-cli-commands.md`](research/obsidian-cli-commands.md) — 官方 CLI 二进制 `obsidian`, 7 actions 全部映射, 需 app 在跑 (丢失 headless), 性能不如 Go 二进制
- [`research/cortex-askuserquestion-audit.md`](research/cortex-askuserquestion-audit.md) — 17 个确认点 / 9 文件 / 零现存; L3 直接写当前默默落盘是改造重点
