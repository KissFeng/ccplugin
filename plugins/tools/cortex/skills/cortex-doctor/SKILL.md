---
name: cortex-doctor
description: 诊断 cortex 健康 — vault/obsidian-cli/app-running/MCP/SC/rg/lint/locales/lang-fallback/sessions/config/wrappers 共 18 项。Triggers on "诊断 cortex", "cortex doctor", "体检 vault", "vault 健康".
disable-model-invocation: true
allowed-tools: Bash Read Glob mcp__obsidian__obsidian_list_files_in_vault mcp__obsidian__obsidian_list_files_in_dir mcp__obsidian__obsidian_get_file_contents
---

# cortex-doctor

对当前环境做完整体检并产出报告。**只读, 不修复**, 仅给修复建议命令。

## 触发场景

- 用户显式 "诊断 cortex" / "cortex doctor" / "体检 vault"
- 安装后首次自检 (用户驱动)
- 跑 lint / search 报错时, 用户主动调用排查环境

## 关键决策树

```
按顺序跑 18 项体检 (详见 health-checks.md):
  1-2 vault 路径 / 结构
  3-6 obsidian CLI / app / 配置
  7-9 MCP / REST API / SC / Git
  10-11 lint 基线 / 模板
  12-13 SC REST API / ripgrep
  14 backlink 完整性
  15-17 config 存在 / 合法 / wrapper

每项 emoji 状态行输出, 任一失败不中断后续。
末尾总结 + 修复建议 (参见 fix-suggestions.md 矩阵)。
```

## AUTO_MODE (wrapper / cron 传 `auto` 后缀触发)

- 跳 AskUserQuestion, 按默认值 (诊断仅读, 不动盘)
- persistent: error 自决降级 / 重试 / 换工具组合, 禁询问, 禁中止
- 输出诊断报告 + 建议命令 (用户后续手动执行)

## 不做

- 不写 vault (诊断专用)
- 不自动修复, 仅给出建议命令
- `disable-model-invocation: true`, 必须用户显式触发

## References (按需加载)

| 文件 | 用途 |
|---|---|
| [`references/health-checks.md`](references/health-checks.md) | 18 项体检逐项规则 + 检查命令 + emoji 状态行格式 |
| [`references/fix-suggestions.md`](references/fix-suggestions.md) | 实现提示 + 容错策略 + 各失败项对应修复命令矩阵 |
