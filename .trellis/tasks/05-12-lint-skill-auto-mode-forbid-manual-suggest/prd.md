# PRD — cortex-lint SKILL AUTO_MODE 禁手动修复建议 + 禁询问

## 痛点

bash 触发 lint (`~/.cortex/scripts/lint.sh`) 后, AI 仍输出:
- "### 手动修复建议" 表格
- "需要我执行 --fix 吗?" 询问

违反约束: bash 全自动, 禁人工。

## 现状

cortex-lint SKILL.md 已有 AUTO_MODE 段, 但 AI 仍走主流程描述输出修复建议表。SKILL 没明确"bash 触发时禁建议输出"。

## 目标

cortex-lint SKILL 加严 AUTO_MODE 段:
- bash 触发 (prompt 含 `[AUTO_MODE]`) → 仅:
  1. Bash 调 `python -m lint.run --fix`
  2. 报 `fixed: N, rules_hit: [...]`
  3. **禁**输出"手动修复建议"/"需要执行 --fix 吗"/任何询问
- 非 AUTO_MODE (用户交互场景, e.g. `/cortex:lint --skill` 或 IDE 内 SKILL 自动触发) → 主流程不变, 可输出建议 + 询问

## 范围
- 仅改 `cortex-lint/SKILL.md`
- **不改** lint/run.py 规则/autofix 行为
- **不改** wrapper / cron / 其他 SKILL

## 设计

`skills/cortex-lint/SKILL.md` AUTO_MODE 段加严:

```markdown
## AUTO_MODE 行为 (wrapper bash 触发)

prompt 含 `[AUTO_MODE]` 时:

**唯一允许输出**:
1. Bash 调 `cd <PLUGIN> && PYTHONPATH=. python3 -m lint.run --vault <VAULT> --fix`
2. 解析 JSON, 报告:
   - fixed: N
   - rules_hit: [...]
   - errors_remaining: N (若 != 0)
3. 结束。

**严禁**:
- 输出"手动修复建议"表/段
- 输出"需要执行 --fix 吗" / "是否需要 ..." / 任何 confirmation 询问
- 输出 fix 后的清理建议
- AskUserQuestion (allowed-tools 已禁)

fail-fast: lint exit 非 0 → 报错误码 + 1 行原因, 不询问回退方案。

非 AUTO_MODE (IDE 内手动调 SKILL 或 /cortex:lint --skill): 主流程不变, 可输出建议 + 询问。
```

## 验收

- [ ] SKILL AUTO_MODE 段含"严禁手动建议/询问"
- [ ] 不动其他规则/限定 (lint/run.py / autofix 行为 / wrapper / 其它 SKILL)
- [ ] 286 tests PASS
- [ ] marketplace 同步

## 子任务
单 trellis-implement 单文件改。
