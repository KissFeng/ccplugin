# cortex-refactor — evolution-apply 子操作

> 消化 cortex-digest 抽出的 evolution proposal, patch SKILL/AGENT。

## 触发

- 用户说 "应用 evolution proposal" / "review patterns"
- 调 `bash ~/.cortex/scripts/refactor.sh evolution-apply`
- 显式 `/cortex:refactor evolution-apply`

## 前置

`cortex-digest` 跑后, `_assets/evolution-proposals/` 有 pending proposal (PR3 生成)。

## AI 主线串行流程

1. 调 `bash ~/.cortex/scripts/refactor.sh evolution-list --json` 取 pending proposal 列表
2. 列表为空 → 输出 `{"applied":0,"rejected":0,"deferred":0,"safety_blocked":0,"reason":"no pending proposal"}` 结束
3. 列表非空 → 逐条循环:
   1. 用 `AskUserQuestion` 单次询问 (header=`Proposal <N/M>`, question 列 path + target_skill + diff_summary, 单选): **接受 / 拒绝 / 推迟**
   2. **接受**:
      - `bash ~/.cortex/scripts/refactor.sh evolution-check <proposal_path> --json` 跑 safety gate
      - safety gate fail → 计 `safety_blocked++`, 输出 message 跳过此条 (不删 proposal)
      - safety gate ok → 解 JSON `diff` 字段, 用 `Edit` 工具 (或 `mcp__obsidian__obsidian_patch_content`) 应用到 `target_skill`; 落盘后调 `bash ~/.cortex/scripts/refactor.sh evolution-delete <proposal_path>` 清 proposal; 计 `applied++`
   3. **拒绝**: 调 `evolution-delete` 清 proposal (拒绝即放弃, 避免下次重复问); 计 `rejected++`
   4. **推迟**: 不动 proposal, 留到下次; 计 `deferred++`
4. 全部处理完输出 compact JSON: `{"applied":N,"rejected":M,"deferred":K,"safety_blocked":L}`

## Safety gate (python 已实现, AI 不重复判断)

| 检查 | 拒绝原因 |
|------|---------|
| target_skill 白名单 | `skills/*/SKILL.md` / `skills/*/references/*.md` / `agents/*.md` / `AGENT.md` |
| target_skill 黑名单 | 命中 `commands/` / `scripts/` / `_meta/` / `_templates/` 拒 |
| git working tree | `plugins/tools/cortex/` 下必须 clean, dirty 则拒并提示 user 先 commit |
| proposal 文件存在 | 不存在直接拒 |
| yaml frontmatter | 解析失败拒 |
| diff block 存在 | 缺 ` ```diff ` fence 拒 |

## 禁忌

- 不批量"全部接受" — 必须一条一问 (AskUserQuestion 单次单条)
- 不静默删 proposal — 接受/拒绝/推迟必明确告知用户
- safety_blocked 后**不**自动重试 — 用户先 commit / 改 proposal target / 调白名单后再跑

## AUTO_MODE 例外

本子操作走用户**显式**确认每条 proposal, **不**接 wrapper AUTO_MODE 跳问语义。即便从 shell wrapper 进入, AI 仍必须 AskUserQuestion 一条条问 (此处用户授权 = 单条接受, 不是批量授权)。
