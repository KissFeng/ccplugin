---
name: cortex-refactor
description: vault 重构 — rename/merge/split/dedupe/extract/inline/migrate-locale/evolution-apply, --apply 才落盘 backup。仅显式触发。Triggers on "重命名", "rename", "merge", "split", "重构 vault".
disable-model-invocation: true
allowed-tools: Bash Read Write Edit Glob mcp__obsidian__obsidian_get_file_contents mcp__obsidian__obsidian_list_files_in_dir AskUserQuestion
---

# cortex-refactor

vault 大动干戈类操作的统一入口。**全部默认 dry-run**, 用户明确 `--apply` 才改盘。

## 触发场景

- 用户明确说"重命名 X 到 Y / 合并 A B / 把这页拆开 / 整理日志"
- `/cortex:lint` 命中 `path-naming-violation` / `filename-illegal` 后用户授权修复
- `/cortex:refactor evolution-apply` 消化 cortex-digest 抽出的 proposal

## 子操作矩阵

| 子操作 | 说明 | References |
|---|---|---|
| rename | 改文件名 + 全 vault wikilink 同步 | rename-merge.md |
| merge | 两页合一, src 移到 `归档/` | rename-merge.md |
| migrate-locale | 切 vault.lang 时一次性 rename 业务目录 | rename-merge.md |
| dedupe | TF-IDF cosine 找相似页对, `--apply` 调 merge | rename-merge.md |
| split | 一页按 H2 拆多页, 原页留 callout | split-page.md |
| extract | 抽 H2 节为独立 concept 页 | split-page.md |
| inline | 子页内联回父页, 子页归档 | split-page.md |
| graph-rebalance | orphan/hub 扫, 自动补 link_gaps | split-page.md |
| evolution-apply | 消化 cortex-digest 写的 proposal, patch SKILL/AGENT | evolution-apply.md |

## 安全约束

1. 默认 dry-run, 输出 JSON plan
2. `--apply` 前在 `_meta/.cortex-backup/refactor-<op>/<ts>/` 全量 backup 涉及文件
3. **不**自动 git commit (与 cortex 整体策略一致)
4. rename/merge 永不覆盖已存在的目标
5. 大批量操作建议先 `--apply` 跑一个文件验证, 再扩大范围

## AUTO_MODE (wrapper / cron 传 `auto` 后缀触发)

- 跳 AskUserQuestion, 按默认值执行 (dry-run, 输出 JSON plan; `--apply` 显式时才落盘)
- persistent: error 自决降级 / 重试, 禁询问, 禁中止
- ≥3 文件批量改写: 不列文件路径授权; backup + apply 直接落 (args 已显式 `--apply`)
- **例外**: `evolution-apply` 不接 AUTO_MODE 跳问, 仍走 AskUserQuestion 一条条问 (单条用户授权)

## References (按需加载)

| 文件 | 用途 |
|---|---|
| [`references/rename-merge.md`](references/rename-merge.md) | rename / merge / migrate-locale / dedupe 详细命令 + dry-run 输出示例 |
| [`references/split-page.md`](references/split-page.md) | split / extract / inline / graph-rebalance 详细命令 |
| [`references/evolution-apply.md`](references/evolution-apply.md) | evolution-apply 串行流程 + safety gate + AskUserQuestion 单条循环 |
