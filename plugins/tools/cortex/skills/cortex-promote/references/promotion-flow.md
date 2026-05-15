# cortex-promote — 执行步骤 + 审计

> SKILL.md 入口的"执行晋级"具体步骤 + 索引更新 + 回滚 + 错误处理。

## 输入

- `--uri`: 单条候选 URI (可选, 默认扫 candidates.md 全部)
- `--target-level`: 单条时指定目标 (e.g. `L1`), 全扫时按候选行内目标
- `--auto-low`: 默认 false; true 时 L4→L3 / L3→L2 自动批 (无交互)
- `--dry-run`: 仅打印计划

## 执行晋级 (per uri)

1. 解析 source uri → 源文件路径
2. 解析 target uri → 目标路径 (按 URI 解析规则)
3. Edit 源文件 frontmatter:
   - `level: <new>`
   - `uri: <new>`
   - `promoted_from: <old uri>`
   - `promoted_at: <now>`
4. 文件 mv (源 → 目标) (用 Bash mv; 路径校验 in-vault)
5. L0 额外: git tag `cortex-L0-<sha8>` (`Bash git -C <vault> tag ...`)

## 更新索引

- 改 `_meta/uri-index.json`: 删旧 URI, 加新 URI
- 改 `candidates.md` 行: `- [ ]` → `- [x]` + 加完成时间注释

## 回滚

任一步骤失败 → 用 Edit 恢复 frontmatter, mv 回原位 (best-effort), 输出 `failed_at_step`。

## 输出示例

```
[promote] scanned candidates.md: 12 候选
  L4→L3: 3 (auto-batch executed)
    ✅ L4://ledger/2026-05-10#evt-3 → L3://episodic/2026-05-10/T0930
    ...
  L3→L2: 4 (need --auto-low, current dry)
    🟡 L3://episodic/2026-05-08/T1100 → L2://semantic/go/channel  (recall 6x)
  L2→L1: 2 (need user approval, prompting...)
    [AskUserQuestion] 批准 L2://semantic/pkm → L1://semantic-stable/pkm ?
  L1→L0: 1 (CRITICAL, AUTO_MODE 拒绝)
    🛑 候选: L1://procedural/git-commit-flow → L0://habits/git
        请跑 ~/.cortex/scripts/memory.sh promote --interactive 人工审批

总结: 3 executed, 4 pending --auto-low, 2 pending user, 1 blocked
索引更新: _meta/uri-index.json
```

## 错误处理

- 候选行格式非法 → 跳过 + warning
- 目标 URI 已存在 → 拒, 不覆盖 (冲突解决交用户)
- mv 失败 (权限/磁盘) → 回滚 frontmatter, 退 1
- git tag 失败 (vault 非 git repo) → L0 晋级仍执行, 但输出 warning "L0 晋级无 git tag, 完整性追溯减弱"
- AskUserQuestion 取消 → 该条标记 cancelled, 继续后续
