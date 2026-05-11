# cortex AskUserQuestion 改造审计

- **Query**: 审计 cortex 插件所有 "需要用户确认" 的交互点, 准备改用 `AskUserQuestion` 工具
- **Scope**: internal (`plugins/tools/cortex/`)
- **Date**: 2026-05-11

## TL;DR

共识别 **17 个确认点**, 分布在 **9 个文件** (4 skill / 4 agent / 1 locale)。按类型划分:

- **多选项决策** (3-4 options): 5 个 (lang/preset/cron 平台/refactor 子操作选择)
- **二元授权** (apply/abort): 8 个 (refactor `--apply`, cron install, locale set, install 写盘, ingest 安装 CLI, …)
- **多挑选清单** (≥2 items from N): 3 个 (linker 候选 wikilink, archivist 迁移提案, curator 提案表)
- **不该问** (跳过): 1 个 (search "长答让用户追问" — 那是输出回馈, 不是决策)

新增风险面: cortex 缺少正式 "L3 直接写 vault" 路径 — 当前 fallback 链 `notesmd-cli → MCP → 裸 Write` 的最后一段在 ingest/install/new/canvas 内已默默使用, **未做用户授权**。这是改造重点。

## 确认点清单

| File | Line | 当前文案 / 信号 | 类型 | 改造建议 (AskUserQuestion 形式) |
|---|---|---|---|---|
| `skills/cortex-install/SKILL.md` | 20 | "询问 lang — 默认 zh-CN, 可选 en/ja/用户自定义" | 多选项 (4) | Q="选择 vault 主语言", options=`[zh-CN, en, ja, 其他 (自定义)]` |
| `skills/cortex-install/SKILL.md` | 14 | `preset ∈ {lyt, zettel, para, blank}` 默认 lyt | 多选项 (4) | Q="选择 vault preset", options=`[lyt (默认), zettel, para, blank]` (单次调用可与 lang 合并, ≤4 questions) |
| `skills/cortex-install/SKILL.md` | 49-60 | "周期任务询问 … 注册到? [launchd/cron/gha/none]" | 多选项 (4) + 多个二元 | Q1="cron 注册平台" options=`[launchd, cron, gha, 跳过]`; Q2/3/4 三个任务勾选 (daily lint / weekly fold / weekly dashboard) → 4 questions per call (在限额) |
| `skills/cortex-cron/SKILL.md` | 61 | "强制 dry-run + 确认 — 写 launchd / crontab 前必须打印 snippet, 用户确认才落盘" | 二元授权 | Q="确认写入 cron snippet?" options=`[确认写入, 取消]` |
| `skills/cortex-cron/SKILL.md` | 54 | `install [job]` "dry-run 显示要写入的 plist/crontab, 用户确认后落盘" | 二元授权 | 同上 (复用) |
| `skills/cortex-cron/SKILL.md` | 83 | `确认写入? [Y/n] y` (输出示例) | 二元 (示例文案) | 替换为 AskUserQuestion 示例 |
| `skills/cortex-refactor/SKILL.md` | 11 | "**全部默认 dry-run**, 用户明确 `--apply` 才改盘" | 二元授权 | Q="应用该重构 plan?" options=`[应用 (--apply), 取消]`; 显示 JSON plan 摘要后调用 |
| `skills/cortex-refactor/SKILL.md` | 102 | "用户确认后再加 `--apply` 重跑" | 二元授权 | 同上 |
| `skills/cortex-refactor/SKILL.md` | 76 | "lint 命中 `path-naming-violation` 后用户授权修复" | 二元授权 | Q="授权修复 path-naming 违规?" options=`[授权, 跳过]` |
| `skills/cortex-locale/SKILL.md` | 50 | "set 操作前先 dry-run 打印 diff, 再确认写盘" | 二元授权 | Q="写入 vault.lang = <new>?" options=`[确认写入, 取消]` |
| `skills/cortex-install/SKILL.md` | 50 | "**不覆盖已有文件** — 用 Glob 检查目标路径, 存在则跳过" | 二元 (隐式) | 当前是 "默认跳过"; 可选改造: Q="目标已存在, 覆盖 / 跳过 / 备份后覆盖?" options=3 |
| `skills/cortex-ingest/SKILL.md` | 116 | "写入失败 → 保留原文到 ~/.cache/cortex/ingest/..." | 二元 (失败兜底) | Q="写入失败, 重试 / 保留缓存 / 放弃?" options=3 |
| `agents/cortex-linker.md` | 23, 31, 40, 71 | "提议清单, 用户挑选后才 patch", "auto_apply 默认 false — 提案为主" | 多挑选 | Q="挑选要应用的 wikilink 增链" options=`[全部应用, 仅前 3, 手工选择, 取消]` (>4 候选时退化为 batch 二元) |
| `agents/cortex-archivist.md` | 22, 50 | "提案-only, 实际迁移走 cortex-refactor", "不直接 move (主线决定后调 cortex-refactor)" | 多挑选 → 二元授权 | Q="应用档案迁移提案?" options=`[全部 apply, 仅高分项 (>0.7), 取消]` |
| `agents/cortex-curator.md` | 20, 37, 49 | "改盘走 cortex-refactor + 用户确认", "主线决定是否调度 cortex-refactor", "rename 由用户跑 cortex-refactor migrate-locale" | 多挑选 → refactor | Q="按提案顺序执行哪些?" options=`[顺序 1-2, 1-3, 全部, 取消]`; 单条二元化亦可 |
| `AGENT.md` | 75 | "proposal-only agent (curator/archivist/linker) 不直接落盘; 落盘走 cortex-refactor + 用户确认" | 元规则 | 同步更新文档: "落盘前调 AskUserQuestion 而非 free-text 询问" |
| `locales/{zh-CN,en,ja}.yml` | 54 (`cli_missing_warn`) | "助手须在首次回复时**主动询问用户**是否要立即安装" | 二元授权 | Q="notesmd-cli 未装, 立即安装?" options=`[brew (macOS), scoop (Win), yay (Arch), 跳过 (走降级)]` (4 options) |

## L3 直接写文件授权设计建议

**背景**: cortex 当前两级路径 `notesmd-cli (L1) → MCP (L2)`, 第三级 "裸 Write/Edit" 在 ingest/install/new/canvas 内已隐式使用 (见 `cortex-ingest:72` "fallback Write", `cortex-install:53` "MCP 不可用回退 Write")。需求是 **把 L3 显式化为 "AskUserQuestion 授权 → 直接写 vault" 路径**。

### 触发条件 (任一)

1. L1+L2 均不可用 (CLI 缺失 + MCP server down)
2. 操作类型 CLI/MCP 不支持 (canvas JSON / `.obsidian/` 配置)
3. 大批量改 (一次 ≥ 10 文件, 走 CLI 太慢)
4. 用户显式要求 "直接写"

### AskUserQuestion 形式

```
Q: "L1/L2 均不可用. 是否授权直接写 vault 文件 <path>?"
options:
  - "授权本次 (单文件)"
  - "授权本会话所有 (session 范围)"
  - "授权本次操作所有文件 (batch 范围)"
  - "拒绝, 中止"
```

### Session 缓存策略

- **per-file**: 每个目标文件单独问 (安全, 噪音大) — 默认
- **per-session**: 用户选 "session 授权" 后, 同会话内 L3 写不再问 → 主线在 transient 内存 (env / 临时 JSON) 记 `cortex_l3_session_grant=true`, session 结束失效
- **per-batch**: 仅当前 `/cortex:<op>` 调用范围内授权; 调用结束清除

**推荐**: 默认 per-file; 单次操作 ≥ 3 文件时升级为 "本次 batch 授权" (二级 AskUserQuestion 选项), 不引入 cross-session 持久授权 (vault 安全优先)。

### 受影响的具体路径 (需挂 L3 授权 gate)

| 当前路径 | 文件 | 信号 | 是否高危 |
|---|---|---|---|
| `mcp__obsidian__obsidian_append_content` 失败 → `Write` | `cortex-install:53` | "MCP 不可用回退 Write" | 中 (新文件) |
| `mcp__obsidian__obsidian_put_content` 失败 → `Write` | `cortex-ingest:72` | "fallback Write" | 中 (新页面) |
| `mcp__obsidian__obsidian_append_content` 失败 → `Write` | `cortex-new:46` | "失败回退 Write" | 中 (新文件) |
| 写 `.canvas` JSON (CLI 不支持) | `cortex-canvas:28` | 默认走静态 JSON | 低 (派生物) |
| linker `auto_apply=true` 写 `相关: [[X]]` | `cortex-linker.md:46` | "本地 Edit" 兜底 | **高** (改既有页) |

### 不该挂 L3 授权的路径

- 读操作 (`print` / `search-content` / `get_file_contents`) — 无副作用
- backup 目录写 (`_meta/.cortex-backup/`) — 由 cortex 维护, 用户已隐式同意
- dry-run 输出 (stdout / JSON plan) — 无落盘

## 不该改造的场景 (跳过原因)

| 场景 | 文件:行 | 跳过原因 |
|---|---|---|
| "长答让用户追问" | `cortex-search:74` | 输出回馈, 非决策点 |
| "用户应自行轮转 sessions" | `cortex-session:51` | 仅文档建议, 无交互 |
| "用户决定是否保留 alias 字段" | `cortex-refactor:23` | 行为规则注释, 非运行时问 |
| "用户可手动 git ignore backup" | `cortex-lint:74` | 配置建议 |
| `{{TITLE}}` ← 用户输入 | `cortex-new:33` | 命令行参数, 已显式 |
| "topic 无匹配节点 → abort" | `cortex-canvas:49` | 自动决策, 无歧义 |
| "fallback 链 zh-CN → zh → en" | `cortex-locale:* ` | 算法兜底, 不问用户 |
| "用户讨论的是某项目内事 → type=domain" | `cortex-save:35` | 主线推断, 已知答案 (trellis-brainstorm gate: 可推导) |

## 改造优先级建议

1. **P0 高 ROI** — `cortex-refactor --apply` 确认 + `cortex-cron install` 确认: 高频, 二元简单, 改一次受益面广
2. **P0 安全** — L3 直接写授权 (尤其 linker auto_apply + ingest fallback Write): 当前默默写盘的反模式
3. **P1 体验** — `cortex-install` lang/preset/cron 一次性问 ≤ 4 questions, 替代分步交互菜单
4. **P2** — proposal-only agent (linker/archivist/curator) 的批量挑选, 退化到 "全部 / 高分 / 取消" 三选项即可, 不必每项问

## Caveats / Not Found

- 未找到任何已实际调用 `AskUserQuestion` 工具的痕迹 — 改造是 **零现存** 起点
- locales/{en,ja,zh-CN}.yml 内仅 `cli_missing_warn` 含明确 "ask the user" 信号, 其余 prompts 为输出文案 (archive_pending / session_header) 不涉决策
- `cortex-historian` / `cortex-summarizer` / `cortex-cartographer` / `cortex-researcher` / `cortex-translator` 五个 agent **未发现独立确认点** — 它们或是只读 (historian/summarizer), 或落盘已委托给 cortex-save/refactor/canvas (后者承担确认)
- 未检查 `hooks/*` 与 `scripts/*` (题目要求仅 agents/skills/AGENT.md/locales); 如 install_cron.sh 等 shell 脚本可能内含 `read -p` 类原生提问, 改造时需一并审视
